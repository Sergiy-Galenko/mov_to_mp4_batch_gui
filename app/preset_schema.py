"""Validate portable preset data without silently coercing malformed settings."""

import math
import re
from dataclasses import fields
from typing import get_args, get_type_hints

from app.constants import (
    HW_ENCODER_MAP,
    OPERATION_MAP,
    OUT_AUDIO_FORMATS,
    OUT_IMAGE_FORMATS,
    OUT_SUBTITLE_FORMATS,
    OUT_TEXT_FORMATS,
    OUT_VIDEO_FORMATS,
    PORTRAIT_PRESETS,
    VIDEO_CODEC_MAP,
)
from app.models import ConversionSettings
from app.performance_profiles import PROFILE_NAMES
from app.settings import SETTINGS_SCHEMA
from utils.formatting import parse_time_to_seconds

ALIASES = {
    "out_video_fmt": "out_video_format",
    "out_image_fmt": "out_image_format",
    "out_audio_fmt": "out_audio_format",
    "out_subtitle_fmt": "out_subtitle_format",
    "out_text_fmt": "out_text_format",
    "subtitle_out_fmt": "subtitle_out_format",
    "codec": "video_codec",
    "hw": "hw_encoder",
    "sheet_cols": "contact_sheet_cols",
    "sheet_rows": "contact_sheet_rows",
    "sheet_width": "contact_sheet_width",
    "sheet_interval": "contact_sheet_interval",
    "wm_path": "watermark_path",
    "wm_pos": "watermark_pos",
    "wm_opacity": "watermark_opacity",
    "wm_scale": "watermark_scale",
    "text_wm": "text_wm",
    "text_pos": "text_pos",
}
ENUMS = {
    "operation": set(OPERATION_MAP),
    "codec": set(VIDEO_CODEC_MAP),
    "hw": set(HW_ENCODER_MAP),
    "out_video_fmt": set(OUT_VIDEO_FORMATS),
    "out_image_fmt": set(OUT_IMAGE_FORMATS),
    "out_audio_fmt": set(OUT_AUDIO_FORMATS),
    "out_subtitle_fmt": set(OUT_SUBTITLE_FORMATS),
    "subtitle_out_fmt": set(OUT_SUBTITLE_FORMATS),
    "out_text_fmt": set(OUT_TEXT_FORMATS),
    "portrait": set(PORTRAIT_PRESETS) | {""},
    "performance_profile": set(PROFILE_NAMES),
    "preset": {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"},
    "audio_codec": {"auto", "aac", "ac3", "opus", "mp3", "copy"},
    "output_collision_policy": {"stop", "index", "parent", "overwrite", "skip"},
    "smart_content_type": {"auto", "animation", "live_action", "screencast"},
    "smart_quality_target": {"small", "balanced", "quality"},
    "smart_quality_metric": {"none", "ssim", "psnr", "vmaf"},
    "subtitle_mode": {"none", "burn", "burn_in", "copy", "embed", "extract"},
    "subtitle_engine": {"auto", "whisper", "openai-whisper", "faster-whisper"},
    "subtitle_device": {"auto", "cpu", "cuda", "mps"},
    "normalize_audio": {"none", "peak", "loudnorm", "ebu_r128", "ebu_r128_2pass"},
    "checksum_algorithm": {"none", "md5", "sha256", "sha512"},
    "editor_denoise": {"none", "light", "medium", "strong", "hqdn3d", "nlmeans"},
    "language": {"uk", "en", "pl", "de"},
}
RANGES = {
    "target_size_mb": (0.000001, None),
    "crf": (0, 51),
    "img_quality": (1, 100),
    "cpu_load_limit": (1, 100),
    "gpu_load_limit": (1, 100),
    "watermark_opacity": (0, 100),
    "watermark_scale": (1, 100),
    "text_box_opacity": (0, 100),
    "audio_track_index": (0, None),
    "subtitle_stream": (0, None),
    "concurrency_limit": (0, 16),
    "disk_safety_margin_mb": (0, 10240),
    "crop_x": (0, None),
    "crop_y": (0, None),
    "silence_threshold_db": (-120, 0),
    "subtitle_sync_ms": (None, None),
    "subtitle_outline": (0, 20),
    "subtitle_shadow": (0, 20),
    "subtitle_alignment": (1, 9),
    "editor_contrast": (0, None),
    "editor_saturation": (0, None),
    "audio_peak_limit_db": (-100, 0),
    "editor_brightness": (-1, 1),
}
TIME_FIELDS = {"trim_start", "trim_end", "thumbnail_time"}


def validate_settings(data: dict) -> dict:
    hints = get_type_hints(ConversionSettings)
    defaults = {field.name: field.default for field in fields(ConversionSettings)}
    result = {}
    for key, value in data.items():
        canonical = ALIASES.get(key, key)
        if canonical not in hints and key not in SETTINGS_SCHEMA:
            raise ValueError(f"Невідоме налаштування: {key}.")
        if key in ENUMS and (not isinstance(value, str) or value not in ENUMS[key]):
            raise ValueError(f"{key}: недопустиме значення {value!r}.")
        if key in TIME_FIELDS:
            if value not in (None, "") and (isinstance(value, bool) or parse_time_to_seconds(str(value)) is None):
                raise ValueError(f"{key}: очікуються секунди або hh:mm:ss.")
            result[key] = value
            continue
        if key == "audio_bitrate" and (not isinstance(value, str) or not re.fullmatch(r"(?:\d+(?:\.\d+)?[kKmM]?|)", value)):
            raise ValueError("audio_bitrate: очікується бітрейт на кшталт 128k.")
        hint = hints.get(canonical, SETTINGS_SCHEMA.get(key, (str,))[0])
        types = get_args(hint) or (hint,)
        if bool in types:
            if not isinstance(value, bool):
                raise ValueError(f"{key}: очікується true або false.")
        elif int in types or float in types:
            if value in (None, ""):
                if value is None and type(None) not in types:
                    raise ValueError(f"{key}: очікується число.")
            else:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{key}: очікується число.") from None
                if isinstance(value, bool) or not math.isfinite(number) or (int in types and not number.is_integer()):
                    raise ValueError(f"{key}: некоректне число.")
                low, high = RANGES.get(canonical, (0 if defaults.get(canonical) == 0 else 0.000001, None))
                if (low is not None and number < low) or (high is not None and number > high):
                    raise ValueError(f"{key}: число поза допустимим діапазоном.")
                value = int(number) if int in types else number
        elif not isinstance(value, str) and not (value is None and type(None) in types):
            raise ValueError(f"{key}: очікується текст.")
        result[key] = value
    return result
