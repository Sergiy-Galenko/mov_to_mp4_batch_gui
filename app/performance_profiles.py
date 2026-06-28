from __future__ import annotations

from dataclasses import replace
from typing import Dict

from app.models import ConversionSettings


PROFILE_NAMES = ["Quality", "Balanced", "Fast", "Small file"]


PROFILE_DEFAULTS: Dict[str, Dict[str, object]] = {
    "Quality": {
        "crf": 18,
        "preset": "slow",
        "codec": "H.264 (AVC)",
        "hw": "auto",
    },
    "Balanced": {
        "crf": 23,
        "preset": "medium",
        "codec": "H.264 (AVC)",
        "hw": "auto",
    },
    "Fast": {
        "crf": 25,
        "preset": "fast",
        "codec": "H.264 (AVC)",
        "hw": "auto",
    },
    "Small file": {
        "crf": 28,
        "preset": "slow",
        "codec": "H.265 (HEVC)",
        "hw": "auto",
    },
}


def normalize_profile(name: str) -> str:
    value = str(name or "").strip()
    return value if value in PROFILE_DEFAULTS else "Balanced"


def apply_performance_profile(settings: ConversionSettings) -> ConversionSettings:
    profile = normalize_profile(settings.performance_profile)
    defaults = PROFILE_DEFAULTS[profile]
    return replace(
        settings,
        performance_profile=profile,
        crf=int(defaults["crf"]),
        preset=str(defaults["preset"]),
        video_codec=str(defaults["codec"]),
        hw_encoder=str(defaults["hw"]),
    )


def prediction_factor(profile: str) -> float:
    profile = normalize_profile(profile)
    if profile == "Quality":
        return 0.85
    if profile == "Fast":
        return 0.75
    if profile == "Small file":
        return 0.45
    return 0.65
