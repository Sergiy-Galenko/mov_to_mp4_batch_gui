import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.constants import AUDIO_EXTS, IMAGE_EXTS, SUBTITLE_EXTS, TEXT_EXTS, VIDEO_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTS


def is_subtitle(path: Path) -> bool:
    return path.suffix.lower() in SUBTITLE_EXTS


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTS


_MEDIA_TYPES = {
    extension: kind
    for kind, extensions in (
        ("text", TEXT_EXTS),
        ("subtitle", SUBTITLE_EXTS),
        ("audio", AUDIO_EXTS),
        ("image", IMAGE_EXTS),
        ("video", VIDEO_EXTS),
    )
    for extension in extensions
}


def media_type(path: Path) -> str | None:
    return _MEDIA_TYPES.get(path.suffix.lower())


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


def resolve_output_collision(path: Path, policy: str, reserved: set[Path], *, strict: bool = True) -> Path:
    """Choose a destination using the same rules in previews and workers."""
    if policy in {"stop", "overwrite", "skip"}:
        conflict = path in reserved or (policy == "stop" and path.exists())
        if conflict and strict and policy != "skip":
            raise FileExistsError(f"Конфлікт вихідного файлу: {path.name}")
        if not conflict or policy != "skip":
            reserved.add(path)
            return path
    candidate = path
    index = 1
    while candidate.exists() or candidate in reserved:
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        index += 1
    reserved.add(candidate)
    return candidate


def publish_output(temporary: Path, destination: Path, *, overwrite: bool = False) -> None:
    """Publish a completed file; never replace a concurrent output without consent."""
    if overwrite:
        os.replace(temporary, destination)
    else:
        os.link(temporary, destination)
        temporary.unlink()


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


def render_output_stem(
    template: str,
    in_path: Path,
    *,
    index: int,
    operation: str,
    media_type_name: str,
    info: Any = None,
) -> str:
    now = datetime.now()
    raw_template = template.strip() or "{stem}"
    w = getattr(info, "width", None) if info else None
    h = getattr(info, "height", None) if info else None
    vcodec = getattr(info, "vcodec", None) if info else None
    acodec = getattr(info, "acodec", None) if info else None
    fps = getattr(info, "fps", None) if info else None
    dur = getattr(info, "duration", None) if info else None

    res_str = ""
    if w and h:
        res_str = f"{h}p" if h in {720, 1080, 1440, 2160} else f"{w}x{h}"

    values = _TemplateDict(
        stem=in_path.stem,
        name=in_path.stem,
        ext=in_path.suffix.lstrip("."),
        dir=in_path.parent.name,
        parent=in_path.parent.name,
        index=f"{index:03d}",
        idx=str(index),
        op=operation,
        media=media_type_name,
        date=now.strftime("%Y-%m-%d"),
        year=now.strftime("%Y"),
        time=now.strftime("%H-%M-%S"),
        res=res_str,
        width=str(w) if w else "",
        height=str(h) if h else "",
        codec=str(vcodec or acodec or ""),
        vcodec=str(vcodec or ""),
        acodec=str(acodec or ""),
        fps=f"{round(fps)}fps" if fps else "",
        dur=f"{int(dur)}s" if dur else "",
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
    info: Any = None,
    collision_policy: str = "",
    reserved: set[Path] | None = None,
    strict_collisions: bool = True,
) -> Path:
    stem = render_output_stem(
        template,
        in_path,
        index=index,
        operation=operation,
        media_type_name=media_type_name,
        info=info,
    )
    desired = out_dir / f"{stem}.{out_ext.lstrip('.')}"
    if collision_policy:
        if collision_policy == "parent":
            desired = desired.with_name(f"{sanitize_file_stem(in_path.parent.name)}_{desired.name}")
        return resolve_output_collision(desired, collision_policy, reserved if reserved is not None else set(), strict=strict_collisions)
    if overwrite or skip_existing:
        return desired
    return safe_output_path(desired)


def build_merge_output_path(
    out_dir: Path,
    merge_name: str,
    out_video_format: str,
    *,
    overwrite: bool,
    skip_existing: bool,
) -> Path:
    name = str(merge_name or "").strip() or "merged"
    out_path = Path(name)
    if not out_path.suffix:
        out_path = out_dir / f"{name}.{out_video_format.lstrip('.')}"
    else:
        out_path = out_dir / out_path.name
    if overwrite or skip_existing:
        return out_path
    return safe_output_path(out_path)
