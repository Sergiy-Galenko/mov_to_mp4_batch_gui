from pathlib import Path
from typing import Optional

from config.constants import VIDEO_EXTS, IMAGE_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def media_type(path: Path) -> Optional[str]:
    if is_video(path):
        return "video"
    if is_image(path):
        return "image"
    return None


def safe_output_name(out_dir: Path, in_path: Path, out_ext: str) -> Path:
    out_ext = out_ext.lstrip(".")
    base = in_path.stem
    out_path = out_dir / f"{base}.{out_ext}"
    if not out_path.exists():
        return out_path
    i = 1
    while True:
        candidate = out_dir / f"{base} ({i}).{out_ext}"
        if not candidate.exists():
            return candidate
        i += 1
