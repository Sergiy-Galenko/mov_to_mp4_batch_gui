"""Media preview service — generates thumbnail strips and audio waveforms.

Uses FFmpeg/FFprobe to create visual previews of media files:
  - Video: generates a strip of N equally-spaced thumbnails
  - Audio: generates a waveform PNG image
  - Image: uses the image itself as preview
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from app.paths import APP_DATA_DIR

PREVIEW_CACHE_DIR = APP_DATA_DIR / "previews"


class MediaPreviewService:
    """Generates visual previews for media files."""

    def __init__(self, ffmpeg_path: str = "", ffprobe_path: str = "") -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def thumbnail_strip(
        self,
        video_path: Path,
        *,
        count: int = 8,
        thumb_width: int = 160,
        thumb_height: int = 90,
    ) -> List[str]:
        """Generate a strip of equally-spaced thumbnails from a video.

        Returns a list of file paths to generated thumbnail images.
        """
        if not self.ffmpeg_path or not video_path.exists():
            return []

        cache_key = _cache_key(video_path)
        cache_dir = PREVIEW_CACHE_DIR / cache_key
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Check if cached thumbnails exist
        existing = sorted(cache_dir.glob("thumb_*.jpg"))
        if len(existing) >= count:
            return [str(path) for path in existing[:count]]

        duration = self._get_duration(video_path)
        if duration <= 0:
            return []

        results: List[str] = []
        for i in range(count):
            timestamp = (duration / (count + 1)) * (i + 1)
            output_path = cache_dir / f"thumb_{i:03d}.jpg"
            if output_path.exists():
                results.append(str(output_path))
                continue

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-ss", f"{timestamp:.2f}",
                "-i", str(video_path),
                "-vframes", "1",
                "-vf", f"scale={thumb_width}:{thumb_height}:force_original_aspect_ratio=decrease,pad={thumb_width}:{thumb_height}:(ow-iw)/2:(oh-ih)/2:color=black",
                "-q:v", "5",
                str(output_path),
            ]
            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if output_path.exists():
                    results.append(str(output_path))
            except Exception:
                continue

        return results

    def audio_waveform(
        self,
        audio_path: Path,
        *,
        width: int = 800,
        height: int = 120,
        color: str = "0x3D8EFF",
        bg_color: str = "0x151820",
    ) -> Optional[str]:
        """Generate a waveform PNG for an audio file.

        Returns path to the generated waveform image, or None on failure.
        """
        if not self.ffmpeg_path or not audio_path.exists():
            return None

        cache_key = _cache_key(audio_path)
        output_path = PREVIEW_CACHE_DIR / f"waveform_{cache_key}.png"

        if output_path.exists():
            return str(output_path)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(audio_path),
            "-filter_complex",
            f"showwavespic=s={width}x{height}:colors={color}:split_channels=0",
            "-frames:v", "1",
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if output_path.exists():
                return str(output_path)
        except Exception:
            pass
        return None

    def video_snapshot(
        self,
        video_path: Path,
        timestamp: float,
        *,
        width: int = 640,
        height: int = 360,
    ) -> Optional[str]:
        """Capture a single frame at the given timestamp.

        Returns path to the captured frame image, or None on failure.
        """
        if not self.ffmpeg_path or not video_path.exists():
            return None

        cache_key = _cache_key(video_path)
        output_path = PREVIEW_CACHE_DIR / f"snap_{cache_key}_{int(timestamp * 1000)}.jpg"

        if output_path.exists():
            return str(output_path)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", f"{timestamp:.3f}",
            "-i", str(video_path),
            "-vframes", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            "-q:v", "3",
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if output_path.exists():
                return str(output_path)
        except Exception:
            pass
        return None

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
            thumbnails = self.thumbnail_strip(file_path)
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
        """Get media duration in seconds using ffprobe."""
        if not self.ffprobe_path:
            return 0.0
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass
        return 0.0

    def clear_cache(self) -> int:
        """Remove all cached preview files. Returns count of removed files."""
        removed = 0
        if PREVIEW_CACHE_DIR.exists():
            for item in PREVIEW_CACHE_DIR.rglob("*"):
                if item.is_file():
                    try:
                        item.unlink()
                        removed += 1
                    except OSError:
                        pass
        return removed


def _cache_key(path: Path) -> str:
    """Generate a stable cache key for a file path."""
    try:
        stat = path.stat()
        raw = f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
    except OSError:
        raw = str(path.resolve())
    return hashlib.md5(raw.encode()).hexdigest()[:16]
