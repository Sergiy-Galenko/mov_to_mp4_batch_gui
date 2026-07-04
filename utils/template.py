"""Advanced output filename template engine.

Supports placeholders like:
  {name}        — original filename stem
  {ext}         — original extension without dot
  {index}       — queue position (zero-padded)
  {date}        — YYYY-MM-DD
  {time}        — HH-MM-SS
  {datetime}    — YYYY-MM-DD_HH-MM-SS
  {operation}   — current operation name
  {type}        — media type (video/audio/image/subtitle)
  {resolution}  — WIDTHxHEIGHT (requires probe data)
  {codec}       — source video codec (requires probe data)
  {fps}         — source fps (requires probe data)
  {counter:N}   — auto-incrementing counter padded to N digits
  {parent}      — parent folder name of source
  {size}        — human-readable file size (e.g. '1.5 GB')
  {size_mb}     — file size in megabytes (e.g. '1536')
  {bitrate}     — source bitrate (e.g. '8500k')
  {duration}    — duration as HH-MM-SS
  {channels}    — audio channel count (requires probe data)
  {sample_rate} — audio sample rate in Hz (requires probe data)
  {hash:N}      — first N chars of content hash (default 8)

Unknown placeholders are left as-is to prevent data loss.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Pre-compiled pattern for template placeholders
_PLACEHOLDER_RE = re.compile(r"\{(\w+)(?::(\d+))?\}")


def _human_size(size_bytes: int) -> str:
    """Convert bytes to a filesystem-safe human-readable string (e.g. '1.5GB')."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    for unit in ("KB", "MB", "GB", "TB"):
        size_bytes /= 1024
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
    return f"{size_bytes:.1f}PB"


def _format_duration(seconds: float) -> str:
    """Format seconds into HH-MM-SS (filesystem-safe)."""
    if seconds <= 0:
        return "00-00-00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}-{m:02d}-{s:02d}"


def render_template(
    template: str,
    *,
    source_path: Optional[Path] = None,
    index: int = 1,
    operation: str = "",
    media_type_name: str = "",
    probe_data: Optional[Dict[str, Any]] = None,
    counter: int = 1,
) -> str:
    """Render an output filename template with the given context.

    Returns the rendered stem (without extension).
    If ``template`` is empty, falls back to the source filename stem.
    """
    if not template:
        return source_path.stem if source_path else "output"

    now = datetime.now()
    info = probe_data or {}
    source = source_path or Path("output")

    width = info.get("width")
    height = info.get("height")
    resolution = f"{width}x{height}" if width and height else ""

    # File size placeholders
    size_bytes = info.get("size_bytes") or 0
    if not size_bytes and source_path:
        try:
            size_bytes = source_path.stat().st_size
        except OSError:
            size_bytes = 0
    size_text = _human_size(size_bytes) if size_bytes else ""
    size_mb = str(int(size_bytes / (1024 * 1024))) if size_bytes else ""

    # Bitrate placeholder
    bitrate_raw = info.get("bitrate") or info.get("bit_rate") or 0
    bitrate_text = f"{int(bitrate_raw) // 1000}k" if bitrate_raw else ""

    # Duration placeholder
    duration_raw = info.get("duration") or 0
    duration_text = _format_duration(float(duration_raw)) if duration_raw else ""

    # Audio metadata
    channels = str(info.get("channels") or info.get("audio_channels") or "") if info.get("channels") or info.get("audio_channels") else ""
    sample_rate = str(info.get("sample_rate") or "") if info.get("sample_rate") else ""

    # Content hash
    content_hash = str(info.get("content_hash") or "")

    values: Dict[str, str] = {
        "name": source.stem,
        "ext": source.suffix.lstrip(".") if source.suffix else "",
        "index": str(index),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H-%M-%S"),
        "datetime": now.strftime("%Y-%m-%d_%H-%M-%S"),
        "operation": operation,
        "type": media_type_name,
        "resolution": resolution,
        "codec": str(info.get("vcodec") or info.get("acodec") or ""),
        "fps": f"{info['fps']:.0f}" if info.get("fps") else "",
        "parent": source.parent.name if source.parent != source else "",
        "size": size_text,
        "size_mb": size_mb,
        "bitrate": bitrate_text,
        "duration": duration_text,
        "channels": channels,
        "sample_rate": sample_rate,
    }

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        pad = match.group(2)

        if key == "counter":
            pad_width = int(pad) if pad else 3
            return str(counter).zfill(pad_width)

        if key == "index" and pad:
            return str(index).zfill(int(pad))

        if key == "hash":
            length = int(pad) if pad else 8
            return content_hash[:length] if content_hash else ""

        value = values.get(key)
        if value is None:
            # Leave unknown placeholders untouched
            return match.group(0)
        return value

    result = _PLACEHOLDER_RE.sub(_replace, template)
    # Sanitize: remove characters unsafe for filenames
    result = re.sub(r'[<>:"/\\|?*]', "_", result)
    return result.strip() or (source.stem if source_path else "output")


def validate_template(template: str) -> Optional[str]:
    """Validate a template string. Returns error message or None if valid."""
    if not template:
        return None

    known_keys = {
        "name", "ext", "index", "date", "time", "datetime",
        "operation", "type", "resolution", "codec", "fps",
        "counter", "parent", "size", "size_mb", "bitrate",
        "duration", "channels", "sample_rate", "hash",
    }

    for match in _PLACEHOLDER_RE.finditer(template):
        key = match.group(1)
        if key not in known_keys:
            return f"Невідомий placeholder: {{{key}}}"

    # Test render to catch formatting errors
    try:
        render_template(template, source_path=Path("test.mp4"))
    except Exception as exc:
        return f"Помилка шаблону: {exc}"

    return None
