import json
from pathlib import Path
from typing import Any

from app.preset_schema import validate_settings
from utils.state import save_json_file

DEFAULT_PRESETS: dict[str, dict[str, Any]] = {
    "H.264 • Баланс (MP4)": {
        "out_video_fmt": "mp4",
        "crf": 23,
        "preset": "medium",
        "performance_profile": "Balanced",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "fast_copy": False,
    },
    "H.265 • Менший розмір (MP4)": {
        "out_video_fmt": "mp4",
        "crf": 26,
        "preset": "slow",
        "performance_profile": "Small file",
        "codec": "H.265 (HEVC)",
        "hw": "Авто",
        "fast_copy": False,
    },
    "AV1 • Якість/розмір (MKV)": {
        "out_video_fmt": "mkv",
        "crf": 30,
        "preset": "medium",
        "codec": "AV1",
        "hw": "Авто",
        "fast_copy": False,
    },
    "WebM • VP9 (Web)": {
        "out_video_fmt": "webm",
        "crf": 28,
        "preset": "slow",
        "codec": "VP9 (WebM)",
        "hw": "Авто",
        "fast_copy": False,
    },
    "GPU • NVENC H.264 (Fast)": {
        "out_video_fmt": "mp4",
        "crf": 23,
        "preset": "fast",
        "performance_profile": "Fast",
        "codec": "H.264 (AVC)",
        "hw": "NVIDIA (NVENC)",
        "fast_copy": False,
    },
    "Fast Copy (без перекодування)": {
        "fast_copy": True,
        "codec": "Авто",
        "hw": "Авто",
    },
    "GIF 480p": {
        "out_video_fmt": "gif",
        "crf": 23,
        "preset": "medium",
        "codec": "Авто",
        "fast_copy": False,
        "resize_w": "640",
        "resize_h": "",
    },
    "Фото → JPG (90)": {
        "out_image_fmt": "jpg",
        "img_quality": 90,
    },
    "Фото → WebP (80)": {
        "out_image_fmt": "webp",
        "img_quality": 80,
    },
    "Audio Only • MP3": {
        "operation": "Лише аудіо",
        "out_audio_fmt": "mp3",
        "audio_bitrate": "192k",
    },
    "YouTube • 1080p H.264": {
        "platform_profile": "YouTube",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 21,
        "preset": "medium",
        "performance_profile": "Quality",
        "resize_w": "1920",
        "resize_h": "1080",
        "audio_bitrate": "192k",
        "output_template": "{stem}_youtube",
    },
    "TikTok • 9:16": {
        "platform_profile": "TikTok",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 22,
        "preset": "fast",
        "portrait": "9:16 (1080x1920) - blur",
        "audio_bitrate": "192k",
        "output_template": "{stem}_tiktok",
    },
    "Instagram Reels • 9:16": {
        "platform_profile": "Instagram Reels",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 22,
        "preset": "fast",
        "portrait": "9:16 (1080x1920) - blur",
        "audio_bitrate": "192k",
        "output_template": "{stem}_reel",
    },
    "Instagram Stories • 9:16": {
        "platform_profile": "Instagram Stories",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 23,
        "preset": "fast",
        "portrait": "9:16 (1080x1920) - crop",
        "audio_bitrate": "160k",
        "output_template": "{stem}_story",
    },
    "Telegram • Compact MP4": {
        "platform_profile": "Telegram",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 25,
        "preset": "medium",
        "performance_profile": "Balanced",
        "resize_w": "1280",
        "resize_h": "720",
        "audio_bitrate": "128k",
        "output_template": "{stem}_telegram",
    },
    "WhatsApp • Share MP4": {
        "platform_profile": "WhatsApp",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 26,
        "preset": "fast",
        "resize_w": "854",
        "resize_h": "480",
        "audio_bitrate": "128k",
        "output_template": "{stem}_wa",
    },
    "X/Twitter • 1080p MP4": {
        "platform_profile": "X/Twitter",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 23,
        "preset": "fast",
        "resize_w": "1920",
        "resize_h": "1080",
        "audio_bitrate": "160k",
        "output_template": "{stem}_x",
    },
    "LinkedIn • 1080p MP4": {
        "platform_profile": "LinkedIn",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 22,
        "preset": "medium",
        "resize_w": "1920",
        "resize_h": "1080",
        "audio_bitrate": "192k",
        "output_template": "{stem}_linkedin",
    },
    "Discord • Compact MP4": {
        "platform_profile": "Discord",
        "out_video_fmt": "mp4",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "crf": 27,
        "preset": "fast",
        "performance_profile": "Small file",
        "resize_w": "1280",
        "resize_h": "720",
        "audio_bitrate": "128k",
        "output_template": "{stem}_discord",
    },
    "Contact Sheet • 4x4": {
        "operation": "Contact sheet",
        "sheet_cols": 4,
        "sheet_rows": 4,
        "sheet_width": 320,
        "sheet_interval": 10,
    },
    "Thumbnail • JPG": {
        "operation": "Thumbnail",
        "out_image_fmt": "jpg",
        "thumbnail_time": "00:00:05",
    },
}


for _size in (8, 25, 50):
    DEFAULT_PRESETS[f"Discord • {_size} МБ"] = {
        **DEFAULT_PRESETS["Discord • Compact MP4"],
        "performance_profile": "Balanced",
        "target_size_mb": _size,
        "smart_two_pass": True,
        "fast_copy": False,
    }
DEFAULT_PRESETS["Архів • HEVC"] = {
    **DEFAULT_PRESETS["H.265 • Менший розмір (MP4)"],
    "hw": "Тільки CPU",
    "audio_bitrate": "192k",
    "portrait": "",
    "resize_w": "",
    "resize_h": "",
}
DEFAULT_PRESETS["Максимальна сумісність • H.264"] = {
    **DEFAULT_PRESETS["H.264 • Баланс (MP4)"],
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "portrait": "",
    "resize_w": "",
    "resize_h": "",
}
# Each video preset resets settings that can otherwise leak from the previous selection.
for _preset in DEFAULT_PRESETS.values():
    if "out_video_fmt" in _preset:
        _preset.setdefault("operation", "Конвертація")
        _preset.setdefault("fast_copy", False)
        _preset.setdefault("target_size_mb", None)
        _preset.setdefault("smart_two_pass", False)
        _preset.setdefault("portrait", "")
        _preset.setdefault("resize_w", "")
        _preset.setdefault("resize_h", "")


def validate_presets(data: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict) or any(
        not isinstance(name, str) or not name.strip() or not isinstance(value, dict) for name, value in data.items()
    ):
        raise ValueError("JSON має містити об’єкт {назва: налаштування}.")
    if len({name.strip() for name in data}) != len(data):
        raise ValueError("Назви пресетів збігаються після видалення пробілів.")
    return {name.strip(): validate_settings(value) for name, value in data.items()}


def load_presets(path: Path) -> dict[str, dict[str, Any]]:
    from copy import deepcopy

    merged = deepcopy(DEFAULT_PRESETS)
    try:
        with path.open("r", encoding="utf-8") as fh:
            merged.update(validate_presets(json.load(fh)))
    except (OSError, ValueError):
        pass
    return merged


def save_presets(path: Path, presets: dict[str, dict[str, Any]]) -> None:
    save_json_file(path, validate_presets(presets))
