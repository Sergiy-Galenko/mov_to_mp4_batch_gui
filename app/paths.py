import os
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path


def get_app_data_dir() -> Path:
    """Return the OS-appropriate writable app data directory."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "MediaConverter"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "MediaConverter"
    else:
        base = Path.home() / ".local" / "share" / "MediaConverter"
    base.mkdir(parents=True, exist_ok=True)
    return base


APP_DATA_DIR = get_app_data_dir()
STATE_PATH = APP_DATA_DIR / "state.json"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
LOG_PATH = APP_DATA_DIR / "history.log"
PRESET_PATH = APP_DATA_DIR / "presets.json"
THEME_PATH = APP_DATA_DIR / "theme.json"
HISTORY_PATH = APP_DATA_DIR / "history.json"
DEFAULT_OUTPUT_DIR = Path.home() / "Videos" / "converted"


def _runtime_roots() -> Iterable[Path]:
    project_root = Path(__file__).resolve().parents[1]
    yield project_root
    yield project_root / "bin"
    yield APP_DATA_DIR / "ffmpeg" / "current" / "bin"

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


def _find_binary(filename: str, explicit_path: str = "") -> str | None:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists() and path.is_file():
            return str(path)
    for root in _runtime_roots():
        candidate = root / filename
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    if os.environ.get("MEDIA_CONVERTER_ALLOW_PATH_BINARIES", "").strip().lower() in {"1", "true", "yes"}:
        resolved = shutil.which(filename)
        return str(Path(resolved).resolve()) if resolved else None
    return None


def find_ffmpeg() -> str | None:
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    explicit = os.environ.get("MEDIA_CONVERTER_FFMPEG", "").strip()
    return _find_binary(exe, explicit)


def find_ffprobe(ffmpeg_path: str | None) -> str | None:
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
