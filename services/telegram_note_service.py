"""Telegram Video Note («Кружечки») Generator Service.

Generates Telegram-compliant round video messages:
- Exact 1:1 square aspect ratio
- Maximum 60 seconds duration
- H.264 video codec with yuv420p pixel format
- AAC audio codec (44100 Hz, stereo/mono)
- Faststart flag for instant streaming in Telegram
- Crop modes: Center crop (1:1) and Blurred background padding
- Optional circular vignette/matte
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtWidgets

from app.constants import VIDEO_EXTS
from app.models import TaskItem, TaskStatus
from services.background_job import BackgroundJob, JobContext

logger = logging.getLogger(__name__)

TELEGRAM_MAX_DURATION = 60.0
TELEGRAM_DEFAULT_RES = 480
TELEGRAM_DEFAULT_BITRATE = "1400k"


class TelegramNoteService(BackgroundJob):
    """Processes videos into Telegram-compliant 1:1 Video Notes."""

    fileInspected = QtCore.Signal(dict)
    renderFinished = QtCore.Signal(str, bool, str)

    def __init__(self, backend=None):
        super().__init__(backend)
        self.backend = backend
        self._ffmpeg_path = ""
        self._ffprobe_path = ""
        self._last_info: dict[str, Any] = {}

    def _resolve_binaries(self) -> tuple[str, str]:
        ffmpeg = "ffmpeg"
        ffprobe = "ffprobe"
        if self.backend:
            if hasattr(self.backend, "ffmpegPath") and self.backend.ffmpegPath:
                ffmpeg = self.backend.ffmpegPath
            elif hasattr(self.backend, "ffmpeg_service") and self.backend.ffmpeg_service.ffmpeg_path:
                ffmpeg = self.backend.ffmpeg_service.ffmpeg_path

            if hasattr(self.backend, "ffmpeg_service") and getattr(self.backend.ffmpeg_service, "ffprobe_path", None):
                ffprobe = self.backend.ffmpeg_service.ffprobe_path
        return ffmpeg, ffprobe

    @QtCore.Slot(str, result="QVariantMap")
    def inspect(self, file_path: str) -> dict[str, Any]:
        """Inspect media file and return video details."""
        src = Path(file_path).resolve()
        result: dict[str, Any] = {
            "path": str(src),
            "file_name": src.name,
            "duration": 0.0,
            "width": 0,
            "height": 0,
            "fps": 30.0,
            "has_audio": False,
            "size_mb": round(src.stat().st_size / (1024 * 1024), 2) if src.exists() else 0.0,
            "valid": False,
        }
        if not src.exists() or not src.is_file():
            self._last_info = result
            self.fileInspected.emit(result)
            return result

        _, ffprobe = self._resolve_binaries()
        cmd = [
            ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(src),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                fmt = data.get("format", {})
                duration_str = fmt.get("duration")
                if duration_str:
                    result["duration"] = round(float(duration_str), 2)

                for stream in data.get("streams", []):
                    c_type = stream.get("codec_type")
                    if c_type == "video" and result["width"] == 0:
                        result["width"] = int(stream.get("width") or 0)
                        result["height"] = int(stream.get("height") or 0)
                        fps_str = stream.get("r_frame_rate", "") or stream.get("avg_frame_rate", "")
                        if "/" in fps_str:
                            num, den = fps_str.split("/", 1)
                            if float(den or 1.0) > 0:
                                result["fps"] = round(float(num) / float(den or 1.0), 2)
                        elif fps_str:
                            with contextlib.suppress(ValueError):
                                result["fps"] = round(float(fps_str), 2)
                    elif c_type == "audio":
                        result["has_audio"] = True

                result["valid"] = result["width"] > 0 and result["height"] > 0
        except Exception as exc:
            logger.warning("Error inspecting video for Telegram note: %s", exc)

        self._last_info = result
        self.fileInspected.emit(result)
        return result

    @QtCore.Slot(result=str)
    def chooseVideoFile(self) -> str:
        """Open system file picker for input video."""
        filt = "Video Files (" + " ".join(f"*{e}" for e in sorted(VIDEO_EXTS)) + ");;All Files (*)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати відео для Telegram Кружечка", "", filt)
        if path:
            self.inspect(path)
            return path
        return ""

    @QtCore.Slot(str)
    def openInFolder(self, path: str) -> None:
        """Reveal rendered file in system file manager."""
        p = Path(path).resolve()
        if not p.exists():
            return
        if os.name == "nt":
            subprocess.run(["explorer", "/select,", str(p)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)], check=False)
        else:
            subprocess.run(["xdg-open", str(p.parent)], check=False)

    def build_render_command(
        self,
        source_path: Path | str,
        output_path: Path | str,
        options: dict[str, Any],
    ) -> list[str]:
        """Construct exact FFmpeg command for Telegram video note rendering."""
        src = Path(source_path).resolve()
        out = Path(output_path).resolve()
        ffmpeg, _ = self._resolve_binaries()

        start_time = max(0.0, float(options.get("start_time", 0.0) or 0.0))
        end_time = float(options.get("end_time", 0.0) or 0.0)
        if end_time <= start_time:
            end_time = start_time + TELEGRAM_MAX_DURATION
        duration = min(TELEGRAM_MAX_DURATION, max(0.5, end_time - start_time))

        resolution = int(options.get("resolution", TELEGRAM_DEFAULT_RES) or TELEGRAM_DEFAULT_RES)
        resolution = max(240, min(1080, (resolution // 2) * 2))

        crop_mode = str(options.get("crop_mode", "center")).strip().lower()
        bitrate = str(options.get("bitrate", TELEGRAM_DEFAULT_BITRATE) or TELEGRAM_DEFAULT_BITRATE)
        burn_circle = bool(options.get("burn_circle", False))
        audio_enabled = bool(options.get("audio_enabled", True))
        volume_boost = max(0.1, min(3.0, float(options.get("volume_boost", 1.0) or 1.0)))

        # Build video filter chain
        if crop_mode == "blur_pad":
            # Scale video to fit inside resolution x resolution, pad background with blurred version
            v_filter = (
                f"split[v_bg][v_fg];"
                f"[v_bg]scale={resolution}:{resolution},boxblur=25:5[bg_blur];"
                f"[v_fg]scale={resolution}:{resolution}:force_original_aspect_ratio=decrease[fg_scaled];"
                f"[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2"
            )
        else:
            # 1:1 center crop by default
            v_filter = f"crop='min(iw,ih)':'min(iw,ih)':'(iw-min(iw,ih))/2':'(ih-min(iw,ih))/2',scale={resolution}:{resolution}:flags=lanczos"

        # Framerate & pixel format
        v_filter += ",fps=30,format=yuv420p"

        # Optional circular border vignette/matte
        if burn_circle:
            # Draw black rounded corners outside the circle of radius resolution/2
            radius = resolution / 2.0
            v_filter += f",geq=lum='if(lte(hypot(X-{radius},Y-{radius}),{radius}),lum(X,Y),0)':cb='if(lte(hypot(X-{radius},Y-{radius}),{radius}),cb(X,Y),128)':cr='if(lte(hypot(X-{radius},Y-{radius}),{radius}),cr(X,Y),128)'"

        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            f"{start_time:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(src),
            "-vf",
            v_filter,
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-preset",
            "fast",
            "-b:v",
            bitrate,
            "-maxrate",
            str(int(int(bitrate.rstrip("kK")) * 1.5)) + "k" if bitrate.rstrip("kK").isdigit() else "2000k",
            "-bufsize",
            "3000k",
        ]

        # Audio stream
        if audio_enabled:
            a_filter = f"volume={volume_boost:.2f},aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
            cmd.extend(["-af", a_filter, "-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.extend(["-an"])

        # Telegram faststart flag
        cmd.extend(["-movflags", "+faststart", str(out)])
        return cmd

    @QtCore.Slot(str, str, "QVariantMap", result=bool)
    def render(self, source_path: str, output_path: str, options: dict[str, Any]) -> bool:
        """Start asynchronous rendering job for Telegram Video Note."""
        src = Path(source_path).resolve()
        if not src.exists():
            self._error = "Вихідний відеофайл не знайдено."
            self.renderFinished.emit("", False, self._error)
            return False

        if not output_path:
            out_dir = Path(self.backend.outputDir if self.backend and hasattr(self.backend, "outputDir") and self.backend.outputDir else src.parent)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_file = out_dir / f"{src.stem}_telegram_note.mp4"
        else:
            output_file = Path(output_path).resolve()
            output_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = self.build_render_command(src, output_file, options)

        def work(ctx: JobContext) -> dict[str, Any]:
            ctx.progress("rendering", 5)
            logger.info("Rendering Telegram Note: %s", " ".join(cmd))
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            try:
                _, stderr = proc.communicate(timeout=180)
            except subprocess.TimeoutExpired as exc:
                proc.kill()
                raise TimeoutError("Перевищено ліміт часу створення відеоповідомлення (180 с).") from exc

            ctx.check()
            if proc.returncode != 0 or not output_file.exists() or output_file.stat().st_size < 1024:
                err_msg = (stderr or "")[-600:]
                raise RuntimeError(f"Помилка рендерингу FFmpeg: {err_msg}")

            ctx.progress("completed", 100)
            size_mb = round(output_file.stat().st_size / (1024 * 1024), 2)
            res = {
                "ok": True,
                "output_path": str(output_file),
                "size_mb": size_mb,
            }
            return res

        started = self.start_job(work)
        return started

    @QtCore.Slot(str, "QVariantMap", result=bool)
    def addToQueue(self, source_path: str, options: dict[str, Any]) -> bool:
        """Add configured Telegram Video Note as a TaskItem to the main conversion queue."""
        if not self.backend or not hasattr(self.backend, "queue_model"):
            return False

        src = Path(source_path).resolve()
        if not src.exists():
            return False

        resolution = int(options.get("resolution", TELEGRAM_DEFAULT_RES) or TELEGRAM_DEFAULT_RES)
        start_time = max(0.0, float(options.get("start_time", 0.0) or 0.0))
        end_time = float(options.get("end_time", 0.0) or 0.0)
        dur = min(TELEGRAM_MAX_DURATION, max(0.5, end_time - start_time)) if end_time > start_time else TELEGRAM_MAX_DURATION

        overrides = {
            "out_video_format": "mp4",
            "video_codec": "H.264 (AVC)",
            "audio_codec": "aac",
            "resolution": f"{resolution}x{resolution}",
            "resize_w": resolution,
            "resize_h": resolution,
            "trim_start": start_time,
            "trim_end": start_time + dur,
            "aspect_ratio": "1:1",
            "crop_mode": "center",
            "fast_start": True,
        }
        item = TaskItem(
            path=src,
            media_type="video",
            status=TaskStatus.QUEUED,
            overrides=overrides,
        )
        self.backend.queue_model.add_items([item])
        if hasattr(self.backend, "queueStatsChanged"):
            self.backend.queueStatsChanged.emit()
        return True
