from typing import Any, Dict, Mapping, Optional

from config.constants import (
    HW_ENCODER_OPTIONS,
    OPERATION_MAP,
    OUT_AUDIO_FORMATS,
    OUT_IMAGE_FORMATS,
    OUT_SUBTITLE_FORMATS,
    OUT_VIDEO_FORMATS,
    POSITION_OPTIONS,
    ROTATE_OPTIONS,
    VIDEO_CODEC_OPTIONS,
)
from core.models import ConversionSettings
from utils.formatting import parse_float, parse_int, parse_time_to_seconds


def settings_map_to_model(settings_map: Mapping[str, Any], *, defaults: Optional[ConversionSettings] = None) -> ConversionSettings:
    settings = defaults or ConversionSettings()

    operation_label = str(settings_map.get("operation") or "").strip()
    settings.operation = OPERATION_MAP.get(operation_label, operation_label or settings.operation)

    out_video_format = str(settings_map.get("out_video_fmt") or settings.out_video_format).strip().lower()
    if out_video_format in OUT_VIDEO_FORMATS:
        settings.out_video_format = out_video_format

    out_image_format = str(settings_map.get("out_image_fmt") or settings.out_image_format).strip().lower()
    if out_image_format in OUT_IMAGE_FORMATS:
        settings.out_image_format = out_image_format

    out_audio_format = str(settings_map.get("out_audio_fmt") or settings.out_audio_format).strip().lower()
    if out_audio_format in OUT_AUDIO_FORMATS:
        settings.out_audio_format = out_audio_format

    out_subtitle_format = str(
        settings_map.get("out_subtitle_fmt")
        or settings_map.get("subtitle_out_fmt")
        or settings.out_subtitle_format
    ).strip().lower()
    if out_subtitle_format in OUT_SUBTITLE_FORMATS:
        settings.out_subtitle_format = out_subtitle_format
        settings.subtitle_out_format = out_subtitle_format

    settings.audio_bitrate = str(settings_map.get("audio_bitrate") or settings.audio_bitrate).strip() or settings.audio_bitrate
    settings.audio_track_index = max(0, int(settings_map.get("audio_track_index", settings.audio_track_index)))
    settings.crf = int(settings_map.get("crf", settings.crf))
    settings.preset = str(settings_map.get("preset") or settings.preset).strip()
    settings.portrait = settings_map.get("portrait") or settings.portrait
    settings.img_quality = int(settings_map.get("img_quality", settings.img_quality))
    settings.overwrite = bool(settings_map.get("overwrite", settings.overwrite))
    settings.fast_copy = bool(settings_map.get("fast_copy", settings.fast_copy))
    settings.skip_existing = bool(settings_map.get("skip_existing", settings.skip_existing))
    settings.output_template = str(settings_map.get("output_template") or settings.output_template).strip() or "{stem}"
    settings.platform_profile = str(settings_map.get("platform_profile") or settings.platform_profile).strip()

    settings.trim_start = parse_time_to_seconds(str(settings_map.get("trim_start", "")))
    settings.trim_end = parse_time_to_seconds(str(settings_map.get("trim_end", "")))
    settings.merge = bool(settings_map.get("merge", settings.merge))
    settings.merge_name = str(settings_map.get("merge_name") or settings.merge_name).strip() or "merged"

    settings.resize_w = parse_int(str(settings_map.get("resize_w", "")))
    settings.resize_h = parse_int(str(settings_map.get("resize_h", "")))
    settings.crop_w = parse_int(str(settings_map.get("crop_w", "")))
    settings.crop_h = parse_int(str(settings_map.get("crop_h", "")))
    settings.crop_x = parse_int(str(settings_map.get("crop_x", "")))
    settings.crop_y = parse_int(str(settings_map.get("crop_y", "")))
    rotate = settings_map.get("rotate") or settings.rotate
    if rotate in ROTATE_OPTIONS:
        settings.rotate = rotate

    speed = parse_float(str(settings_map.get("speed", "")))
    settings.speed = speed if speed and speed > 0 else None

    settings.subtitle_mode = str(settings_map.get("subtitle_mode") or settings.subtitle_mode).strip() or "none"
    settings.subtitle_path = str(settings_map.get("subtitle_path") or settings.subtitle_path).strip()
    settings.subtitle_stream = int(settings_map.get("subtitle_stream", settings.subtitle_stream))
    settings.subtitle_language = str(settings_map.get("subtitle_language") or settings.subtitle_language).strip() or "auto"
    settings.subtitle_model = str(settings_map.get("subtitle_model") or settings.subtitle_model).strip() or "base"
    settings.subtitle_engine = str(settings_map.get("subtitle_engine") or settings.subtitle_engine).strip() or "auto"
    subtitle_out_format = str(settings_map.get("subtitle_out_fmt") or settings.subtitle_out_format).strip().lower()
    if subtitle_out_format in OUT_SUBTITLE_FORMATS:
        settings.subtitle_out_format = subtitle_out_format
        settings.out_subtitle_format = subtitle_out_format

    settings.thumbnail_time = parse_time_to_seconds(str(settings_map.get("thumbnail_time", "")))
    settings.contact_sheet_cols = max(1, int(settings_map.get("sheet_cols", settings.contact_sheet_cols)))
    settings.contact_sheet_rows = max(1, int(settings_map.get("sheet_rows", settings.contact_sheet_rows)))
    settings.contact_sheet_width = max(80, int(settings_map.get("sheet_width", settings.contact_sheet_width)))
    settings.contact_sheet_interval = max(1, int(settings_map.get("sheet_interval", settings.contact_sheet_interval)))

    settings.watermark_path = str(settings_map.get("wm_path", settings.watermark_path))
    wm_pos = settings_map.get("wm_pos") or settings.watermark_pos
    if wm_pos in POSITION_OPTIONS:
        settings.watermark_pos = wm_pos
    settings.watermark_opacity = int(settings_map.get("wm_opacity", settings.watermark_opacity))
    settings.watermark_scale = int(settings_map.get("wm_scale", settings.watermark_scale))

    settings.text_wm = str(settings_map.get("text_wm", settings.text_wm))
    text_pos = settings_map.get("text_pos") or settings.text_pos
    if text_pos in POSITION_OPTIONS:
        settings.text_pos = text_pos
    settings.text_size = int(settings_map.get("text_size", settings.text_size))
    settings.text_color = str(settings_map.get("text_color") or settings.text_color)
    settings.text_box = bool(settings_map.get("text_box", settings.text_box))
    settings.text_box_color = str(settings_map.get("text_box_color") or settings.text_box_color)
    settings.text_box_opacity = int(settings_map.get("text_box_opacity", settings.text_box_opacity))
    settings.text_font = str(settings_map.get("text_font", settings.text_font))

    codec = settings_map.get("codec") or settings.video_codec
    if codec in VIDEO_CODEC_OPTIONS:
        settings.video_codec = codec
    hw = settings_map.get("hw") or settings.hw_encoder
    if hw in HW_ENCODER_OPTIONS:
        settings.hw_encoder = hw

    settings.replace_audio_path = str(settings_map.get("replace_audio_path") or settings.replace_audio_path).strip()
    settings.normalize_audio = str(settings_map.get("normalize_audio") or settings.normalize_audio).strip() or "none"
    peak_limit = parse_float(str(settings_map.get("audio_peak_limit_db", "")))
    settings.audio_peak_limit_db = peak_limit
    settings.trim_silence = bool(settings_map.get("trim_silence", settings.trim_silence))
    silence_threshold = parse_int(str(settings_map.get("silence_threshold_db", settings.silence_threshold_db)))
    settings.silence_threshold_db = silence_threshold if silence_threshold is not None else settings.silence_threshold_db
    silence_duration = parse_float(str(settings_map.get("silence_duration", settings.silence_duration)))
    settings.silence_duration = silence_duration if silence_duration and silence_duration > 0 else settings.silence_duration
    settings.split_chapters = bool(settings_map.get("split_chapters", settings.split_chapters))
    settings.cover_art_path = str(settings_map.get("cover_art_path") or settings.cover_art_path).strip()
    settings.before_hook = str(settings_map.get("before_hook") or settings.before_hook).strip()
    settings.after_hook = str(settings_map.get("after_hook") or settings.after_hook).strip()

    settings.copy_metadata = bool(settings_map.get("copy_metadata", settings.copy_metadata))
    settings.strip_metadata = bool(settings_map.get("strip_metadata", settings.strip_metadata))
    settings.meta_title = str(settings_map.get("meta_title", settings.meta_title))
    settings.meta_comment = str(settings_map.get("meta_comment", settings.meta_comment))
    settings.meta_author = str(settings_map.get("meta_author", settings.meta_author))
    settings.meta_copyright = str(settings_map.get("meta_copyright", settings.meta_copyright))
    settings.meta_album = str(settings_map.get("meta_album", settings.meta_album))
    settings.meta_genre = str(settings_map.get("meta_genre", settings.meta_genre))
    settings.meta_year = str(settings_map.get("meta_year", settings.meta_year))
    settings.meta_track = str(settings_map.get("meta_track", settings.meta_track))
    return settings


def merge_settings_maps(base_map: Mapping[str, Any], override_map: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base_map)
    for key, value in override_map.items():
        if value not in (None, ""):
            merged[key] = value
    return merged
