from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


class TaskStatus:
    QUEUED = "queued"
    ANALYZING = "analyzing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


TASK_STATUSES = {
    TaskStatus.QUEUED,
    TaskStatus.ANALYZING,
    TaskStatus.READY,
    TaskStatus.RUNNING,
    TaskStatus.PAUSED,
    TaskStatus.SUCCESS,
    TaskStatus.FAILED,
    TaskStatus.SKIPPED,
    TaskStatus.CANCELLED,
}


@dataclass
class MediaChapter:
    index: int
    start: float
    end: float
    title: str = ""


@dataclass
class MediaInfo:
    duration: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    width: int | None = None
    height: int | None = None
    format_name: str | None = None
    size_bytes: int | None = None
    fps: float | None = None
    frame_rate_mode: str | None = None
    dynamic_range: str | None = None
    color_space: str | None = None
    color_transfer: str | None = None
    color_primaries: str | None = None
    pix_fmt: str | None = None
    rotation: int | None = None
    display_aspect_ratio: str | None = None
    audio_streams: int = 0
    subtitle_streams: int = 0
    chapters: list[MediaChapter] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class TaskItem:
    path: Path
    media_type: str
    status: str = "queued"
    last_error: str = ""
    exit_code: int | None = None
    attempts: int = 0
    last_output: str = ""
    preview_output: str = ""
    duration_text: str = "—"
    size_text: str = "—"
    thumbnail_path: str = ""
    content_hash: str = ""
    input_bytes: int = 0
    output_bytes: int = 0
    predicted_output_bytes: int = 0
    compression_ratio: float = 0.0
    progress: float = 0.0
    eta_text: str = ""
    speed_text: str = ""
    elapsed_seconds: float = 0.0
    probe_data: MediaInfo | None = None
    overrides: dict[str, Any] = field(default_factory=dict)
    resolved_settings: Optional["ConversionSettings"] = None
    smart_recommendation: str = ""
    pinned: bool = False
    priority: int = 0


@dataclass
class PreviewItem:
    source_path: Path
    output_path: Path
    operation: str
    parameters: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    command: str = ""


@dataclass
class PreviewSummary:
    items: list[PreviewItem] = field(default_factory=list)
    text: str = ""
    selected_source: str = "—"
    selected_output: str = "—"
    selected_command: str = "—"
    warnings: list[str] = field(default_factory=list)


@dataclass
class ConversionSettings:
    operation: str = "convert"
    out_video_format: str = "mp4"
    out_image_format: str = "jpg"
    out_audio_format: str = "mp3"
    out_subtitle_format: str = "srt"
    out_text_format: str = "txt"
    audio_bitrate: str = "192k"
    audio_codec: str = "auto"
    audio_track_index: int = 0
    crf: int = 23
    preset: str = "medium"
    portrait: str = "Вимкнено"
    img_quality: int = 90
    overwrite: bool = False
    fast_copy: bool = False
    skip_existing: bool = False
    output_template: str = "{stem}"
    commercial_export: bool = False
    platform_profile: str = ""
    performance_profile: str = "Balanced"
    target_size_mb: float | None = None
    cpu_load_limit: int = 95
    gpu_load_limit: int = 98

    smart_convert_enabled: bool = False
    smart_content_type: str = "auto"
    smart_quality_target: str = "balanced"
    smart_reencode_detection: bool = True
    smart_two_pass: bool = False
    smart_integrity_check: bool = False
    smart_quality_metric: str = "none"
    smart_ab_test: bool = False
    smart_ab_crfs: str = "18,23,28"
    smart_ab_duration: int = 8

    trim_start: float | None = None
    trim_end: float | None = None
    merge: bool = False
    merge_name: str = "merged"

    resize_w: int | None = None
    resize_h: int | None = None
    crop_w: int | None = None
    crop_h: int | None = None
    crop_x: int | None = None
    crop_y: int | None = None
    rotate: str = "0"
    speed: float | None = None

    subtitle_mode: str = "none"
    subtitle_path: str = ""
    subtitle_stream: int = 0
    subtitle_out_format: str = "srt"
    subtitle_language: str = "auto"
    subtitle_model: str = "base"
    subtitle_engine: str = "auto"
    subtitle_sync_ms: int = 0
    subtitle_style_enabled: bool = False
    subtitle_font_name: str = ""
    subtitle_font_size: int = 24
    subtitle_primary_color: str = "white"
    subtitle_outline: int = 1
    subtitle_shadow: int = 0
    subtitle_alignment: int = 2

    thumbnail_time: float | None = None
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

    video_codec: str = "auto"
    hw_encoder: str = "auto"
    video_profile: str = ""
    replace_audio_path: str = ""
    normalize_audio: str = "none"
    audio_peak_limit_db: float | None = None
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

    device_profile: str = ""

    privacy_blur_regions: str = ""
    ai_blur_enabled: bool = False
    checksum_algorithm: str = "none"
    secure_delete_original: bool = False

    editor_deinterlace: bool = False
    editor_stabilize: bool = False
    editor_denoise: str = "none"
    editor_brightness: float = 0.0
    editor_contrast: float = 1.0
    editor_saturation: float = 1.0
    editor_gamma: float = 1.0
    editor_lut_path: str = ""

    cloud_upload_enabled: bool = False
    cloud_provider: str = "rclone"
    cloud_rclone_path: str = "rclone"
    cloud_remote_path: str = ""
