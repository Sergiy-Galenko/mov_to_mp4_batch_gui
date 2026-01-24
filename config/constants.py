from pathlib import Path

APP_TITLE = "Media Converter — Фото + Відео (FFmpeg)"

VIDEO_EXTS = {".mov", ".mp4", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv", ".mts", ".m2ts"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}

OUT_VIDEO_FORMATS = ["mp4", "mkv", "webm", "mov", "avi", "gif"]
OUT_IMAGE_FORMATS = ["jpg", "png", "webp", "bmp", "tiff"]

PORTRAIT_PRESETS = {
    "Вимкнено": None,
    "9:16 (1080x1920) - crop": ("crop", 1080, 1920),
    "9:16 (1080x1920) - blur": ("blur", 1080, 1920),
    "9:16 (720x1280) - crop": ("crop", 720, 1280),
    "9:16 (720x1280) - blur": ("blur", 720, 1280),
}

VIDEO_CODEC_OPTIONS = [
    "Авто",
    "H.264 (AVC)",
    "H.265 (HEVC)",
    "AV1",
    "VP9 (WebM)",
]
VIDEO_CODEC_MAP = {
    "Авто": "auto",
    "H.264 (AVC)": "h264",
    "H.265 (HEVC)": "h265",
    "AV1": "av1",
    "VP9 (WebM)": "vp9",
}

HW_ENCODER_OPTIONS = [
    "Авто",
    "Тільки CPU",
    "NVIDIA (NVENC)",
    "Intel (QSV)",
    "AMD (AMF)",
]
HW_ENCODER_MAP = {
    "Авто": "auto",
    "Тільки CPU": "cpu",
    "NVIDIA (NVENC)": "nvidia",
    "Intel (QSV)": "intel",
    "AMD (AMF)": "amd",
}

ROTATE_OPTIONS = ["0", "90° вправо", "90° вліво", "180°"]
ROTATE_MAP = {
    "0": None,
    "90° вправо": "transpose=1",
    "90° вліво": "transpose=2",
    "180°": "transpose=1,transpose=1",
}

POSITION_OPTIONS = [
    "Верх-ліворуч",
    "Верх-праворуч",
    "Низ-ліворуч",
    "Низ-праворуч",
    "Центр",
]
POSITION_MAP = {
    "Верх-ліворуч": "10:10",
    "Верх-праворуч": "W-w-10:10",
    "Низ-ліворуч": "10:H-h-10",
    "Низ-праворуч": "W-w-10:H-h-10",
    "Центр": "(W-w)/2:(H-h)/2",
}

THEMES = ["light", "dark"]
DEFAULT_THEME = "light"

PRESET_STORE = Path.home() / ".media_converter_gui_presets.json"
DEFAULT_OUTPUT_DIR = Path.home() / "Videos" / "converted"
THEME_STORE = Path.home() / ".media_converter_gui_theme.json"
