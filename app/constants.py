from app.paths import DEFAULT_OUTPUT_DIR, HISTORY_PATH, PRESET_PATH, STATE_PATH, THEME_PATH

APP_TITLE = "Media Converter - Photo + Video + Text"
APP_VERSION = "1.2.1"

# Timing constants used across services
PROGRESS_THROTTLE_SEC = 0.25
EVENT_POLL_INTERVAL_MS = 120
WATCH_SCAN_INTERVAL_MS = 3000
WATCH_DEBOUNCE_SEC = 2.0
RESOURCE_SAMPLE_INTERVAL_SEC = 2.0
ANALYTICS_EMIT_INTERVAL_SEC = 2.0

VIDEO_EXTS = {".mov", ".mp4", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv", ".mts", ".m2ts"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".opus", ".ogg", ".wma", ".aiff", ".aif", ".mka"}
SUBTITLE_EXTS = {".srt", ".ass", ".ssa", ".vtt", ".webvtt"}
TEXT_EXTS = {
    ".txt",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".json",
    ".csv",
    ".tsv",
    ".xml",
    ".yaml",
    ".yml",
    ".log",
    ".rtf",
    ".pdf",
    ".docx",
    ".docm",
    ".dotx",
    ".doc",
    ".odt",
    ".ott",
    ".xlsx",
    ".xlsm",
    ".xltx",
    ".xls",
    ".ods",
    ".ots",
    ".pptx",
    ".pptm",
    ".ppsx",
    ".potx",
    ".ppt",
    ".odp",
    ".otp",
}

OUT_VIDEO_FORMATS = ["mp4", "mkv", "webm", "mov", "avi", "gif", "mpg", "m2ts"]
OUT_IMAGE_FORMATS = ["jpg", "png", "webp", "bmp", "tiff"]
OUT_AUDIO_FORMATS = ["mp3", "m4a", "aac", "wav", "flac", "opus"]
OUT_SUBTITLE_FORMATS = ["srt", "ass", "vtt"]
OUT_TEXT_FORMATS = [
    "txt",
    "md",
    "html",
    "json",
    "csv",
    "tsv",
    "rtf",
    "pdf",
    "docx",
    "doc",
    "odt",
    "xlsx",
    "xls",
    "ods",
    "pptx",
    "ppt",
    "odp",
]

OPERATION_OPTIONS = [
    "Конвертація",
    "Лише аудіо",
    "Авто субтитри",
    "Витяг субтитрів",
    "Вшити субтитри",
    "Мініатюра",
    "Контакт-лист",
]
OPERATION_MAP = {
    "convert": "convert",
    "audio_only": "audio_only",
    "auto_subtitle": "auto_subtitle",
    "subtitle_extract": "subtitle_extract",
    "subtitle_burn": "subtitle_burn",
    "thumbnail": "thumbnail",
    "contact_sheet": "contact_sheet",
    "Конвертація": "convert",
    "Лише аудіо": "audio_only",
    "Авто субтитри": "auto_subtitle",
    "Витяг субтитрів": "subtitle_extract",
    "Вшити субтитри": "subtitle_burn",
    "Мініатюра": "thumbnail",
    "Контакт-лист": "contact_sheet",
    "Extract subtitle": "subtitle_extract",
    "Burn-in subtitle": "subtitle_burn",
    "Thumbnail": "thumbnail",
    "Contact sheet": "contact_sheet",
}

PORTRAIT_PRESETS = {
    "Вимкнено": None,
    "off": None,
    "9:16 (1080x1920) - crop": ("crop", 1080, 1920),
    "9:16 (1080x1920) - blur": ("blur", 1080, 1920),
    "9:16 (720x1280) - crop": ("crop", 720, 1280),
    "9:16 (720x1280) - blur": ("blur", 720, 1280),
}

VIDEO_CODEC_OPTIONS = [
    "auto",
    "H.264 (AVC)",
    "H.265 (HEVC)",
    "ProRes",
    "MPEG-2",
    "AV1",
    "VP9 (WebM)",
]
VIDEO_CODEC_MAP = {
    "auto": "auto",
    "Auto": "auto",
    "Авто": "auto",
    "H.264 (AVC)": "h264",
    "H.265 (HEVC)": "h265",
    "ProRes": "prores",
    "MPEG-2": "mpeg2",
    "AV1": "av1",
    "VP9 (WebM)": "vp9",
}

HW_ENCODER_OPTIONS = [
    "auto",
    "cpu",
    "NVIDIA (NVENC)",
    "Intel (QSV)",
    "AMD (AMF)",
]
HW_ENCODER_MAP = {
    "auto": "auto",
    "Auto": "auto",
    "Авто": "auto",
    "cpu": "cpu",
    "CPU only": "cpu",
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

PRESET_STORE = PRESET_PATH
THEME_STORE = THEME_PATH
STATE_STORE = STATE_PATH
HISTORY_STORE = HISTORY_PATH
RECENT_FOLDERS_LIMIT = 8
