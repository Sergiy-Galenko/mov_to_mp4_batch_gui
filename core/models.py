from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MediaInfo:
    duration: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format_name: Optional[str] = None
    size_bytes: Optional[int] = None


@dataclass
class TaskItem:
    path: Path
    media_type: str


@dataclass
class ConversionSettings:
    out_video_format: str = "mp4"
    out_image_format: str = "jpg"
    crf: int = 23
    preset: str = "medium"
    portrait: str = "Вимкнено"
    img_quality: int = 90
    overwrite: bool = False
    fast_copy: bool = False

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

    strip_metadata: bool = False
    copy_metadata: bool = False
    meta_title: str = ""
    meta_comment: str = ""
    meta_author: str = ""
    meta_copyright: str = ""
