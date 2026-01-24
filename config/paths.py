import os
import shutil
from pathlib import Path
from typing import Optional


def find_ffmpeg() -> Optional[str]:
    local = Path(__file__).resolve().parents[1]
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidates = [
        local / exe,
        local / "bin" / exe,
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return str(path)
    return shutil.which("ffmpeg")


def find_ffprobe(ffmpeg_path: Optional[str]) -> Optional[str]:
    local = Path(__file__).resolve().parents[1]
    exe = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    candidates = []
    if ffmpeg_path:
        ffmpeg_dir = Path(ffmpeg_path).resolve().parent
        candidates.append(ffmpeg_dir / exe)
    candidates.extend([
        local / exe,
        local / "bin" / exe,
    ])
    for path in candidates:
        if path.exists() and path.is_file():
            return str(path)
    return shutil.which("ffprobe")
