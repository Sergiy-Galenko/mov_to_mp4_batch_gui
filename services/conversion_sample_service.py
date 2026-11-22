"""Isolated, bounded conversion samples using the normal FFmpeg builders."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import replace
from pathlib import Path

from app.models import ConversionSettings
from services.cache_manager import CacheManager
from services.ffmpeg_service import FfmpegService
from services.smart_convert_service import apply_smart_settings
from utils.error_classifier import error_summary


def create_sample(
    ffmpeg: FfmpegService, source: Path, media_type: str, settings: ConversionSettings, cache_dir: Path, seconds: int = 15
) -> Path:
    if media_type not in {"video", "audio"} or settings.operation not in {"convert", "audio_only", "subtitle_burn"}:
        raise ValueError("Пробна конвертація доступна для відео та аудіо.")
    if not ffmpeg.ffmpeg_path:
        raise ValueError("Спочатку налаштуйте FFmpeg.")
    if not source.is_file():
        raise ValueError("Файл джерела не знайдено.")
    if settings.merge or settings.target_size_mb:
        raise ValueError("Для пробного фрагмента вимкніть об’єднання та цільовий розмір: вони розраховані на повний файл.")
    info = ffmpeg.probe_media(source)
    settings = apply_smart_settings(settings, info, media_type=media_type, source_path=source)
    start = settings.trim_start or 0.0
    end = start + max(10, min(20, int(seconds)))
    if settings.trim_end is not None:
        end = min(end, settings.trim_end)
    if info and info.duration:
        end = min(end, info.duration)
    if end <= start:
        raise ValueError("Початок фрагмента має бути раніше його кінця.")
    sample_settings = replace(settings, trim_start=start, trim_end=end, overwrite=True)
    cache = CacheManager(cache_dir)
    suffix = "." + ffmpeg.output_extension_for(media_type, sample_settings).lstrip(".")

    def encode(output: Path) -> bool:
        if media_type == "audio" or settings.operation == "audio_only":
            command = ffmpeg.build_audio_command(source, output, sample_settings, duration=end - start)
        else:
            command = ffmpeg.build_video_command(source, output, sample_settings, info, allow_fast_copy=settings.fast_copy)
        # Bound output even when a codec/container uses keyframe-aligned stream copying.
        command[-1:-1] = ["-t", str(end - start)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if result.returncode or not output.is_file() or not output.stat().st_size:
            raise RuntimeError(error_summary(result.stderr) or "Не вдалося створити пробний фрагмент.")
        return True

    # A fresh sample reflects changes to sidecar subtitles, replacement audio and artwork.
    output = cache.produce(source, "samples", {"request": uuid.uuid4().hex}, suffix, encode)
    if output is None:
        raise RuntimeError("Не вдалося зберегти фрагмент: джерело змінилося або перевищено ліміт кешу.")
    return output
