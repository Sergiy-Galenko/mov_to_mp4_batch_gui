from __future__ import annotations

import subprocess
from pathlib import Path

from app.models import MediaInfo
from services.cache_manager import CacheManager, tool_fingerprint
from services.ffmpeg_service import FfmpegService


class MediaAnalysisService:
    def __init__(self, ffmpeg: FfmpegService, cache_dir: Path | None = None, *, cache: CacheManager | None = None) -> None:
        self.ffmpeg = ffmpeg
        self.cache = cache or (CacheManager(cache_dir) if cache_dir else CacheManager())
        self.cache_dir = self.cache.root / "thumbnails"

    def probe(self, path: Path) -> MediaInfo | None:
        return self.ffmpeg.probe_media(path)

    def thumbnail_path(self, path: Path) -> Path:
        parameters = {"width": 160, "timestamp": 1, "ffmpeg": tool_fingerprint(self.ffmpeg.ffmpeg_path)}
        return self.cache.path(self.cache.key(path, "thumbnails", parameters), "thumbnails", ".jpg")

    def thumbnail_for(self, path: Path, media_kind: str) -> str | None:
        if media_kind == "image" and path.exists():
            return str(path)
        if media_kind != "video" or not self.ffmpeg.ffmpeg_path or not path.is_file():
            return None

        def produce(target):
            command = [self.ffmpeg.ffmpeg_path, "-y", "-ss", "1", "-i", str(path), "-frames:v", "1",
                       "-vf", "scale=160:-1", str(target)]
            result = subprocess.run(command, capture_output=True, timeout=20,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return result.returncode == 0

        try:
            target = self.cache.produce(path, "thumbnails", {"width": 160, "timestamp": 1,
                                        "ffmpeg": tool_fingerprint(self.ffmpeg.ffmpeg_path)}, ".jpg", produce)
            return str(target) if target else None
        except (OSError, TimeoutError, subprocess.SubprocessError):
            return None
