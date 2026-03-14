import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.constants import IMAGE_EXTS, SUBTITLE_EXTS, VIDEO_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def is_subtitle(path: Path) -> bool:
    return path.suffix.lower() in SUBTITLE_EXTS


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
    return safe_output_path(out_path)


def safe_output_path(out_path: Path) -> Path:
    if not out_path.exists():
        return out_path
    base = out_path.stem
    out_ext = out_path.suffix
    out_dir = out_path.parent
    i = 1
    while True:
        candidate = out_dir / f"{base} ({i}){out_ext}"
        if not candidate.exists():
            return candidate
        i += 1


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class _TemplateDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def sanitize_file_stem(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip().strip(".")
    return cleaned or "output"


def render_output_stem(template: str, in_path: Path, *, index: int, operation: str, media_type_name: str) -> str:
    now = datetime.now()
    raw_template = template.strip() or "{stem}"
    values = _TemplateDict(
        stem=in_path.stem,
        ext=in_path.suffix.lstrip("."),
        dir=in_path.parent.name,
        parent=in_path.parent.name,
        index=f"{index:03d}",
        op=operation,
        media=media_type_name,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H-%M-%S"),
    )
    try:
        rendered = raw_template.format_map(values)
    except Exception:
        rendered = in_path.stem
    return sanitize_file_stem(rendered)


def build_output_path(
    out_dir: Path,
    in_path: Path,
    out_ext: str,
    *,
    template: str,
    index: int,
    operation: str,
    media_type_name: str,
    overwrite: bool,
    skip_existing: bool,
) -> Path:
    stem = render_output_stem(template, in_path, index=index, operation=operation, media_type_name=media_type_name)
    desired = out_dir / f"{stem}.{out_ext.lstrip('.')}"
    if overwrite or skip_existing:
        return desired
    return safe_output_path(desired)
