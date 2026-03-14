import os
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path
from queue import Queue
from typing import Dict, List, Optional, Tuple

from core.models import ConversionSettings, MediaInfo, TaskItem
from services.ffmpeg_service import FfmpegService
from services.transcription_service import TranscriptionService
from utils.files import build_output_path, safe_output_path, sanitize_file_stem
from utils.formatting import format_bytes, format_time, parse_ffmpeg_time


def _estimate_eta(elapsed: float, progress: float) -> Optional[float]:
    if progress <= 0:
        return None
    total = elapsed / progress
    return max(total - elapsed, 0.0)


class ConverterService:
    def __init__(self, ffmpeg: FfmpegService, event_queue: Queue, transcriber: Optional[TranscriptionService] = None):
        self.ffmpeg = ffmpeg
        self.queue = event_queue
        self.transcriber = transcriber or TranscriptionService()
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

    def _task_state(self, task_path: Path, status: str, message: str = "", output_path: str = "") -> None:
        self._emit("task_state", task_path, status, message, output_path)

    def _effective_settings(self, task: TaskItem, defaults: ConversionSettings) -> ConversionSettings:
        return task.resolved_settings or defaults

    def _task_duration(self, task: TaskItem) -> float:
        info = self.media_info.get(task.path)
        return info.duration or 0.0 if info else 0.0

    def _resolve_output_path(self, task: TaskItem, settings: ConversionSettings, out_dir: Path, index: int) -> Path:
        out_ext = self.ffmpeg.output_extension_for(task.media_type, settings)
        return build_output_path(
            out_dir,
            task.path,
            out_ext,
            template=settings.output_template,
            index=index,
            operation=settings.operation,
            media_type_name=task.media_type,
            overwrite=settings.overwrite,
            skip_existing=settings.skip_existing,
        )

    def _chapter_output_path(self, base_output: Path, chapter_index: int, chapter_title: str) -> Path:
        suffix = base_output.suffix
        chapter_name = chapter_title.strip() or f"chapter_{chapter_index:02d}"
        stem = sanitize_file_stem(f"{base_output.stem} - {chapter_index:02d} {chapter_name}")
        return base_output.with_name(f"{stem}{suffix}")

    def _run_hook(self, command: str, stage: str, *, env: Dict[str, str]) -> None:
        command = command.strip()
        if not command:
            return
        self._log("INFO", f"Hook {stage}: {command}")
        result = subprocess.run(command, shell=True, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            output = (result.stdout or "").strip()
            if output:
                self._log("INFO", output)
            return
        details = (result.stderr or result.stdout or "").strip()
        self._log("WARN", f"Hook {stage} завершився з кодом {result.returncode}: {details or command}")

    def _emit_run_summary(
        self,
        *,
        settings: ConversionSettings,
        out_dir: Path,
        total_files: int,
        stopped: bool,
        results: List[Dict[str, str]],
        started_at: float,
    ) -> None:
        summary = {
            "started_at": started_at,
            "finished_at": time.time(),
            "output_dir": str(out_dir),
            "operation": settings.operation,
            "stopped": stopped,
            "total_files": total_files,
            "results": results,
            "settings": {
                "operation": settings.operation,
                "platform_profile": settings.platform_profile,
                "out_video_fmt": settings.out_video_format,
                "out_audio_fmt": settings.out_audio_format,
                "out_subtitle_fmt": settings.out_subtitle_format,
                "normalize_audio": settings.normalize_audio,
                "audio_track_index": settings.audio_track_index,
                "replace_audio_path": settings.replace_audio_path,
                "split_chapters": settings.split_chapters,
                "output_template": settings.output_template,
            },
        }
        self._emit("run_summary", summary)

    def _validate_operation(self, task: TaskItem, settings: ConversionSettings) -> Tuple[bool, str]:
        if settings.operation in {"audio_only", "subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet", "auto_subtitle"}:
            if task.media_type != "video":
                return False, "Операція підтримується лише для відео"
        return True, ""

    def _total_duration_for(self, tasks: List[TaskItem], defaults: ConversionSettings) -> float:
        total_duration = 0.0
        for task in tasks:
            settings = self._effective_settings(task, defaults)
            if settings.operation in {"convert", "audio_only", "subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet", "auto_subtitle"}:
                total_duration += self._task_duration(task)
        return total_duration

    def _process_audio_chapters(
        self,
        task: TaskItem,
        settings: ConversionSettings,
        out_dir: Path,
        index: int,
        done_duration: float,
        total_duration: float,
        done_files: int,
        total_files: int,
        total_start: float,
    ) -> Tuple[bool, str]:
        info = self.media_info.get(task.path)
        if not info or not info.chapters:
            return False, "У файлі немає глав для split by chapters"

        base_output = self._resolve_output_path(task, settings, out_dir, index)
        chapter_outputs: List[str] = []
        chapter_done = 0.0
        for chapter in info.chapters:
            chapter_duration = max(chapter.end - chapter.start, 0.0)
            chapter_settings = replace(
                settings,
                trim_start=chapter.start,
                trim_end=chapter.end,
                meta_title=chapter.title.strip() or settings.meta_title,
            )
            outp = self._chapter_output_path(base_output, chapter.index, chapter.title)
            if chapter_settings.skip_existing and outp.exists() and not chapter_settings.overwrite:
                self._log("INFO", f"Пропускаю главу, файл вже існує: {outp.name}")
                chapter_outputs.append(str(outp))
                continue
            cmd = self.ffmpeg.build_audio_command(task.path, outp, chapter_settings, log_cb=self._log)
            rc = self._run_ffmpeg(
                cmd,
                chapter_duration,
                done_duration + chapter_done,
                total_duration,
                done_files,
                total_files,
                total_start,
            )
            if rc != 0 or not outp.exists():
                return False, f"Помилка експорту глави {chapter.index}: код {rc}"
            chapter_outputs.append(str(outp))
            chapter_done += chapter_duration
            self._log("OK", f"Глава {chapter.index}: {outp.name}")
        return True, "; ".join(chapter_outputs)

    def _run(self, tasks: List[TaskItem], settings: ConversionSettings, out_dir: Path) -> None:
        if not self.ffmpeg.ffmpeg_path:
            self._log("ERROR", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.")
            self._emit("done", True)
            return

        if not tasks:
            self._log("WARN", "Черга порожня.")
            self._emit("done", True)
            return

        out_dir.mkdir(parents=True, exist_ok=True)
        total_files = len(tasks)
        done_files = 0
        total_start = time.time()
        run_results: List[Dict[str, str]] = []

        self.media_info.clear()
        if self.ffmpeg.ffprobe_path:
            for task in tasks:
                info = self.ffmpeg.probe_media(task.path)
                if info:
                    self.media_info[task.path] = info
                    self._log(
                        "INFO",
                        f"{task.path.name}: {format_time(info.duration)} | {info.vcodec or '-'}"
                        f"/{info.acodec or '-'} | {info.width or '-'}x{info.height or '-'} | {format_bytes(info.size_bytes)}",
                    )
                    analysis_bits = []
                    if info.fps:
                        mode = f" {info.frame_rate_mode}" if info.frame_rate_mode else ""
                        analysis_bits.append(f"{info.fps:.3f} fps{mode}")
                    if info.dynamic_range:
                        analysis_bits.append(info.dynamic_range)
                    if info.color_space:
                        analysis_bits.append(info.color_space)
                    if info.rotation not in (None, 0):
                        analysis_bits.append(f"rot {info.rotation}°")
                    if info.audio_streams:
                        analysis_bits.append(f"a:{info.audio_streams}")
                    if info.subtitle_streams:
                        analysis_bits.append(f"s:{info.subtitle_streams}")
                    if info.chapters:
                        analysis_bits.append(f"chapters:{len(info.chapters)}")
                    if analysis_bits:
                        self._log("INFO", f"{task.path.name}: {' | '.join(analysis_bits)}")
                    for warning in info.warnings:
                        self._log("WARN", f"{task.path.name}: {warning}")
        else:
            self._log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")

        total_duration = self._total_duration_for(tasks, settings)
        done_duration = 0.0
        self._emit("set_total", total_files, total_duration)

        hook_env = dict(os.environ)
        hook_env.update(
            {
                "MC_OUT_DIR": str(out_dir),
                "MC_TOTAL_FILES": str(total_files),
                "MC_OPERATION": settings.operation,
            }
        )
        self._run_hook(settings.before_hook, "before", env=hook_env)

        merge_candidates = [task for task in tasks if task.media_type == "video" and self._effective_settings(task, settings).operation == "convert"]
        merge_enabled = settings.merge and len(merge_candidates) >= 2
        if settings.merge and not merge_enabled:
            self._log("WARN", "Merge доступний лише для щонайменше 2 відео в режимі конвертації.")
        if merge_enabled and settings.replace_audio_path.strip():
            self._log("WARN", "Merge + replace audio не підтримується. Використовую аудіо з джерел.")

        merged_video_paths = {task.path for task in merge_candidates} if merge_enabled else set()

        if merge_enabled:
            name = settings.merge_name.strip() or "merged"
            outp = Path(name)
            if not outp.suffix:
                outp = out_dir / f"{name}.{settings.out_video_format}"
            else:
                outp = out_dir / outp.name
            if not settings.overwrite and not settings.skip_existing:
                outp = safe_output_path(outp)

            merge_duration = sum(self._task_duration(task) for task in merge_candidates)
            if settings.skip_existing and outp.exists() and not settings.overwrite:
                self._log("INFO", f"Пропускаю merge, файл вже існує: {outp.name}")
                for task in merge_candidates:
                    self._task_state(task.path, "skipped", "Вихідний файл вже існує", str(outp))
                    done_files += 1
                    done_duration += self._task_duration(task)
                self._emit("progress", None, 0.0, None, None, done_files / total_files, None)
            else:
                self._emit("status", f"Обробка (merge): {outp.name}")
                self._log("INFO", f"Merge відео: {len(merge_candidates)} файлів → {outp.name}")
                for task in merge_candidates:
                    self._task_state(task.path, "running")
                try:
                    filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(
                        merge_candidates[0].path,
                        settings,
                        outp.suffix,
                        log_cb=self._log,
                    )
                    audio_processing = self.ffmpeg.has_audio_processing(settings)
                    trim_args = self.ffmpeg.build_trim_args(settings, log_cb=self._log)
                    fast_copy_ok, reason = self.ffmpeg.merge_copy_allowed(
                        [task.path for task in merge_candidates],
                        outp.suffix,
                        self.media_info,
                        filters_used,
                        audio_processing,
                        trim_args,
                    )
                    allow_fast = settings.fast_copy and fast_copy_ok
                    if settings.fast_copy and not fast_copy_ok:
                        self._log("WARN", f"Fast copy (merge) вимкнено: {reason}")
                    cmd, list_path = self.ffmpeg.build_merge_command(
                        [task.path for task in merge_candidates],
                        outp,
                        settings,
                        self.media_info,
                        allow_fast,
                        log_cb=self._log,
                    )
                    try:
                        rc = self._run_ffmpeg(
                            cmd,
                            merge_duration,
                            done_duration,
                            total_duration,
                            done_files,
                            total_files,
                            total_start,
                        )
                    finally:
                        try:
                            Path(list_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                    success = rc == 0 and outp.exists()
                    message = "" if success else f"Помилка merge (код {rc})"
                    if success:
                        self._log("OK", f"Готово (merge): {outp.name}")
                    else:
                        self._log("ERROR", message)
                    for task in merge_candidates:
                        self._task_state(task.path, "success" if success else "failed", message, str(outp))
                        done_files += 1
                        done_duration += self._task_duration(task)
                        run_results.append(
                            {
                                "path": str(task.path),
                                "status": "success" if success else "failed",
                                "message": message,
                                "output_path": str(outp),
                            }
                        )
                except FileNotFoundError:
                    self._log("ERROR", "FFmpeg не знайдено під час запуску.")
                    self.stop_event.set()
                except Exception as exc:
                    self._log("ERROR", f"Merge помилка: {exc}")
                    for task in merge_candidates:
                        self._task_state(task.path, "failed", str(exc))
                        done_files += 1
                        done_duration += self._task_duration(task)
                        run_results.append(
                            {
                                "path": str(task.path),
                                "status": "failed",
                                "message": str(exc),
                                "output_path": "",
                            }
                        )

        for index, task in enumerate(tasks, start=1):
            if self.stop_event.is_set():
                self._log("WARN", "Зупинено користувачем.")
                break
            if task.path in merged_video_paths:
                continue

            settings_for_task = self._effective_settings(task, settings)
            valid, message = self._validate_operation(task, settings_for_task)
            if not valid:
                self._log("WARN", f"{task.path.name}: {message}")
                self._task_state(task.path, "failed", message)
                done_files += 1
                run_results.append({"path": str(task.path), "status": "failed", "message": message, "output_path": ""})
                self._emit("progress", None, 0.0, None, None, done_files / total_files, None)
                continue

            if not task.path.exists():
                self._log("ERROR", f"Файл не знайдено: {task.path}")
                self._task_state(task.path, "failed", "Файл не знайдено")
                done_files += 1
                run_results.append(
                    {"path": str(task.path), "status": "failed", "message": "Файл не знайдено", "output_path": ""}
                )
                self._emit("progress", None, 0.0, None, None, done_files / total_files, None)
                continue

            outp = self._resolve_output_path(task, settings_for_task, out_dir, index)
            duration = self._task_duration(task) if task.media_type == "video" else None

            if settings_for_task.skip_existing and outp.exists() and not settings_for_task.overwrite:
                self._log("INFO", f"Пропускаю, файл вже існує: {outp.name}")
                self._task_state(task.path, "skipped", "Вихідний файл вже існує", str(outp))
                done_files += 1
                if duration:
                    done_duration += duration
                run_results.append(
                    {
                        "path": str(task.path),
                        "status": "skipped",
                        "message": "Вихідний файл вже існує",
                        "output_path": str(outp),
                    }
                )
                self._emit("progress", None, 0.0, None, None, done_files / total_files, None)
                continue

            self._emit("status", f"Обробка: {task.path.name}")
            self._task_state(task.path, "running")
            self._log("INFO", f"→ {task.path.name} ({task.media_type}) ==> {outp.name}")

            status = "failed"
            result_message = ""
            result_output = ""
            try:
                op = settings_for_task.operation
                if op in {"convert", "subtitle_burn"}:
                    if task.media_type == "video":
                        info = self.media_info.get(task.path)
                        filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(
                            task.path,
                            settings_for_task,
                            outp.suffix,
                            log_cb=self._log,
                        )
                        audio_processing = self.ffmpeg.has_audio_processing(settings_for_task) or bool(
                            settings_for_task.replace_audio_path.strip()
                        )
                        fast_copy_ok, reason = self.ffmpeg.fast_copy_allowed(
                            task.path,
                            outp.suffix,
                            info,
                            filters_used,
                            audio_processing,
                        )
                        allow_fast = settings_for_task.fast_copy and fast_copy_ok
                        if settings_for_task.fast_copy and not fast_copy_ok:
                            self._log("WARN", f"Fast copy вимкнено для {task.path.name}: {reason}")
                        cmd = self.ffmpeg.build_video_command(
                            task.path,
                            outp,
                            settings_for_task,
                            info,
                            allow_fast,
                            log_cb=self._log,
                        )
                    else:
                        cmd = self.ffmpeg.build_image_command(task.path, outp, settings_for_task, log_cb=self._log)
                    rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                    success = rc == 0 and outp.exists()
                    if success:
                        status = "success"
                        result_output = str(outp)
                        self._log("OK", f"Готово: {outp.name}")
                        self._task_state(task.path, "success", "", str(outp))
                    else:
                        result_message = f"Помилка конвертації: {task.path.name} (код {rc})"
                        self._log("ERROR", result_message)
                        self._task_state(task.path, "failed", result_message)
                elif op == "audio_only":
                    if settings_for_task.split_chapters:
                        success, details = self._process_audio_chapters(
                            task,
                            settings_for_task,
                            out_dir,
                            index,
                            done_duration,
                            total_duration,
                            done_files,
                            total_files,
                            total_start,
                        )
                        if success:
                            status = "success"
                            result_output = details
                            self._task_state(task.path, "success", "", details)
                        else:
                            result_message = details
                            self._log("ERROR", details)
                            self._task_state(task.path, "failed", details)
                    else:
                        cmd = self.ffmpeg.build_audio_command(task.path, outp, settings_for_task, log_cb=self._log)
                        rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                        success = rc == 0 and outp.exists()
                        if success:
                            status = "success"
                            result_output = str(outp)
                            self._log("OK", f"Готово: {outp.name}")
                            self._task_state(task.path, "success", "", str(outp))
                        else:
                            result_message = f"Помилка конвертації: {task.path.name} (код {rc})"
                            self._log("ERROR", result_message)
                            self._task_state(task.path, "failed", result_message)
                elif op == "auto_subtitle":
                    rc = self.transcriber.generate(task.path, outp, settings_for_task, log_cb=self._log)
                    success = rc == 0 and outp.exists()
                    if success:
                        status = "success"
                        result_output = str(outp)
                        self._log("OK", f"Субтитри створено: {outp.name}")
                        self._task_state(task.path, "success", "", str(outp))
                    else:
                        result_message = f"Помилка створення субтитрів: {task.path.name} (код {rc})"
                        self._log("ERROR", result_message)
                        self._task_state(task.path, "failed", result_message)
                elif op == "subtitle_extract":
                    cmd = self.ffmpeg.build_subtitle_extract_command(task.path, outp, settings_for_task)
                    rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                    success = rc == 0 and outp.exists()
                    if success:
                        status = "success"
                        result_output = str(outp)
                        self._log("OK", f"Готово: {outp.name}")
                        self._task_state(task.path, "success", "", str(outp))
                    else:
                        result_message = f"Помилка конвертації: {task.path.name} (код {rc})"
                        self._log("ERROR", result_message)
                        self._task_state(task.path, "failed", result_message)
                elif op == "thumbnail":
                    cmd = self.ffmpeg.build_thumbnail_command(task.path, outp, settings_for_task, log_cb=self._log)
                    rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                    success = rc == 0 and outp.exists()
                    if success:
                        status = "success"
                        result_output = str(outp)
                        self._log("OK", f"Готово: {outp.name}")
                        self._task_state(task.path, "success", "", str(outp))
                    else:
                        result_message = f"Помилка конвертації: {task.path.name} (код {rc})"
                        self._log("ERROR", result_message)
                        self._task_state(task.path, "failed", result_message)
                elif op == "contact_sheet":
                    cmd = self.ffmpeg.build_contact_sheet_command(task.path, outp, settings_for_task)
                    rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                    success = rc == 0 and outp.exists()
                    if success:
                        status = "success"
                        result_output = str(outp)
                        self._log("OK", f"Готово: {outp.name}")
                        self._task_state(task.path, "success", "", str(outp))
                    else:
                        result_message = f"Помилка конвертації: {task.path.name} (код {rc})"
                        self._log("ERROR", result_message)
                        self._task_state(task.path, "failed", result_message)
                else:
                    raise ValueError(f"Непідтримувана операція: {op}")
            except FileNotFoundError:
                self._log("ERROR", "FFmpeg не знайдено під час запуску. Перевір шлях до ffmpeg.")
                self._task_state(task.path, "failed", "FFmpeg не знайдено")
                result_message = "FFmpeg не знайдено"
                break
            except Exception as exc:
                self._log("ERROR", f"Несподівана помилка: {exc}")
                self._task_state(task.path, "failed", str(exc))
                result_message = str(exc)

            done_files += 1
            if duration:
                done_duration += duration
            run_results.append(
                {
                    "path": str(task.path),
                    "status": status,
                    "message": result_message,
                    "output_path": result_output,
                }
            )

        failed_count = sum(1 for item in run_results if item["status"] == "failed")
        hook_env.update(
            {
                "MC_STOPPED": "1" if self.stop_event.is_set() else "0",
                "MC_FAILED_COUNT": str(failed_count),
            }
        )
        self._run_hook(settings.after_hook, "after", env=hook_env)
        self._emit_run_summary(
            settings=settings,
            out_dir=out_dir,
            total_files=total_files,
            stopped=self.stop_event.is_set(),
            results=run_results,
            started_at=total_start,
        )
        self._emit("done", self.stop_event.is_set())

    def _consume_stderr(self, pipe) -> None:
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
                if key in {"out_time_ms", "out_time_us"}:
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
