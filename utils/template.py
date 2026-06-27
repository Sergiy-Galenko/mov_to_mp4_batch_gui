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

Unknown placeholders are left as-is to prevent data loss.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Pre-compiled pattern for template placeholders
_PLACEHOLDER_RE = re.compile(r"\{(\w+)(?::(\d+))?\}")


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
    }

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        pad = match.group(2)

        if key == "counter":
            pad_width = int(pad) if pad else 3
            return str(counter).zfill(pad_width)

        if key == "index" and pad:
            return str(index).zfill(int(pad))

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
        "counter", "parent",
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
