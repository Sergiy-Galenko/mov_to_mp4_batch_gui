"""Media preview service — generates thumbnail strips and audio waveforms.

Uses FFmpeg/FFprobe to create visual previews of media files:
  - Video: generates a strip of N equally-spaced thumbnails
  - Audio: generates a waveform PNG image
  - Image: uses the image itself as preview
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from app.paths import APP_DATA_DIR
from services.cache_manager import CacheManager, source_fingerprint, tool_fingerprint

PREVIEW_CACHE_DIR = APP_DATA_DIR / "cache"


class MediaPreviewService:
    """Generates visual previews for media files."""

    def __init__(self, ffmpeg_path: str = "", ffprobe_path: str = "", *, cache: CacheManager | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.cache = cache or CacheManager(PREVIEW_CACHE_DIR)

    def thumbnail_strip(
        self,
        video_path: Path,
        *,
        count: int = 8,
        thumb_width: int = 160,
        thumb_height: int = 90,
        duration: float | None = None,
    ) -> list[str]:
        """Generate a strip of equally-spaced thumbnails from a video.

        Returns a list of file paths to generated thumbnail images.
        """
        if not self.ffmpeg_path or not video_path.exists():
            return []

        if duration is None:
            duration = self._get_duration(video_path)
        if duration <= 0:
            return []

        results: list[str] = []
        if count < 1 or thumb_width < 1 or thumb_height < 1:
            return results
        for i in range(count):
            timestamp = (duration / (count + 1)) * (i + 1)
            params = {"count": count, "width": thumb_width, "height": thumb_height, "duration": duration,
                      "index": i, "ffmpeg": tool_fingerprint(self.ffmpeg_path)}
            filter_string = (f"scale={thumb_width}:{thumb_height}:force_original_aspect_ratio=decrease,"
                             f"pad={thumb_width}:{thumb_height}:(ow-iw)/2:(oh-ih)/2:color=black")
            path = self._artifact(video_path, "strips", params, ".jpg",
                                  ["-ss", f"{timestamp:.6f}", "-i", str(video_path), "-vframes", "1",
                                   "-vf", filter_string, "-q:v", "5"], timeout=10)
            if path:
                results.append(path)
        return results

    def _artifact(self, source, namespace, params, suffix, arguments, *, timeout):
        def producer(target):
            result = subprocess.run([self.ffmpeg_path, "-y", *arguments, str(target)], capture_output=True,
                                    timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return result.returncode == 0
        try:
            target = self.cache.produce(source, namespace, params, suffix, producer)
            return str(target) if target else None
        except (OSError, TimeoutError, subprocess.SubprocessError):
            return None

    def audio_waveform(
        self,
        audio_path: Path,
        *,
        width: int = 800,
        height: int = 120,
        color: str = "0x3D8EFF",
        bg_color: str = "0x151820",
    ) -> str | None:
        """Generate a waveform PNG for an audio file.

        Returns path to the generated waveform image, or None on failure.
        """
        if not self.ffmpeg_path or not audio_path.exists():
            return None

        if width < 1 or height < 1:
            return None
        params = {"width": width, "height": height, "color": color, "background": bg_color,
                  "ffmpeg": tool_fingerprint(self.ffmpeg_path)}
        # showwavespic produces transparency; explicitly compose the requested background.
        filters = (f"color=c={bg_color}:s={width}x{height}[bg];"
                   f"[0:a]showwavespic=s={width}x{height}:colors={color}:split_channels=0[wave];"
                   "[bg][wave]overlay=shortest=1[out]")
        return self._artifact(audio_path, "waveforms", params, ".png",
                              ["-i", str(audio_path), "-filter_complex", filters, "-map", "[out]", "-frames:v", "1"], timeout=30)

    def video_snapshot(
        self,
        video_path: Path,
        timestamp: float,
        *,
        width: int = 640,
        height: int = 360,
    ) -> str | None:
        """Capture a single frame at the given timestamp.

        Returns path to the captured frame image, or None on failure.
        """
        if not self.ffmpeg_path or not video_path.exists():
            return None

        if timestamp < 0 or width < 1 or height < 1:
            return None
        params = {"timestamp": timestamp, "width": width, "height": height, "ffmpeg": tool_fingerprint(self.ffmpeg_path)}
        return self._artifact(video_path, "snapshots", params, ".jpg",
                              ["-ss", f"{timestamp:.6f}", "-i", str(video_path), "-vframes", "1",
                               "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease", "-q:v", "3"], timeout=10)

    def generate_preview(
        self,
        file_path: Path,
        media_kind: str,
    ) -> dict:
        """Generate appropriate preview for the media type.

        Returns dict with:
          - 'type': 'thumbnails' | 'waveform' | 'image'
          - 'paths': list of paths (thumbnails) or single path
          - 'duration': float duration in seconds (if available)
        """
        result: dict = {"type": "none", "paths": [], "duration": 0.0}

        if media_kind == "video":
            duration = self._get_duration(file_path)
            thumbnails = self.thumbnail_strip(file_path, duration=duration)
            result = {
                "type": "thumbnails",
                "paths": thumbnails,
                "duration": duration,
            }
        elif media_kind == "audio":
            waveform = self.audio_waveform(file_path)
            duration = self._get_duration(file_path)
            result = {
                "type": "waveform",
                "paths": [waveform] if waveform else [],
                "duration": duration,
            }
        elif media_kind == "image":
            if file_path.exists():
                result = {
                    "type": "image",
                    "paths": [str(file_path)],
                    "duration": 0.0,
                }

        return result

    def _get_duration(self, path: Path) -> float:
        from services.ffmpeg_service import FfmpegService
        service = FfmpegService(self.ffmpeg_path, self.ffprobe_path)
        service.cache = self.cache
        info = service.probe_media(path)
        return info.duration or 0.0 if info else 0.0

    def clear_cache(self) -> int:
        """Remove all cached preview files. Returns count of removed files."""
        return sum(self.cache.cleanup(namespace=namespace, clear=True)
                   for namespace in ("strips", "snapshots", "waveforms", "thumbnails"))


def _cache_key(path: Path) -> str:
    return hashlib.sha256(json.dumps(source_fingerprint(path), sort_keys=True).encode()).hexdigest()[:16]
