import threading
import time
import subprocess
from pathlib import Path
from queue import Queue
from typing import Dict, List, Optional, Tuple

from core.models import ConversionSettings, MediaInfo, TaskItem
from services.ffmpeg_service import FfmpegService
from utils.files import safe_output_name
from utils.formatting import format_bytes, format_time, parse_ffmpeg_time


def _estimate_eta(elapsed: float, progress: float) -> Optional[float]:
    if progress <= 0:
        return None
    total = elapsed / progress
    return max(total - elapsed, 0.0)


class ConverterService:
    def __init__(self, ffmpeg: FfmpegService, event_queue: Queue):
        self.ffmpeg = ffmpeg
        self.queue = event_queue
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.current_proc: Optional[subprocess.Popen] = None
        self.media_info: Dict[Path, MediaInfo] = {}

    def start(self, tasks: List[TaskItem], settings: ConversionSettings, out_dir: Path) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(tasks, settings, out_dir), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.current_proc and self.current_proc.poll() is None:
            try:
                self.current_proc.terminate()
            except Exception:
                pass

    def _emit(self, event: str, *payload) -> None:
        self.queue.put((event, *payload))

    def _log(self, level: str, msg: str) -> None:
        self._emit("log", level, msg)

    def _run(self, tasks: List[TaskItem], settings: ConversionSettings, out_dir: Path) -> None:
        if not self.ffmpeg.ffmpeg_path:
            self._log("ERROR", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.exe.")
            self._emit("done", True)
            return

        if not tasks:
            self._log("WARN", "Черга порожня.")
            self._emit("done", True)
            return

        total_files = len(tasks)
        done_files = 0
        done_duration = 0.0
        total_duration = 0.0
        total_start = time.time()

        out_dir.mkdir(parents=True, exist_ok=True)

        self.media_info.clear()
        if self.ffmpeg.ffprobe_path:
            for task in tasks:
                info = self.ffmpeg.probe_media(task.path)
                if info:
                    self.media_info[task.path] = info
                    if task.media_type == "video" and info.duration:
                        total_duration += info.duration
                    self._log(
                        "INFO",
                        f"{task.path.name}: {format_time(info.duration)} | {info.vcodec or '-'}"
                        f"/{info.acodec or '-'} | {info.width or '-'}x{info.height or '-'} | {format_bytes(info.size_bytes)}",
                    )
        else:
            self._log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")

        self._emit("set_total", total_files, total_duration)

        merge_enabled = settings.merge
        video_inputs = [t.path for t in tasks if t.media_type == "video"]
        if merge_enabled and len(video_inputs) < 2:
            self._log("WARN", "Merge увімкнено, але відео менше 2. Пропускаю merge.")
            merge_enabled = False

        if merge_enabled:
            name = settings.merge_name.strip() or "merged"
            outp = Path(name)
            if not outp.suffix:
                outp = out_dir / f"{name}.{settings.out_video_format}"
            else:
                outp = out_dir / outp.name
            if not settings.overwrite:
                outp = safe_output_name(out_dir, outp, outp.suffix.lstrip("."))

            duration = sum(self.media_info.get(p, MediaInfo()).duration or 0 for p in video_inputs)
            self._emit("status", f"Обробка (merge): {outp.name}")
            self._log("INFO", f"Merge відео: {len(video_inputs)} файлів → {outp.name}")

            filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(settings, outp.suffix, log_cb=self._log)
            audio_filter = self.ffmpeg.build_audio_speed_filter(settings)
            trim_args = self.ffmpeg.build_trim_args(settings, log_cb=self._log)
            fast_copy_ok, reason = self.ffmpeg.merge_copy_allowed(
                video_inputs, outp.suffix, self.media_info, filters_used, audio_filter is not None, trim_args
            )
            allow_fast = settings.fast_copy and fast_copy_ok
            if settings.fast_copy and not fast_copy_ok:
                self._log("WARN", f"Fast copy (merge) вимкнено: {reason}")

            list_path = ""
            try:
                cmd, list_path = self.ffmpeg.build_merge_command(
                    video_inputs, outp, settings, self.media_info, allow_fast, log_cb=self._log
                )
                rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                if rc == 0 and outp.exists():
                    self._log("OK", f"Готово (merge): {outp.name}")
                else:
                    self._log("ERROR", f"Помилка merge (код {rc})")
            except FileNotFoundError:
                self._log("ERROR", "FFmpeg не знайдено під час запуску.")
                self.stop_event.set()
            except Exception as exc:
                self._log("ERROR", f"Merge помилка: {exc}")
            finally:
                if list_path:
                    try:
                        Path(list_path).unlink(missing_ok=True)
                    except Exception:
                        pass

            done_files += len(video_inputs)
            if duration:
                done_duration += duration
            self._emit("file_done", None, True)

        for task in list(tasks):
            if self.stop_event.is_set():
                self._log("WARN", "Зупинено користувачем.")
                break
            if merge_enabled and task.media_type == "video":
                continue

            if not task.path.exists():
                self._log("ERROR", f"Файл не знайдено: {task.path}")
                done_files += 1
                self._emit("progress", None, 0.0, None, None, done_files / total_files, None)
                continue

            out_ext = settings.out_video_format if task.media_type == "video" else settings.out_image_format
            if settings.overwrite:
                outp = out_dir / f"{task.path.stem}.{out_ext}"
            else:
                outp = safe_output_name(out_dir, task.path, out_ext)

            info = self.media_info.get(task.path)
            duration = info.duration if info and task.media_type == "video" else None

            self._emit("status", f"Обробка: {task.path.name}")
            self._log("INFO", f"→ {task.path.name} ({task.media_type}) ==> {outp.name}")

            try:
                if task.media_type == "video":
                    filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(
                        settings, outp.suffix, log_cb=self._log
                    )
                    audio_filter = self.ffmpeg.build_audio_speed_filter(settings)
                    fast_copy_ok, reason = self.ffmpeg.fast_copy_allowed(
                        task.path, outp.suffix, info, filters_used, audio_filter is not None
                    )
                    allow_fast = settings.fast_copy and fast_copy_ok
                    if settings.fast_copy and not fast_copy_ok:
                        self._log("WARN", f"Fast copy вимкнено для {task.path.name}: {reason}")
                    cmd = self.ffmpeg.build_video_command(task.path, outp, settings, info, allow_fast, log_cb=self._log)
                else:
                    cmd = self.ffmpeg.build_image_command(task.path, outp, settings, log_cb=self._log)
                rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                if rc == 0 and outp.exists():
                    self._log("OK", f"Готово: {outp.name}")
                else:
                    self._log("ERROR", f"Помилка конвертації: {task.path.name} (код {rc})")
            except FileNotFoundError:
                self._log("ERROR", "FFmpeg не знайдено під час запуску. Перевір шлях до ffmpeg.exe.")
                break
            except Exception as exc:
                self._log("ERROR", f"Несподівана помилка: {exc}")

            done_files += 1
            if task.media_type == "video" and duration:
                done_duration += duration
            self._emit("file_done", task.path, True)

        self._emit("done", self.stop_event.is_set())

    def _consume_stderr(self, pipe):
        for line in pipe:
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if "error" in low or "invalid" in low or "failed" in low:
                self._log("WARN", line)

    def _run_ffmpeg(
        self,
        cmd: List[str],
        duration: Optional[float],
        total_done: float,
        total_duration: float,
        done_files: int,
        total_files: int,
        total_start: float,
    ) -> int:
        if len(cmd) < 2:
            return -1
        cmd_with_progress = cmd[:2] + ["-progress", "pipe:1", "-nostats", "-hide_banner"] + cmd[2:]
        proc = subprocess.Popen(
            cmd_with_progress,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,
        )
        self.current_proc = proc
        file_start = time.time()

        assert proc.stderr is not None
        err_thread = threading.Thread(target=self._consume_stderr, args=(proc.stderr,), daemon=True)
        err_thread.start()

        out_time = 0.0
        speed = None
        if proc.stdout is not None:
            for line in proc.stdout:
                if self.stop_event.is_set():
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    break
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key == "out_time_ms":
                    try:
                        out_time = int(value) / 1_000_000
                    except ValueError:
                        pass
                elif key == "out_time_us":
                    try:
                        out_time = int(value) / 1_000_000
                    except ValueError:
                        pass
                elif key == "out_time":
                    parsed = parse_ffmpeg_time(value)
                    if parsed is not None:
                        out_time = parsed
                elif key == "speed":
                    try:
                        speed = float(value.replace("x", ""))
                    except ValueError:
                        pass

                file_pct = None
                file_eta = None
                if duration and duration > 0:
                    file_pct = min(out_time / duration, 1.0)
                    elapsed = max(time.time() - file_start, 0.001)
                    if speed and speed > 0:
                        file_eta = max((duration - out_time) / speed, 0.0)
                    else:
                        file_eta = _estimate_eta(elapsed, file_pct) if file_pct else None

                if total_duration > 0:
                    overall_done = total_done + out_time
                    total_pct = min(overall_done / total_duration, 1.0)
                    overall_elapsed = time.time() - total_start
                    total_eta = _estimate_eta(overall_elapsed, total_pct) if total_pct else None
                else:
                    total_pct = (done_files + (file_pct or 0.0)) / max(total_files, 1)
                    overall_elapsed = time.time() - total_start
                    total_eta = _estimate_eta(overall_elapsed, total_pct) if total_pct else None

                self._emit("progress", file_pct, out_time, duration, file_eta, total_pct, total_eta)

        rc = proc.wait()
        err_thread.join(timeout=0.2)
        self.current_proc = None
        return rc
