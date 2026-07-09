from __future__ import annotations

from dataclasses import replace

from app.models import ConversionSettings

DEVICE_PROFILE_NAMES = [
    "None",
    "iPhone 14/15/16",
    "iPad Pro",
    "Apple TV 4K HDR",
    "Android H.264 baseline",
    "Samsung TV",
    "PlayStation 5",
    "Xbox Series X",
    "Chromecast / Fire TV",
    "GoPro import",
    "DJI Drone import",
    "Steam Deck",
    "DVD compatible",
    "Blu-ray compatible",
]


DEVICE_PROFILE_DEFAULTS: dict[str, dict[str, object]] = {
    "iPhone 14/15/16": {"out_video_format": "mp4", "video_codec": "H.265 (HEVC)", "audio_codec": "aac", "crf": 22, "preset": "medium"},
    "iPad Pro": {"out_video_format": "mov", "video_codec": "ProRes", "audio_codec": "aac", "crf": 18, "preset": "slow"},
    "Apple TV 4K HDR": {"out_video_format": "mp4", "video_codec": "H.265 (HEVC)", "audio_codec": "aac", "crf": 20, "preset": "slow"},
    "Android H.264 baseline": {"out_video_format": "mp4", "video_codec": "H.264 (AVC)", "video_profile": "baseline", "audio_codec": "aac", "crf": 23, "preset": "medium"},
    "Samsung TV": {"out_video_format": "mkv", "video_codec": "H.264 (AVC)", "audio_codec": "ac3", "audio_bitrate": "384k", "crf": 22, "preset": "medium"},
    "PlayStation 5": {"out_video_format": "mp4", "video_codec": "H.264 (AVC)", "audio_codec": "aac", "crf": 21, "preset": "medium"},
    "Xbox Series X": {"out_video_format": "mp4", "video_codec": "H.265 (HEVC)", "audio_codec": "aac", "crf": 21, "preset": "medium"},
    "Chromecast / Fire TV": {"out_video_format": "mp4", "video_codec": "H.264 (AVC)", "audio_codec": "aac", "crf": 24, "preset": "fast"},
    "GoPro import": {"out_video_format": "mp4", "video_codec": "H.264 (AVC)", "audio_codec": "aac", "crf": 18, "preset": "fast"},
    "DJI Drone import": {"out_video_format": "mp4", "video_codec": "H.265 (HEVC)", "audio_codec": "aac", "crf": 18, "preset": "fast"},
    "Steam Deck": {"out_video_format": "mkv", "video_codec": "H.264 (AVC)", "audio_codec": "aac", "crf": 22, "preset": "medium"},
    "DVD compatible": {"out_video_format": "mpg", "video_codec": "MPEG-2", "audio_codec": "ac3", "audio_bitrate": "192k", "crf": 26, "preset": "fast"},
    "Blu-ray compatible": {"out_video_format": "m2ts", "video_codec": "H.264 (AVC)", "video_profile": "high", "audio_codec": "ac3", "audio_bitrate": "448k", "crf": 20, "preset": "slow"},
}


def apply_device_profile(settings: ConversionSettings, profile_name: str) -> ConversionSettings:
    profile = str(profile_name or "").strip()
    if profile not in DEVICE_PROFILE_DEFAULTS:
        return replace(settings, device_profile="")
    values = DEVICE_PROFILE_DEFAULTS[profile]
    return replace(settings, device_profile=profile, **values)
