from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Optional

from app.models import MediaInfo
from services.ffmpeg_service import FfmpegService


class MediaAnalysisService:
    def __init__(self, ffmpeg: FfmpegService, cache_dir: Optional[Path] = None) -> None:
        self.ffmpeg = ffmpeg
        self.cache_dir = cache_dir or (Path.home() / ".media_converter_gui_thumbnails")

    def probe(self, path: Path) -> Optional[MediaInfo]:
        return self.ffmpeg.probe_media(path)

    def thumbnail_for(self, path: Path, media_kind: str) -> Optional[str]:
        if media_kind == "image" and path.exists():
            return str(path)
        if media_kind != "video" or not self.ffmpeg.ffmpeg_path:
            return None
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha1(str(path).encode("utf-8", errors="ignore")).hexdigest()[:16]
            target = self.cache_dir / f"{digest}.jpg"
            if not target.exists():
                cmd = [
                    self.ffmpeg.ffmpeg_path,
                    "-y",
                    "-ss",
                    "1",
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=160:-1",
                    str(target),
                ]
                subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if target.exists():
                return str(target)
        except Exception:
            return None
        return None
