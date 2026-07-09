from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from app.constants import OUT_AUDIO_FORMATS, OUT_IMAGE_FORMATS, OUT_SUBTITLE_FORMATS, OUT_TEXT_FORMATS, OUT_VIDEO_FORMATS
from app.models import TaskItem


DEFAULT_FOLDER_RULES = "Downloads -> mp4\nCamera -> h265\nAudio -> mp3"


@dataclass
class FolderRule:
    match: str
    overrides: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    pinned: bool = False


class BatchWorkflowService:
    """Small rule engine for watch-folder batch automation."""

    def parse_rules(self, text: str) -> List[FolderRule]:
        rules: List[FolderRule] = []
        for raw_line in str(text or "").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "->" not in line:
                continue
            left, right = line.split("->", 1)
            match = left.strip().strip('"').strip("'")
            if not match:
                continue
            overrides, priority, pinned = self._parse_action(right)
            rules.append(FolderRule(match=match, overrides=overrides, priority=priority, pinned=pinned))
        return rules

    def apply_rules(self, item: TaskItem, rules: Iterable[FolderRule]) -> bool:
        changed = False
        for rule in rules:
            if not self._matches(item.path, rule.match):
                continue
            media_overrides = self._media_overrides(rule.overrides, item.media_type)
            if media_overrides:
                merged = dict(item.overrides)
                merged.update(media_overrides)
                item.overrides = merged
                changed = True
            if rule.priority > item.priority:
                item.priority = rule.priority
                changed = True
            if rule.pinned and not item.pinned:
                item.pinned = True
                changed = True
        return changed

    def preview_rules(self, text: str) -> List[Dict[str, Any]]:
        return [
            {
                "match": rule.match,
                "overrides": dict(rule.overrides),
                "priority": rule.priority,
                "pinned": rule.pinned,
            }
            for rule in self.parse_rules(text)
        ]

    def _matches(self, path: Path, pattern: str) -> bool:
        needle = str(pattern or "").strip().lower()
        if not needle:
            return False
        try:
            path_text = str(path.expanduser()).lower()
            parts = [part.lower() for part in path.parts]
        except Exception:
            path_text = str(path).lower()
            parts = []
        return needle in path_text or needle in parts

    def _parse_action(self, action: str) -> Tuple[Dict[str, Any], int, bool]:
        overrides: Dict[str, Any] = {"operation": "convert"}
        priority = 0
        pinned = False
        tokens = [token for token in re.split(r"[\s,;]+", str(action or "").strip()) if token]

        for token in tokens:
            key, sep, value = token.partition("=")
            normalized = key.strip().lower()
            raw_value = value.strip() if sep else ""
            value_lower = raw_value.lower()
            command = value_lower if sep else normalized

            if normalized in {"priority", "prio"} and sep:
                try:
                    priority = max(0, min(5, int(raw_value)))
                except ValueError:
                    pass
                continue
            if command in {"pin", "pinned"} or (normalized == "pinned" and value_lower in {"1", "true", "yes", "on"}):
                pinned = True
                continue
            if normalized in {"template", "output_template"} and sep:
                overrides["output_template"] = raw_value or "{stem}"
                continue
            if normalized in {"profile", "performance_profile"} and sep:
                overrides["performance_profile"] = raw_value
                continue
            if normalized in {"op", "operation"} and sep:
                overrides["operation"] = self._normalize_operation(raw_value)
                continue
            if normalized in {"codec", "video_codec"} and sep:
                self._apply_codec(command, overrides)
                continue
            if normalized in {"format", "fmt"} and sep:
                self._apply_format(command, overrides)
                continue

            if command in {"audio_only", "audio-only", "extract_audio", "extract-audio"}:
                overrides["operation"] = "audio_only"
                continue
            if command in {"h265", "hevc", "x265"}:
                overrides["codec"] = "H.265 (HEVC)"
                overrides.setdefault("out_video_fmt", "mp4")
                continue
            if command in {"h264", "avc", "x264"}:
                overrides["codec"] = "H.264 (AVC)"
                overrides.setdefault("out_video_fmt", "mp4")
                continue
            self._apply_format(command, overrides)

        return overrides, priority, pinned

    def _normalize_operation(self, value: str) -> str:
        normalized = str(value or "").strip().lower().replace("-", "_")
        if normalized in {"audio", "audio_only", "extract_audio"}:
            return "audio_only"
        if normalized in {"subtitle_extract", "extract_subtitle"}:
            return "subtitle_extract"
        if normalized in {"subtitle_burn", "burn_subtitle"}:
            return "subtitle_burn"
        if normalized in {"thumbnail", "contact_sheet", "auto_subtitle"}:
            return normalized
        return "convert"

    def _apply_codec(self, value: str, overrides: Dict[str, Any]) -> None:
        normalized = str(value or "").strip().lower()
        if normalized in {"h265", "hevc", "x265"}:
            overrides["codec"] = "H.265 (HEVC)"
        elif normalized in {"h264", "avc", "x264"}:
            overrides["codec"] = "H.264 (AVC)"
        elif normalized == "av1":
            overrides["codec"] = "AV1"
        elif normalized == "vp9":
            overrides["codec"] = "VP9 (WebM)"
        elif normalized == "prores":
            overrides["codec"] = "ProRes"
        elif normalized in {"mpeg2", "mpeg-2"}:
            overrides["codec"] = "MPEG-2"

    def _apply_format(self, value: str, overrides: Dict[str, Any]) -> None:
        normalized = str(value or "").strip().lower().lstrip(".")
        if normalized in OUT_VIDEO_FORMATS:
            overrides["out_video_fmt"] = normalized
        elif normalized in OUT_AUDIO_FORMATS:
            overrides["out_audio_fmt"] = normalized
        elif normalized in OUT_IMAGE_FORMATS:
            overrides["out_image_fmt"] = normalized
        elif normalized in OUT_SUBTITLE_FORMATS:
            overrides["out_subtitle_fmt"] = normalized
        elif normalized in OUT_TEXT_FORMATS:
            overrides["out_text_fmt"] = normalized

    def _media_overrides(self, overrides: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        allowed = {"operation", "output_template", "performance_profile", "codec"}
        if media_type == "video":
            allowed.update({"out_video_fmt", "out_audio_fmt"})
        elif media_type == "audio":
            allowed.update({"out_audio_fmt"})
        elif media_type == "image":
            allowed.update({"out_image_fmt"})
        elif media_type == "subtitle":
            allowed.update({"out_subtitle_fmt"})
        elif media_type == "text":
            allowed.update({"out_text_fmt"})
        return {key: value for key, value in overrides.items() if key in allowed}
