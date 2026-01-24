import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "H.264 • Баланс (MP4)": {
        "out_video_fmt": "mp4",
        "crf": 23,
        "preset": "medium",
        "codec": "H.264 (AVC)",
        "hw": "Авто",
        "fast_copy": False,
    },
    "H.265 • Менший розмір (MP4)": {
        "out_video_fmt": "mp4",
        "crf": 26,
        "preset": "slow",
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
}


def load_presets(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return dict(DEFAULT_PRESETS)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            merged = dict(DEFAULT_PRESETS)
            merged.update(data)
            return merged
    except Exception:
        return dict(DEFAULT_PRESETS)
    return dict(DEFAULT_PRESETS)


def save_presets(path: Path, presets: Dict[str, Dict[str, Any]]) -> None:
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(presets, fh, ensure_ascii=False, indent=2)
    except Exception:
        return
