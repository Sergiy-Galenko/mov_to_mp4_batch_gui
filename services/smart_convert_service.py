from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from app.models import ConversionSettings, MediaInfo


@dataclass
class SmartRecommendation:
    content_type: str
    video_codec: str
    crf: int
    preset: str
    reason: str


def _normalize_codec(codec: str | None) -> str:
    value = str(codec or "").strip().lower()
    if value in {"h264", "avc", "libx264"}:
        return "h264"
    if value in {"hevc", "h265", "libx265"}:
        return "h265"
    if "av1" in value:
        return "av1"
    if "vp9" in value:
        return "vp9"
    return value


def classify_content(info: MediaInfo | None, source_path: Path | None = None, override: str = "auto") -> str:
    requested = str(override or "auto").strip().lower()
    if requested in {"animation", "live_action", "screencast"}:
        return requested

    name = source_path.name.lower() if source_path else ""
    if any(token in name for token in ("anime", "animation", "cartoon", "toon")):
        return "animation"
    if any(token in name for token in ("screen", "capture", "recording", "tutorial", "desktop")):
        return "screencast"

    if info:
        codec = _normalize_codec(info.vcodec)
        if codec in {"gif", "png", "qtrle"}:
            return "animation"
        if info.fps and info.fps <= 18:
            return "animation"
        if (
            info.width
            and info.height
            and info.fps
            and info.fps <= 30
            and info.width >= 1280
            and info.height >= 720
            and (info.frame_rate_mode or "").upper() == "CFR"
        ):
            return "screencast"
    return "live_action"


def recommend_settings(settings: ConversionSettings, info: MediaInfo | None, source_path: Path | None = None) -> SmartRecommendation:
    content_type = classify_content(info, source_path, settings.smart_content_type)
    quality = str(settings.smart_quality_target or "balanced").strip().lower()
    if quality not in {"small", "balanced", "quality"}:
        quality = "balanced"

    width = int(info.width or 0) if info else 0
    height = int(info.height or 0) if info else 0
    pixels = width * height
    hdr = bool(info and info.dynamic_range == "HDR")

    if settings.out_video_format == "webm":
        codec = "VP9 (WebM)"
    elif hdr or pixels >= 3840 * 2160:
        codec = "H.265 (HEVC)"
    else:
        codec = "H.264 (AVC)"

    base_crf = {
        "animation": {"small": 25, "balanced": 21, "quality": 18},
        "screencast": {"small": 28, "balanced": 24, "quality": 20},
        "live_action": {"small": 28, "balanced": 23, "quality": 19},
    }[content_type][quality]
    if pixels >= 3840 * 2160:
        base_crf = max(16, base_crf - 1)
    elif pixels and pixels <= 1280 * 720:
        base_crf = min(30, base_crf + 1)

    preset = {"small": "slow", "balanced": "medium", "quality": "slow"}[quality]
    reason = f"{content_type}, {width or '?'}x{height or '?'}, {quality}"
    return SmartRecommendation(content_type=content_type, video_codec=codec, crf=base_crf, preset=preset, reason=reason)


def apply_smart_settings(
    settings: ConversionSettings,
    info: MediaInfo | None,
    *,
    media_type: str,
    source_path: Path | None = None,
) -> ConversionSettings:
    if not settings.smart_convert_enabled or media_type != "video" or settings.operation not in {"convert", "subtitle_burn"}:
        return settings
    recommendation = recommend_settings(settings, info, source_path)
    return replace(
        settings,
        video_codec=recommendation.video_codec,
        crf=recommendation.crf,
        preset=recommendation.preset,
        fast_copy=settings.fast_copy or settings.smart_reencode_detection,
    )


def parse_ab_crfs(value: str) -> list[int]:
    result: list[int] = []
    for part in str(value or "").replace(";", ",").split(","):
        text = part.strip()
        if not text:
            continue
        try:
            crf = int(float(text))
        except ValueError:
            continue
        if 0 <= crf <= 51 and crf not in result:
            result.append(crf)
    return result[:6]
