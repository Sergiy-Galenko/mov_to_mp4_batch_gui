import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional


def _runtime_roots() -> Iterable[Path]:
    project_root = Path(__file__).resolve().parents[1]
    yield project_root
    yield project_root / "bin"

    env_dir = os.environ.get("MEDIA_CONVERTER_FFMPEG_DIR", "").strip()
    if env_dir:
        yield Path(env_dir).expanduser()

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        yield exe_dir
        yield exe_dir / "ffmpeg"
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            yield Path(meipass)


def _find_binary(filename: str, explicit_path: str = "") -> Optional[str]:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists() and path.is_file():
            return str(path)
    for root in _runtime_roots():
        candidate = root / filename
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return shutil.which(filename)


def find_ffmpeg() -> Optional[str]:
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    explicit = os.environ.get("MEDIA_CONVERTER_FFMPEG", "").strip()
    return _find_binary(exe, explicit)


def find_ffprobe(ffmpeg_path: Optional[str]) -> Optional[str]:
    exe = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    candidates = []
    if ffmpeg_path:
        ffmpeg_dir = Path(ffmpeg_path).expanduser().resolve().parent
        candidates.append(ffmpeg_dir / exe)
    explicit = os.environ.get("MEDIA_CONVERTER_FFPROBE", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists() and path.is_file():
            return str(path)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return _find_binary(exe)
