import contextlib
import os
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from queue import Queue

from app.constants import PROGRESS_THROTTLE_SEC
from app.models import ConversionSettings, MediaInfo, TaskItem, TaskStatus
from services.cloud_upload_service import CloudUploadError, CloudUploadService
from services.ffmpeg_service import FfmpegService, parse_progress_line
from services.security_service import secure_delete, write_checksum_sidecar
from services.smart_convert_service import apply_smart_settings, parse_ab_crfs, recommend_settings
from services.text_conversion_service import convert_text_file
from services.transcription_service import TranscriptionService
from services.validation_service import operation_supports_media
from utils.files import build_merge_output_path, build_output_path, sanitize_file_stem
from utils.formatting import format_bytes, format_time, parse_ffmpeg_time


def _estimate_eta(elapsed: float, progress: float) -> float | None:
    if progress <= 0:
        return None
    total = elapsed / progress
    return max(total - elapsed, 0.0)


class ConverterService:
    SKIP_RC = -32001

    def __init__(self, ffmpeg: FfmpegService, event_queue: Queue, transcriber: TranscriptionService | None = None):
        self.ffmpeg = ffmpeg
        self.queue = event_queue
        self.transcriber = transcriber or TranscriptionService()
        self.cloud_uploader = CloudUploadService()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.skip_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.current_proc: subprocess.Popen | None = None
        self.child_services: list[ConverterService] = []
        self.progress_task_path: Path | None = None
        self.current_output_path: Path | None = None
        self.media_info: dict[Path, MediaInfo] = {}
        self.prefetched_media_info: dict[Path, MediaInfo] = {}
        self.prefetch_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="converter-ffprobe")

    def _result_output_paths(self, result_output: str) -> list[Path]:
        paths: list[Path] = []
        for raw in str(result_output or "").split(";"):
            text = raw.strip()
            if not text:
                continue
            path = Path(text).expanduser()
            if path.exists() and path.is_file():
                paths.append(path)
        return paths

    def _post_process_success(self, task: TaskItem, settings: ConversionSettings, result_output: str) -> None:
        output_paths = self._result_output_paths(result_output)
        if not output_paths:
            return
        checksum_algorithm = str(settings.checksum_algorithm or "none").lower()
        for output_path in output_paths:
            if checksum_algorithm in {"md5", "sha256"}:
                try:
                    sidecar = write_checksum_sidecar(output_path, checksum_algorithm)
                    self._log("OK", f"{checksum_algorithm.upper()} записано: {sidecar.name}")
                except Exception as exc:
                    self._log("WARN", f"Не вдалося записати checksum для {output_path.name}: {exc}")
            if settings.cloud_upload_enabled:
                try:
                    self.cloud_uploader.upload(output_path, settings, log_cb=self._log)
                    self._log("OK", f"Cloud upload готовий: {output_path.name}")
                except CloudUploadError as exc:
                    self._log("WARN", f"Cloud upload помилка для {output_path.name}: {exc}")
            if settings.smart_integrity_check:
                if task.media_type == "text":
                    self._log("WARN", f"Integrity check пропущено для текстового файлу: {output_path.name}")
                else:
                    ok, details = self.ffmpeg.check_media_integrity(output_path)
                    if ok:
                        self._log("OK", f"Integrity check OK: {output_path.name}")
                    else:
                        self._log("WARN", f"Integrity check failed for {output_path.name}: {details or 'decode error'}")
            if task.media_type == "video" and settings.smart_quality_metric in {"ssim", "vmaf"}:
                ok, score, details = self.ffmpeg.measure_quality(task.path, output_path, settings.smart_quality_metric)
                label = settings.smart_quality_metric.upper()
                if ok and score is not None:
                    self._log("OK", f"{label}: {score:.4f} для {output_path.name}")
                elif ok:
                    self._log("OK", f"{label} check завершено для {output_path.name}")
                else:
                    self._log("WARN", f"{label} check failed for {output_path.name}: {details or 'metric unavailable'}")
        if settings.secure_delete_original:
            try:
                source = task.path.expanduser()
                if source.exists() and source.is_file() and all(source.resolve() != path.resolve() for path in output_paths):
                    secure_delete(source)
                    self._log("WARN", f"Secure delete виконано для оригіналу: {source.name}")
            except Exception as exc:
                self._log("WARN", f"Secure delete не виконано для {task.path.name}: {exc}")

    def start(self, tasks: list[TaskItem], settings: ConversionSettings, out_dir: Path) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.pause_event.clear()
        self.skip_event.clear()
        self.thread = threading.Thread(target=self._run, args=(tasks, settings, out_dir), daemon=True)
        self.thread.start()

    def _has_gpu_encoder(self) -> bool:
        caps = getattr(self.ffmpeg, "encoder_caps", set()) or set()
        return bool({"h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "hevc_qsv", "av1_qsv", "h264_amf", "hevc_amf", "av1_amf"} & caps)

    def conversion_worker_limit(self) -> int:
        return 2 if self._has_gpu_encoder() else 1

    def _create_child_service(self, result_queue: Queue) -> "ConverterService":
        return ConverterService(self.ffmpeg, result_queue, self.transcriber)

    def stop(self) -> None:
        self.stop_event.set()
        for child in list(self.child_services):
            child.stop()
        self._terminate_process(self.current_proc)

    def pause(self) -> None:
        self.pause_event.set()
        for child in list(self.child_services):
            child.pause()
        self._set_process_suspended(True)

    def resume(self) -> None:
        for child in list(self.child_services):
            child.resume()
        self._set_process_suspended(False)
        self.pause_event.clear()

    def skip_current(self) -> None:
        self.skip_event.set()
        for child in list(self.child_services):
            child.skip_current()
        self._terminate_process(self.current_proc)

    def _terminate_process(self, proc: subprocess.Popen | None, timeout: float = 3.0) -> None:
        if not proc or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                proc.wait(timeout=1.0)
            except Exception:
                pass
        except Exception:
            pass

    def _wait_if_paused(self) -> None:
        emitted = False
        while self.pause_event.is_set() and not self.stop_event.is_set() and not self.skip_event.is_set():
            if not emitted:
                self._emit("status", "Пауза. Очікую Resume...")
                emitted = True
            time.sleep(0.2)

    def _set_process_suspended(self, suspend: bool) -> None:
        proc = self.current_proc
        if not proc or proc.poll() is not None:
            return
        if os.name == "nt":
            self._set_windows_process_suspended(proc.pid, suspend)
            return
        with contextlib.suppress(Exception):
            os.kill(proc.pid, signal.SIGSTOP if suspend else signal.SIGCONT)

    def _set_windows_process_suspended(self, pid: int, suspend: bool) -> None:
        try:
            import ctypes
            from ctypes import wintypes

            class ThreadEntry32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ThreadID", wintypes.DWORD),
                    ("th32OwnerProcessID", wintypes.DWORD),
                    ("tpBasePri", wintypes.LONG),
                    ("tpDeltaPri", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
            if snapshot == wintypes.HANDLE(-1).value:
                return
            entry = ThreadEntry32()
            entry.dwSize = ctypes.sizeof(ThreadEntry32)
            has_thread = kernel32.Thread32First(snapshot, ctypes.byref(entry))
            while has_thread:
                if entry.th32OwnerProcessID == pid:
                    thread = kernel32.OpenThread(0x0002, False, entry.th32ThreadID)
                    if thread:
                        try:
                            if suspend:
                                kernel32.SuspendThread(thread)
                            else:
                                while kernel32.ResumeThread(thread) > 1:
                                    pass
                        finally:
                            kernel32.CloseHandle(thread)
                has_thread = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
            kernel32.CloseHandle(snapshot)
        except Exception:
            pass

    def _emit(self, event: str, *payload) -> None:
        if event == "progress" and self.progress_task_path is not None:
            self.queue.put(("progress_for", self.progress_task_path, *payload))
            return
        self.queue.put((event, *payload))

    def _log(self, level: str, msg: str) -> None:
        self._emit("log", level, msg)

    def _task_state(self, task_path: Path, status: str, message: str = "", output_path: str = "") -> None:
        self._emit("task_state", task_path, status, message, output_path)

    def _effective_settings(self, task: TaskItem, defaults: ConversionSettings) -> ConversionSettings:
        base = task.resolved_settings or defaults
        info = self.media_info.get(task.path)
        return apply_smart_settings(base, info, media_type=task.media_type, source_path=task.path)

    def _can_use_two_pass(self, settings: ConversionSettings, cmd: list[str], allow_fast: bool) -> bool:
        if allow_fast or not settings.smart_two_pass or not settings.target_size_mb:
            return False
        joined = " ".join(cmd)
        if "-b:v" not in cmd or "-c:v" not in cmd:
            return False
        unsupported = {"h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "hevc_qsv", "av1_qsv", "h264_amf", "hevc_amf", "av1_amf", "prores_ks"}
        return not any(encoder in joined for encoder in unsupported)

    def _cleanup_passlog(self, passlog: Path) -> None:
        for candidate in passlog.parent.glob(passlog.name + "*"):
            with contextlib.suppress(Exception):
                candidate.unlink(missing_ok=True)

    def _run_video_command(
        self,
        cmd: list[str],
        outp: Path,
        settings: ConversionSettings,
        duration: float | None,
        done_duration: float,
        total_duration: float,
        done_files: int,
        total_files: int,
        total_start: float,
        allow_fast: bool,
    ) -> int:
        if not self._can_use_two_pass(settings, cmd, allow_fast):
            return self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
        passlog = outp.with_suffix(outp.suffix + ".ffmpeg2pass")
        pass1, pass2 = self.ffmpeg.build_two_pass_commands(cmd, passlog)
        self._log("INFO", f"Two-pass encoding: pass 1/2 для {outp.name}")
        rc = self._run_ffmpeg(pass1, duration, done_duration, total_duration, done_files, total_files, total_start)
        if rc == 0 and not self.stop_event.is_set():
            self._log("INFO", f"Two-pass encoding: pass 2/2 для {outp.name}")
            rc = self._run_ffmpeg(pass2, duration, done_duration, total_duration, done_files, total_files, total_start)
        self._cleanup_passlog(passlog)
        return rc

    def _run_ab_samples(self, task: TaskItem, outp: Path, settings: ConversionSettings, info: MediaInfo | None) -> None:
        if not settings.smart_ab_test or task.media_type != "video":
            return
        crfs = parse_ab_crfs(settings.smart_ab_crfs)
        if not crfs:
            return
        sample_duration = max(1, min(120, int(settings.smart_ab_duration)))
        start = settings.trim_start if settings.trim_start is not None else 0.0
        end = start + sample_duration
        self._log("INFO", f"A/B samples: {', '.join(str(crf) for crf in crfs)} CRF, {sample_duration}s")
        for crf in crfs:
            if self.stop_event.is_set() or self.skip_event.is_set():
                return
            sample_path = outp.with_name(f"{outp.stem}_ab_crf{crf}{outp.suffix}")
            sample_settings = replace(
                settings,
                crf=crf,
                target_size_mb=None,
                smart_ab_test=False,
                smart_two_pass=False,
                overwrite=True,
                trim_start=start,
                trim_end=end,
            )
            cmd = self.ffmpeg.build_video_command(task.path, sample_path, sample_settings, info, False, log_cb=self._log)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=max(60, sample_duration * 30))
            except Exception as exc:
                self._log("WARN", f"A/B sample CRF {crf} failed: {exc}")
                continue
            if result.returncode == 0 and sample_path.exists():
                self._log("OK", f"A/B sample готовий: {sample_path.name}")
            else:
                details = (result.stderr or result.stdout or "").strip()
                self._log("WARN", f"A/B sample CRF {crf} failed: {details[-300:]}")

    def _task_duration(self, task: TaskItem) -> float:
        info = self.media_info.get(task.path)
        return info.duration or 0.0 if info else 0.0

    def _log_media_info(self, task: TaskItem, info: MediaInfo) -> None:
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

    def _run_hook(self, command: str, stage: str, *, env: dict[str, str]) -> None:
        command = command.strip()
        if not command:
            return
        if os.environ.get("MEDIA_CONVERTER_ENABLE_HOOKS", "").strip().lower() not in {"1", "true", "yes"}:
            self._log("WARN", f"Hook {stage} skipped because MEDIA_CONVERTER_ENABLE_HOOKS is not enabled.")
            return
        self._log("INFO", f"Hook {stage}: {command}")
        try:
            import shlex
            cmd_list = command if os.name == 'nt' else shlex.split(command)
            result = subprocess.run(cmd_list, shell=False, env=env, capture_output=True, text=True)
        except Exception as e:
            self._log('WARN', f'Hook {stage} failed: {e}')
            return
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
        results: list[dict[str, str]],
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
                "out_text_fmt": settings.out_text_format,
                "normalize_audio": settings.normalize_audio,
                "audio_track_index": settings.audio_track_index,
                "replace_audio_path": settings.replace_audio_path,
                "split_chapters": settings.split_chapters,
                "output_template": settings.output_template,
                "performance_profile": settings.performance_profile,
                "target_size_mb": settings.target_size_mb,
                "cpu_load_limit": settings.cpu_load_limit,
                "gpu_load_limit": settings.gpu_load_limit,
            },
        }
        self._emit("run_summary", summary)

    def _validate_operation(self, task: TaskItem, settings: ConversionSettings) -> tuple[bool, str]:
        if not operation_supports_media(settings.operation, task.media_type):
            return False, "Операція не підтримує тип цього файлу"
        return True, ""

    def _total_duration_for(self, tasks: list[TaskItem], defaults: ConversionSettings) -> float:
        total_duration = 0.0
        for task in tasks:
            settings = self._effective_settings(task, defaults)
            if settings.operation in {"convert", "audio_only", "subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet", "auto_subtitle"}:
                total_duration += self._task_duration(task)
        return total_duration

    def _can_run_parallel(self, tasks: list[TaskItem], defaults: ConversionSettings) -> bool:
        if self.conversion_worker_limit() < 2 or len(tasks) < 2:
            return False
        for task in tasks:
            settings = self._effective_settings(task, defaults)
            if settings.merge or settings.split_chapters or settings.operation == "auto_subtitle":
                return False
            if settings.operation not in {"convert", "subtitle_burn", "audio_only", "subtitle_extract", "thumbnail", "contact_sheet"}:
                return False
        return True

    def _current_cpu_load(self) -> float:
        try:
            import psutil  # type: ignore

            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return 0.0

    def _current_gpu_load(self) -> float:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=0.4,
            )
            if result.returncode != 0:
                return 0.0
            values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
            return max(values) if values else 0.0
        except Exception:
            return 0.0

    def _wait_for_resource_budget(self, settings: ConversionSettings) -> None:
        logged = False
        while not self.stop_event.is_set():
            cpu = self._current_cpu_load()
            gpu = self._current_gpu_load()
            cpu_over = cpu >= max(1, min(100, settings.cpu_load_limit))
            gpu_over = gpu > 0 and gpu >= max(1, min(100, settings.gpu_load_limit))
            if not cpu_over and not gpu_over:
                return
            if not logged:
                self._log(
                    "WARN",
                    f"Load limit reached; waiting before next task (CPU {cpu:.0f}%/{settings.cpu_load_limit}%, GPU {gpu:.0f}%/{settings.gpu_load_limit}%).",
                )
                logged = True
            time.sleep(1.0)

    def _run_parallel_tasks(
        self,
        tasks: list[TaskItem],
        settings: ConversionSettings,
        out_dir: Path,
        total_files: int,
        total_start: float,
    ) -> list[dict[str, str]]:
        worker_count = min(self.conversion_worker_limit(), len(tasks))
        self._log("INFO", f"Parallel conversion enabled: {worker_count} workers")
        result_queue: Queue[tuple] = Queue()
        run_results: list[dict[str, str]] = []
        completed_paths: set[Path] = set()
        progress_by_path: dict[Path, float] = {task.path: 0.0 for task in tasks}

        def run_child(task: TaskItem, index: int) -> None:
            child = self._create_child_service(result_queue)
            child.prefetched_media_info = dict(self.media_info)
            child.progress_task_path = task.path
            child_settings = replace(settings, before_hook="", after_hook="", merge=False)
            child_task = task
            if task.resolved_settings is not None:
                child_task = replace(
                    task,
                    resolved_settings=replace(task.resolved_settings, before_hook="", after_hook="", merge=False),
                )
            self.child_services.append(child)
            try:
                self._wait_for_resource_budget(child_task.resolved_settings or child_settings)
                child._run([child_task], child_settings, out_dir, start_index=index)
            finally:
                with contextlib.suppress(ValueError):
                    self.child_services.remove(child)

        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="converter-worker") as executor:
            futures = [executor.submit(run_child, task, index) for index, task in enumerate(tasks, start=1)]
            while futures:
                self._wait_if_paused()
                if self.stop_event.is_set():
                    for child in list(self.child_services):
                        child.stop()
                while not result_queue.empty():
                    event = result_queue.get()
                    etype = event[0]
                    if etype in {"log", "status", "task_state"}:
                        self._emit(*event)
                        if etype == "task_state":
                            _, path, status, _message, _output_path = event
                            if status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}:
                                completed_paths.add(path)
                                progress_by_path[path] = 1.0
                    elif etype == "progress_for":
                        if len(event) >= 9:
                            _, path, file_pct, _out_time, _duration, file_eta, _child_total, _child_eta, speed = event
                        else:
                            _, path, file_pct, _out_time, _duration, file_eta, _child_total, _child_eta = event
                            speed = None
                        if path is not None and file_pct is not None:
                            progress_by_path[path] = max(progress_by_path.get(path, 0.0), float(file_pct))
                            total_pct = sum(progress_by_path.values()) / max(total_files, 1)
                            elapsed = time.time() - total_start
                            total_eta = _estimate_eta(elapsed, total_pct) if total_pct else None
                            self._emit("task_progress", path, file_pct, file_eta, speed, total_pct, total_eta)
                    elif etype == "run_summary":
                        _, summary = event
                        if isinstance(summary, dict):
                            run_results.extend(summary.get("results", []))
                    elif etype in {"set_total", "done"}:
                        continue
                    else:
                        self._emit(*event)

                futures = [future for future in futures if not future.done()]
                time.sleep(0.05)

            while not result_queue.empty():
                event = result_queue.get()
                if event[0] == "run_summary" and isinstance(event[1], dict):
                    run_results.extend(event[1].get("results", []))
                elif event[0] not in {"set_total", "done"}:
                    self._emit(*event)

        return run_results

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
    ) -> tuple[bool, str]:
        info = self.media_info.get(task.path)
        if not info or not info.chapters:
            return False, "У файлі немає глав для split by chapters"

        base_output = self._resolve_output_path(task, settings, out_dir, index)
        chapter_outputs: list[str] = []
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
            cmd = self.ffmpeg.build_audio_command(task.path, outp, chapter_settings, duration=chapter_duration, log_cb=self._log)
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

    def _run(self, tasks: list[TaskItem], settings: ConversionSettings, out_dir: Path, *, start_index: int = 1) -> None:
        if not tasks:
            self._log("WARN", "Черга порожня.")
            self._emit("done", True)
            return

        needs_ffmpeg = any(
            task.media_type != "text" or self._effective_settings(task, settings).operation != "convert"
            for task in tasks
        )
        if needs_ffmpeg and not self.ffmpeg.ffmpeg_path:
            self._log("ERROR", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.")
            self._emit("done", True)
            return

        out_dir.mkdir(parents=True, exist_ok=True)
        total_files = len(tasks)
        done_files = 0
        total_start = time.time()
        run_results: list[dict[str, str]] = []

        self.media_info.clear()
        self.media_info.update(self.prefetched_media_info)
        if self.ffmpeg.ffprobe_path:
            missing_probe: list[Path] = []
            for task in tasks:
                self._task_state(task.path, TaskStatus.ANALYZING)
                if task.media_type == "text":
                    self._task_state(task.path, TaskStatus.READY)
                    continue
                info = self.media_info.get(task.path)
                if info is None:
                    missing_probe.append(task.path)
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
                if info:
                    self._task_state(task.path, TaskStatus.READY)
            if missing_probe:
                probed = self.ffmpeg.probe_media_batch(missing_probe, max_workers=4)
                for task in tasks:
                    if task.path not in missing_probe:
                        continue
                    info = probed.get(task.path)
                    if info is not None:
                        self.media_info[task.path] = info
                        self._log_media_info(task, info)
                    self._task_state(task.path, TaskStatus.READY)
        else:
            if needs_ffmpeg:
                self._log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")
            for task in tasks:
                self._task_state(task.path, TaskStatus.READY)

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
            outp = build_merge_output_path(
                out_dir,
                settings.merge_name,
                settings.out_video_format,
                overwrite=settings.overwrite,
                skip_existing=settings.skip_existing,
            )

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
                    _filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(
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
                        with contextlib.suppress(Exception):
                            Path(list_path).unlink(missing_ok=True)
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

        remaining_tasks = [task for task in tasks if task.path not in merged_video_paths]
        parallel_results: list[dict[str, str]] | None = None
        if not merge_enabled and self._can_run_parallel(remaining_tasks, settings):
            parallel_results = self._run_parallel_tasks(remaining_tasks, settings, out_dir, total_files, total_start)
            run_results.extend(parallel_results)

        if parallel_results is None:
            for index, task in enumerate(tasks, start=start_index):
                if self.stop_event.is_set():
                    self._log("WARN", "Зупинено користувачем.")
                    break
                self._wait_if_paused()
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
                duration = self._task_duration(task) if task.media_type in {"video", "audio"} else None

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

                self._wait_for_resource_budget(settings_for_task)
                self._emit("status", f"Обробка: {task.path.name}")
                self._task_state(task.path, TaskStatus.RUNNING)
                self._log("INFO", f"→ {task.path.name} ({task.media_type}) ==> {outp.name}")

                status = TaskStatus.FAILED
                result_message = ""
                result_output = ""
                try:
                    op = settings_for_task.operation
                    if op in {"convert", "subtitle_burn"}:
                        if task.media_type == "video":
                            info = self.media_info.get(task.path)
                            _filter_arg, _, _, _, filters_used = self.ffmpeg.build_video_filter_spec(
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
                                allow_remux=settings_for_task.smart_convert_enabled and settings_for_task.smart_reencode_detection,
                            )
                            if (
                                settings_for_task.smart_convert_enabled
                                and settings_for_task.smart_reencode_detection
                                and fast_copy_ok
                                and not self.ffmpeg.source_matches_codec_choice(info, settings_for_task.video_codec, outp.suffix)
                            ):
                                fast_copy_ok = False
                                reason = "Smart Convert обрав інший кодек"
                            allow_fast = settings_for_task.fast_copy and fast_copy_ok
                            if settings_for_task.fast_copy and not fast_copy_ok:
                                self._log("WARN", f"Fast copy вимкнено для {task.path.name}: {reason}")
                            if settings_for_task.smart_convert_enabled:
                                rec = recommend_settings(settings_for_task, info, task.path)
                                self._log("INFO", f"Smart Convert: {rec.reason} -> {rec.video_codec}, CRF {rec.crf}, preset {rec.preset}")
                            cmd = self.ffmpeg.build_video_command(
                                task.path,
                                outp,
                                settings_for_task,
                                info,
                                allow_fast,
                                log_cb=self._log,
                            )
                            self._run_ab_samples(task, outp, settings_for_task, info)
                        elif task.media_type == "image":
                            cmd = self.ffmpeg.build_image_command(task.path, outp, settings_for_task, log_cb=self._log)
                        elif task.media_type == "audio":
                            cmd = self.ffmpeg.build_audio_command(task.path, outp, settings_for_task, duration=duration, log_cb=self._log)
                        elif task.media_type == "subtitle":
                            cmd = self.ffmpeg.build_subtitle_file_command(task.path, outp, settings_for_task)
                        elif task.media_type == "text":
                            convert_text_file(task.path, outp, settings_for_task.out_text_format)
                            cmd = []
                        else:
                            raise ValueError(f"Невідомий тип файлу: {task.media_type}")
                        if task.media_type == "text":
                            rc = 0
                            self._emit(
                                "progress",
                                1.0,
                                None,
                                None,
                                None,
                                (done_files + 1) / max(total_files, 1),
                                None,
                            )
                        elif task.media_type == "video" and op in {"convert", "subtitle_burn"}:
                            rc = self._run_video_command(
                                cmd,
                                outp,
                                settings_for_task,
                                duration,
                                done_duration,
                                total_duration,
                                done_files,
                                total_files,
                                total_start,
                                allow_fast,
                            )
                        else:
                            rc = self._run_ffmpeg(cmd, duration, done_duration, total_duration, done_files, total_files, total_start)
                        if self.stop_event.is_set():
                            status = TaskStatus.CANCELLED
                            result_message = "Скасовано користувачем"
                            self._task_state(task.path, TaskStatus.CANCELLED, result_message)
                            success = False
                        else:
                            success = rc == 0 and outp.exists()
                        if success:
                            status = TaskStatus.SUCCESS
                            result_output = str(outp)
                            self._log("OK", f"Готово: {outp.name}")
                            self._task_state(task.path, TaskStatus.SUCCESS, "", str(outp))
                        elif status != TaskStatus.CANCELLED:
                            result_message = f"Помилка конвертації: {task.path.name} (код {rc})"
                            self._log("ERROR", result_message)
                            self._task_state(task.path, TaskStatus.FAILED, result_message)
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
                            cmd = self.ffmpeg.build_audio_command(task.path, outp, settings_for_task, duration=duration, log_cb=self._log)
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

                if self.skip_event.is_set():
                    self.skip_event.clear()
                    status = "skipped"
                    result_message = "Пропущено користувачем"
                    result_output = ""
                    self._log("WARN", f"Пропущено користувачем: {task.path.name}")
                    self._task_state(task.path, "skipped", result_message)

                if status == TaskStatus.SUCCESS or status == "success":
                    self._post_process_success(task, settings_for_task, result_output)

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
        cmd: list[str],
        duration: float | None,
        total_done: float,
        total_duration: float,
        done_files: int,
        total_files: int,
        total_start: float,
    ) -> int:
        if len(cmd) < 2:
            return -1
        output_path = Path(cmd[-1])
        output_existed_before = output_path.exists()
        cmd_with_progress = [*cmd[:2], "-progress", "pipe:1", "-nostats", "-hide_banner", *cmd[2:]]
        proc = subprocess.Popen(
            cmd_with_progress,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,
        )
        self.current_proc = proc
        self.current_output_path = output_path
        file_start = time.time()

        assert proc.stderr is not None
        err_thread = threading.Thread(target=self._consume_stderr, args=(proc.stderr,), daemon=True)
        err_thread.start()

        out_time = 0.0
        speed = None
        last_progress_emit = 0.0
        pending_progress: tuple[float | None, float, float | None, float | None, float, float | None, float | None] | None = None
        if proc.stdout is not None:
            for line in proc.stdout:
                self._wait_if_paused()
                if self.skip_event.is_set():
                    self._terminate_process(proc)
                    break
                if self.stop_event.is_set():
                    self._terminate_process(proc)
                    break
                parsed_line = parse_progress_line(line)
                if not parsed_line:
                    continue
                key, value = next(iter(parsed_line.items()))
                if value in {"", "N/A"}:
                    continue
                if key in {"out_time_ms", "out_time_us"}:
                    with contextlib.suppress(ValueError):
                        out_time = int(value) / 1_000_000
                elif key == "out_time":
                    parsed = parse_ffmpeg_time(value)
                    if parsed is not None:
                        out_time = parsed
                elif key == "speed":
                    with contextlib.suppress(ValueError):
                        speed = float(value.replace("x", ""))

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

                pending_progress = (file_pct, out_time, duration, file_eta, total_pct, total_eta, speed)
                now = time.monotonic()
                if now - last_progress_emit >= PROGRESS_THROTTLE_SEC or total_pct >= 1.0:
                    self._emit("progress", *pending_progress)
                    last_progress_emit = now
                    pending_progress = None

        if pending_progress is not None:
            self._emit("progress", *pending_progress)
        try:
            rc = proc.wait()
        finally:
            err_thread.join(timeout=0.2)
            self.current_proc = None
            self.current_output_path = None
        if (self.skip_event.is_set() or self.stop_event.is_set()) and not output_existed_before:
            with contextlib.suppress(Exception):
                output_path.unlink(missing_ok=True)
        if self.skip_event.is_set():
            return self.SKIP_RC
        return rc
