from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MediaChapter:
    index: int
    start: float
    end: float
    title: str = ""


@dataclass
class MediaInfo:
    duration: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format_name: Optional[str] = None
    size_bytes: Optional[int] = None
    fps: Optional[float] = None
    frame_rate_mode: Optional[str] = None
    dynamic_range: Optional[str] = None
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    pix_fmt: Optional[str] = None
    rotation: Optional[int] = None
    display_aspect_ratio: Optional[str] = None
    audio_streams: int = 0
    subtitle_streams: int = 0
    chapters: List[MediaChapter] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TaskItem:
    path: Path
    media_type: str
    status: str = "queued"
    last_error: str = ""
    attempts: int = 0
    last_output: str = ""
    preview_output: str = ""
    duration_text: str = "—"
    size_text: str = "—"
    thumbnail_path: str = ""
    content_hash: str = ""
    overrides: Dict[str, Any] = field(default_factory=dict)
    resolved_settings: Optional["ConversionSettings"] = None


@dataclass
class ConversionSettings:
    operation: str = "convert"
    out_video_format: str = "mp4"
    out_image_format: str = "jpg"
    out_audio_format: str = "mp3"
    out_subtitle_format: str = "srt"
    audio_bitrate: str = "192k"
    audio_track_index: int = 0
    crf: int = 23
    preset: str = "medium"
    portrait: str = "Вимкнено"
    img_quality: int = 90
    overwrite: bool = False
    fast_copy: bool = False
    skip_existing: bool = False
    output_template: str = "{stem}"
    platform_profile: str = ""

    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    merge: bool = False
    merge_name: str = "merged"

    resize_w: Optional[int] = None
    resize_h: Optional[int] = None
    crop_w: Optional[int] = None
    crop_h: Optional[int] = None
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    rotate: str = "0"
    speed: Optional[float] = None

    subtitle_mode: str = "none"
    subtitle_path: str = ""
    subtitle_stream: int = 0
    subtitle_out_format: str = "srt"
    subtitle_language: str = "auto"
    subtitle_model: str = "base"
    subtitle_engine: str = "auto"

    thumbnail_time: Optional[float] = None
    contact_sheet_cols: int = 4
    contact_sheet_rows: int = 4
    contact_sheet_width: int = 320
    contact_sheet_interval: int = 10

    watermark_path: str = ""
    watermark_pos: str = "Низ-праворуч"
    watermark_opacity: int = 80
    watermark_scale: int = 30

    text_wm: str = ""
    text_pos: str = "Низ-праворуч"
    text_size: int = 24
    text_color: str = "white"
    text_box: bool = False
    text_box_color: str = "black"
    text_box_opacity: int = 50
    text_font: str = ""

    video_codec: str = "Авто"
    hw_encoder: str = "Авто"
    replace_audio_path: str = ""
    normalize_audio: str = "none"
    audio_peak_limit_db: Optional[float] = None
    trim_silence: bool = False
    silence_threshold_db: int = -50
    silence_duration: float = 0.3
    split_chapters: bool = False
    cover_art_path: str = ""
    before_hook: str = ""
    after_hook: str = ""

    strip_metadata: bool = False
    copy_metadata: bool = False
    meta_title: str = ""
    meta_comment: str = ""
    meta_author: str = ""
    meta_copyright: str = ""
    meta_album: str = ""
    meta_genre: str = ""
    meta_year: str = ""
    meta_track: str = ""
