import os
import sys
import threading
import queue
import subprocess
import shutil
import json
import time
import tempfile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Media Converter (Фото + Відео) — FFmpeg"
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

PRESET_STORE = Path.home() / ".media_converter_gui_presets.json"

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

POSITION_OPTIONS = ["Верх-ліворуч", "Верх-праворуч", "Низ-ліворуч", "Низ-праворуч", "Центр"]
POSITION_MAP = {
    "Верх-ліворуч": "10:10",
    "Верх-праворуч": "W-w-10:10",
    "Низ-ліворуч": "10:H-h-10",
    "Низ-праворуч": "W-w-10:H-h-10",
    "Центр": "(W-w)/2:(H-h)/2",
}

def find_ffmpeg() -> Optional[str]:
    local = Path(__file__).resolve().parent
    candidates = [
        local / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        local / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)
    return shutil.which("ffmpeg")

def find_ffprobe(ffmpeg_path: Optional[str]) -> Optional[str]:
    local = Path(__file__).resolve().parent
    candidates = []
    if ffmpeg_path:
        ffmpeg_dir = Path(ffmpeg_path).resolve().parent
        candidates.append(ffmpeg_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe"))
    candidates.extend([
        local / ("ffprobe.exe" if os.name == "nt" else "ffprobe"),
        local / "bin" / ("ffprobe.exe" if os.name == "nt" else "ffprobe"),
    ])
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)
    return shutil.which("ffprobe")

def is_video(p: Path) -> bool:
    return p.suffix.lower() in VIDEO_EXTS

def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS

def media_type(p: Path) -> Optional[str]:
    if is_video(p):
        return "video"
    if is_image(p):
        return "image"
    return None

def safe_output_name(out_dir: Path, in_path: Path, out_ext: str) -> Path:
    out_ext = out_ext.lstrip(".")
    base = in_path.stem
    out_path = out_dir / f"{base}.{out_ext}"
    if not out_path.exists():
        return out_path
    i = 1
    while True:
        cand = out_dir / f"{base} ({i}).{out_ext}"
        if not cand.exists():
            return cand
        i += 1

@dataclass
class MediaInfo:
    duration: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format_name: Optional[str] = None
    size_bytes: Optional[int] = None

def format_time(seconds: Optional[float]) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_bytes(size: Optional[int]) -> str:
    if size is None:
        return "--"
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"

def parse_time_to_seconds(text: str) -> Optional[float]:
    raw = text.strip()
    if not raw:
        return None
    if re.fullmatch(r"\\d+(\\.\\d+)?", raw):
        return float(raw)
    parts = raw.split(":")
    try:
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return None
    return None

def parse_float(text: str) -> Optional[float]:
    raw = text.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None

def parse_int(text: str) -> Optional[int]:
    raw = text.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None

def build_atempo_chain(speed: float) -> List[float]:
    if speed <= 0:
        return []
    factors = []
    while speed > 2.0:
        factors.append(2.0)
        speed /= 2.0
    while speed < 0.5:
        factors.append(0.5)
        speed /= 0.5
    factors.append(speed)
    return factors

def escape_drawtext(text: str) -> str:
    return text.replace("\\\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "\\\\'")

def escape_filter_path(path: str) -> str:
    return path.replace("\\\\", "/").replace(":", "\\\\:")

def parse_ffmpeg_time(value: str) -> Optional[float]:
    raw = value.strip()
    if not raw:
        return None
    if re.fullmatch(r"\\d+(\\.\\d+)?", raw):
        return float(raw)
    parts = raw.split(":")
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except ValueError:
            return None
    return None

class ConverterUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1020x720")
        self.minsize(940, 650)

        self.ffmpeg_path: Optional[str] = find_ffmpeg()
        self.ffprobe_path: Optional[str] = find_ffprobe(self.ffmpeg_path)
        self.encoder_caps: set[str] = set()
        self.tasks: List[Tuple[Path, str]] = []
        self.media_info: Dict[Path, MediaInfo] = {}
        self.stop_requested = False
        self.worker_thread: Optional[threading.Thread] = None
        self.current_proc: Optional[subprocess.Popen] = None
        self.ui_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()

        self.presets_path = PRESET_STORE
        self.presets: Dict[str, Dict[str, Any]] = self._load_presets()

        self.total_start_time: Optional[float] = None
        self.total_duration: float = 0.0
        self.done_duration: float = 0.0
        self.current_duration: Optional[float] = None
        self.current_file_start: Optional[float] = None

        self._build_ui()
        self._poll_queue()

        self._log("INFO", "Підтримка: відео + фото. Тип визначається автоматично по розширенню.")
        if self.ffmpeg_path:
            self._log("OK", f"FFmpeg знайдено: {self.ffmpeg_path}")
            self.ffmpeg_var.set(self.ffmpeg_path)
        else:
            self._log("ERROR", "FFmpeg не знайдено. Натисни 'Вказати ffmpeg.exe' або додай ffmpeg у PATH.")

        self._refresh_ffmpeg_tools(log_initial=True)
        self._refresh_preset_list()

    def _build_ui(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="FFmpeg:").grid(row=0, column=0, sticky="w")
        self.ffmpeg_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.ffmpeg_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="Вказати ffmpeg.exe", command=self.pick_ffmpeg).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Перевірити", command=self.check_ffmpeg).grid(row=0, column=3, padx=4)

        ttk.Label(top, text="Джерело:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.src_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.src_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(top, text="Вибрати папку", command=self.pick_folder).grid(row=1, column=2, padx=4, pady=(10, 0))
        ttk.Button(top, text="Вибрати файли", command=self.pick_files).grid(row=1, column=3, padx=4, pady=(10, 0))

        ttk.Label(top, text="Папка виводу:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.out_var = tk.StringVar(value=str(Path.home() / "Videos" / "converted"))
        ttk.Entry(top, textvariable=self.out_var).grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(top, text="Вибрати", command=self.pick_output).grid(row=2, column=2, padx=4, pady=(10, 0))
        ttk.Button(top, text="Відкрити папку", command=self.open_output_folder).grid(row=2, column=3, padx=4, pady=(10, 0))

        top.columnconfigure(1, weight=1)

        opts_nb = ttk.Notebook(self)
        opts_nb.pack(fill="x", padx=12, pady=(0, 10))

        basic = ttk.Frame(opts_nb, padding=8)
        advanced = ttk.Frame(opts_nb, padding=8)
        codec_tab = ttk.Frame(opts_nb, padding=8)
        presets_tab = ttk.Frame(opts_nb, padding=8)
        metadata_tab = ttk.Frame(opts_nb, padding=8)

        opts_nb.add(basic, text="Базові")
        opts_nb.add(advanced, text="Розширені")
        opts_nb.add(codec_tab, text="Кодеки/GPU")
        opts_nb.add(presets_tab, text="Пресети")
        opts_nb.add(metadata_tab, text="Метадані")

        ttk.Label(basic, text="Відео → формат:").grid(row=0, column=0, sticky="w")
        self.out_video_fmt_var = tk.StringVar(value="mp4")
        ttk.Combobox(
            basic,
            textvariable=self.out_video_fmt_var,
            values=OUT_VIDEO_FORMATS,
            state="readonly",
            width=10,
        ).grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(basic, text="CRF:").grid(row=0, column=2, sticky="w")
        self.crf_var = tk.IntVar(value=23)
        ttk.Spinbox(basic, from_=14, to=35, textvariable=self.crf_var, width=6)\
            .grid(row=0, column=3, sticky="w", padx=(8, 18))

        ttk.Label(basic, text="Preset:").grid(row=0, column=4, sticky="w")
        self.preset_var = tk.StringVar(value="medium")
        ttk.Combobox(
            basic,
            textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            state="readonly",
            width=10,
        ).grid(row=0, column=5, sticky="w")

        ttk.Label(basic, text="Зробити вертикальним:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.portrait_var = tk.StringVar(value="Вимкнено")
        ttk.Combobox(
            basic,
            textvariable=self.portrait_var,
            values=list(PORTRAIT_PRESETS.keys()),
            state="readonly",
            width=26,
        ).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(10, 0))
        ttk.Label(basic, text="(тільки для відео)").grid(row=1, column=2, sticky="w", pady=(10, 0))

        ttk.Label(basic, text="Фото → формат:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.out_image_fmt_var = tk.StringVar(value="jpg")
        ttk.Combobox(
            basic,
            textvariable=self.out_image_fmt_var,
            values=OUT_IMAGE_FORMATS,
            state="readonly",
            width=10,
        ).grid(row=2, column=1, sticky="w", padx=(8, 18), pady=(10, 0))

        ttk.Label(basic, text="Якість фото (1–100):").grid(row=2, column=2, sticky="w", pady=(10, 0))
        self.img_quality_var = tk.IntVar(value=90)
        ttk.Spinbox(basic, from_=1, to=100, textvariable=self.img_quality_var, width=6)\
            .grid(row=2, column=3, sticky="w", padx=(8, 18), pady=(10, 0))

        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(basic, text="Перезаписувати існуючі файли", variable=self.overwrite_var)\
            .grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.fast_copy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(basic, text="Швидко для відео (copy без перекодування, якщо можливо)", variable=self.fast_copy_var)\
            .grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))

        advanced.columnconfigure(0, weight=1)

        time_frame = ttk.LabelFrame(advanced, text="Час / Об'єднання", padding=8)
        time_frame.grid(row=0, column=0, sticky="ew", pady=4)
        time_frame.columnconfigure(1, weight=1)
        time_frame.columnconfigure(3, weight=1)

        ttk.Label(time_frame, text="Початок (hh:mm:ss або сек):").grid(row=0, column=0, sticky="w")
        self.trim_start_var = tk.StringVar(value="")
        ttk.Entry(time_frame, textvariable=self.trim_start_var, width=12).grid(row=0, column=1, sticky="w", padx=(6, 18))
        ttk.Label(time_frame, text="Кінець (hh:mm:ss або сек):").grid(row=0, column=2, sticky="w")
        self.trim_end_var = tk.StringVar(value="")
        ttk.Entry(time_frame, textvariable=self.trim_end_var, width=12).grid(row=0, column=3, sticky="w", padx=(6, 0))

        self.merge_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(time_frame, text="Об'єднати всі відео в один файл", variable=self.merge_var)\
            .grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(time_frame, text="Назва файлу:").grid(row=1, column=2, sticky="w", pady=(8, 0))
        self.merge_name_var = tk.StringVar(value="merged")
        ttk.Entry(time_frame, textvariable=self.merge_name_var).grid(row=1, column=3, sticky="w", padx=(6, 0), pady=(8, 0))

        transform_frame = ttk.LabelFrame(advanced, text="Трансформації", padding=8)
        transform_frame.grid(row=1, column=0, sticky="ew", pady=4)

        ttk.Label(transform_frame, text="Resize W:").grid(row=0, column=0, sticky="w")
        self.resize_w_var = tk.StringVar(value="")
        ttk.Entry(transform_frame, textvariable=self.resize_w_var, width=6).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(transform_frame, text="H:").grid(row=0, column=2, sticky="w")
        self.resize_h_var = tk.StringVar(value="")
        ttk.Entry(transform_frame, textvariable=self.resize_h_var, width=6).grid(row=0, column=3, sticky="w", padx=(6, 0))

        ttk.Label(transform_frame, text="Crop W:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.crop_w_var = tk.StringVar(value="")
        ttk.Entry(transform_frame, textvariable=self.crop_w_var, width=6).grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(6, 0))
        ttk.Label(transform_frame, text="H:").grid(row=1, column=2, sticky="w", pady=(6, 0))
        self.crop_h_var = tk.StringVar(value="")
        ttk.Entry(transform_frame, textvariable=self.crop_h_var, width=6).grid(row=1, column=3, sticky="w", padx=(6, 12), pady=(6, 0))
        ttk.Label(transform_frame, text="X:").grid(row=1, column=4, sticky="w", pady=(6, 0))
        self.crop_x_var = tk.StringVar(value="")
        ttk.Entry(transform_frame, textvariable=self.crop_x_var, width=6).grid(row=1, column=5, sticky="w", padx=(6, 12), pady=(6, 0))
        ttk.Label(transform_frame, text="Y:").grid(row=1, column=6, sticky="w", pady=(6, 0))
        self.crop_y_var = tk.StringVar(value="")
        ttk.Entry(transform_frame, textvariable=self.crop_y_var, width=6).grid(row=1, column=7, sticky="w", padx=(6, 0), pady=(6, 0))

        ttk.Label(transform_frame, text="Rotate:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.rotate_var = tk.StringVar(value="0")
        ttk.Combobox(
            transform_frame,
            textvariable=self.rotate_var,
            values=ROTATE_OPTIONS,
            state="readonly",
            width=14,
        ).grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(6, 0))

        speed_frame = ttk.LabelFrame(advanced, text="Швидкість", padding=8)
        speed_frame.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Label(speed_frame, text="Speed (0.25–4.0):").grid(row=0, column=0, sticky="w")
        self.speed_var = tk.StringVar(value="1.0")
        ttk.Entry(speed_frame, textvariable=self.speed_var, width=8).grid(row=0, column=1, sticky="w", padx=(6, 0))

        wm_frame = ttk.LabelFrame(advanced, text="Водяний знак", padding=8)
        wm_frame.grid(row=3, column=0, sticky="ew", pady=4)
        wm_frame.columnconfigure(1, weight=1)

        ttk.Label(wm_frame, text="Зображення:").grid(row=0, column=0, sticky="w")
        self.wm_path_var = tk.StringVar(value="")
        ttk.Entry(wm_frame, textvariable=self.wm_path_var).grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ttk.Button(wm_frame, text="Вибрати", command=self.pick_watermark).grid(row=0, column=2)

        ttk.Label(wm_frame, text="Позиція:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.wm_pos_var = tk.StringVar(value=POSITION_OPTIONS[3])
        ttk.Combobox(
            wm_frame,
            textvariable=self.wm_pos_var,
            values=POSITION_OPTIONS,
            state="readonly",
            width=16,
        ).grid(row=1, column=1, sticky="w", padx=(6, 18), pady=(6, 0))
        ttk.Label(wm_frame, text="Opacity %:").grid(row=1, column=2, sticky="w", pady=(6, 0))
        self.wm_opacity_var = tk.IntVar(value=80)
        ttk.Spinbox(wm_frame, from_=0, to=100, textvariable=self.wm_opacity_var, width=6)\
            .grid(row=1, column=3, sticky="w", pady=(6, 0))
        ttk.Label(wm_frame, text="Scale %:").grid(row=1, column=4, sticky="w", pady=(6, 0))
        self.wm_scale_var = tk.IntVar(value=30)
        ttk.Spinbox(wm_frame, from_=1, to=100, textvariable=self.wm_scale_var, width=6)\
            .grid(row=1, column=5, sticky="w", pady=(6, 0))

        ttk.Label(wm_frame, text="Текст:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.text_wm_var = tk.StringVar(value="")
        ttk.Entry(wm_frame, textvariable=self.text_wm_var).grid(row=2, column=1, sticky="ew", padx=(6, 6), pady=(8, 0))
        ttk.Label(wm_frame, text="Позиція:").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.text_pos_var = tk.StringVar(value=POSITION_OPTIONS[3])
        ttk.Combobox(
            wm_frame,
            textvariable=self.text_pos_var,
            values=POSITION_OPTIONS,
            state="readonly",
            width=16,
        ).grid(row=2, column=3, sticky="w", pady=(8, 0))

        ttk.Label(wm_frame, text="Розмір:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.text_size_var = tk.IntVar(value=24)
        ttk.Spinbox(wm_frame, from_=8, to=128, textvariable=self.text_size_var, width=6)\
            .grid(row=3, column=1, sticky="w", padx=(6, 18), pady=(6, 0))
        ttk.Label(wm_frame, text="Колір:").grid(row=3, column=2, sticky="w", pady=(6, 0))
        self.text_color_var = tk.StringVar(value="white")
        ttk.Entry(wm_frame, textvariable=self.text_color_var, width=10).grid(row=3, column=3, sticky="w", pady=(6, 0))

        ttk.Label(wm_frame, text="Шрифт (.ttf):").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.text_font_var = tk.StringVar(value="")
        ttk.Entry(wm_frame, textvariable=self.text_font_var).grid(row=4, column=1, sticky="ew", padx=(6, 6), pady=(6, 0))
        ttk.Button(wm_frame, text="Вибрати", command=self.pick_font).grid(row=4, column=2, pady=(6, 0))

        ttk.Label(codec_tab, text="Відеокодек:").grid(row=0, column=0, sticky="w")
        self.codec_var = tk.StringVar(value="Авто")
        ttk.Combobox(
            codec_tab,
            textvariable=self.codec_var,
            values=VIDEO_CODEC_OPTIONS,
            state="readonly",
            width=18,
        ).grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(codec_tab, text="GPU/Encoder:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.hw_var = tk.StringVar(value="Авто")
        ttk.Combobox(
            codec_tab,
            textvariable=self.hw_var,
            values=HW_ENCODER_OPTIONS,
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Button(codec_tab, text="Оновити список", command=self.refresh_encoders)\
            .grid(row=1, column=2, padx=4, pady=(8, 0))

        self.encoder_info_var = tk.StringVar(value="Доступні: --")
        ttk.Label(codec_tab, textvariable=self.encoder_info_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Label(presets_tab, text="Збережені пресети:").grid(row=0, column=0, sticky="w")
        self.preset_select_var = tk.StringVar(value="")
        self.preset_combo = ttk.Combobox(
            presets_tab,
            textvariable=self.preset_select_var,
            values=[],
            state="readonly",
            width=26,
        )
        self.preset_combo.grid(row=0, column=1, sticky="w", padx=(8, 18))
        ttk.Button(presets_tab, text="Завантажити", command=self.load_preset).grid(row=0, column=2, padx=4)
        ttk.Button(presets_tab, text="Видалити", command=self.delete_preset).grid(row=0, column=3, padx=4)

        ttk.Label(presets_tab, text="Назва для збереження:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.preset_name_var = tk.StringVar(value="")
        ttk.Entry(presets_tab, textvariable=self.preset_name_var, width=26).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Button(presets_tab, text="Зберегти", command=self.save_preset).grid(row=1, column=2, padx=4, pady=(8, 0))

        self.strip_metadata_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            metadata_tab,
            text="Очистити метадані (-map_metadata -1)",
            variable=self.strip_metadata_var,
        ).grid(row=0, column=0, sticky="w")
        self.copy_metadata_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            metadata_tab,
            text="Копіювати метадані з джерела",
            variable=self.copy_metadata_var,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ttk.Label(metadata_tab, text="Title:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.meta_title_var = tk.StringVar(value="")
        ttk.Entry(metadata_tab, textvariable=self.meta_title_var, width=36).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Label(metadata_tab, text="Comment:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.meta_comment_var = tk.StringVar(value="")
        ttk.Entry(metadata_tab, textvariable=self.meta_comment_var, width=36).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        ttk.Label(metadata_tab, text="Artist/Author:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.meta_author_var = tk.StringVar(value="")
        ttk.Entry(metadata_tab, textvariable=self.meta_author_var, width=36).grid(row=4, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        mid = ttk.Frame(self, padding=(12, 0, 12, 12))
        mid.pack(fill="both", expand=True)

        left = ttk.LabelFrame(mid, text="Черга файлів", padding=8)
        left.pack(side="left", fill="both", expand=True)

        self.listbox = tk.Listbox(left, height=14, selectmode=tk.EXTENDED)
        self.listbox.pack(fill="both", expand=True, padx=4, pady=4)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Очистити", command=self.clear_list).pack(side="left")
        ttk.Button(btns, text="Видалити вибране", command=self.remove_selected).pack(side="left", padx=8)
        ttk.Button(btns, text="Додати ще файли", command=self.pick_files).pack(side="left")

        right = ttk.LabelFrame(mid, text="Статус", padding=10)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(right, textvariable=self.status_var, wraplength=380).pack(anchor="w")

        ttk.Label(right, text="Поточний файл:").pack(anchor="w", pady=(8, 0))
        self.file_progress = ttk.Progressbar(right, mode="determinate")
        self.file_progress.pack(fill="x", pady=(4, 2))
        self.file_progress_var = tk.StringVar(value="0%")
        ttk.Label(right, textvariable=self.file_progress_var).pack(anchor="w")
        self.file_eta_var = tk.StringVar(value="ETA: --:--")
        ttk.Label(right, textvariable=self.file_eta_var).pack(anchor="w")

        ttk.Label(right, text="Загальний прогрес:").pack(anchor="w", pady=(8, 0))
        self.total_progress = ttk.Progressbar(right, mode="determinate")
        self.total_progress.pack(fill="x", pady=(4, 2))
        self.total_progress_var = tk.StringVar(value="0 / 0")
        ttk.Label(right, textvariable=self.total_progress_var).pack(anchor="w")
        self.total_eta_var = tk.StringVar(value="Загальний ETA: --:--")
        self.total_elapsed_var = tk.StringVar(value="Минуло: 00:00")
        ttk.Label(right, textvariable=self.total_eta_var).pack(anchor="w")
        ttk.Label(right, textvariable=self.total_elapsed_var).pack(anchor="w")

        controls = ttk.Frame(right)
        controls.pack(fill="x", pady=(12, 0))
        self.btn_start = ttk.Button(controls, text="▶ Старт", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(controls, text="■ Стоп", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=8)

        log_frame = ttk.LabelFrame(self, text="Лог", padding=10)
        log_frame.pack(fill="both", expand=False, padx=12, pady=(0, 12))

        self.log_text = tk.Text(log_frame, height=9, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("INFO", foreground="#1f6feb")
        self.log_text.tag_configure("OK", foreground="#2da44e")
        self.log_text.tag_configure("WARN", foreground="#bf8700")
        self.log_text.tag_configure("ERROR", foreground="#cf222e")

    def _log(self, level: str, msg: str):
        self.log_text.insert("end", f"[{level}] {msg}\n", level)
        self.log_text.see("end")

    def _queue_log(self, level: str, msg: str):
        self.ui_queue.put((level, msg))

    def _poll_queue(self):
        try:
            while True:
                level, msg = self.ui_queue.get_nowait()
                self._log(level, msg)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def refresh_listbox(self):
        self.listbox.delete(0, "end")
        for i, (p, t) in enumerate(self.tasks, start=1):
            tag = "🎬" if t == "video" else "🖼"
            self.listbox.insert("end", f"{i}. {tag} {p.name}")

    def pick_ffmpeg(self):
        path = filedialog.askopenfilename(
            title="Вибери ffmpeg.exe",
            filetypes=[("ffmpeg", "ffmpeg.exe"), ("All files", "*.*")]
        )
        if not path:
            return
        self.ffmpeg_path = path
        self.ffmpeg_var.set(path)
        self._log("OK", f"FFmpeg задано вручну: {path}")
        self._refresh_ffmpeg_tools(log_initial=True)

    def check_ffmpeg(self):
        p = self.ffmpeg_var.get().strip()
        if p:
            self.ffmpeg_path = p
        if not self.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg не задано. Натисни 'Вказати ffmpeg.exe'.")
            return
        try:
            r = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True)
            if r.returncode == 0:
                first_line = (r.stdout.splitlines() or [""])[0]
                self._log("OK", f"FFmpeg працює: {first_line}")
                self._refresh_ffmpeg_tools(log_initial=True)
            else:
                self._log("ERROR", "FFmpeg не запускається. Перевір шлях до ffmpeg.exe")
        except Exception as e:
            self._log("ERROR", f"Помилка перевірки FFmpeg: {e}")

    def refresh_encoders(self):
        self._refresh_ffmpeg_tools(log_initial=True)

    def pick_folder(self):
        folder = filedialog.askdirectory(title="Вибери папку з медіа (фото/відео)")
        if not folder:
            return
        self.src_var.set(folder)
        self.load_media_from_folder(Path(folder))

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Вибери файли (фото/відео)",
            filetypes=[
                ("Media", "*.mov *.mp4 *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts "
                          "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.heic *.heif"),
                ("All files", "*.*")
            ],
        )
        if not paths:
            return
        self.add_files([Path(p) for p in paths])

    def pick_output(self):
        folder = filedialog.askdirectory(title="Вибери папку виводу")
        if folder:
            self.out_var.set(folder)

    def open_output_folder(self):
        out = Path(self.out_var.get()).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(out))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(out)], check=False)
        else:
            subprocess.run(["xdg-open", str(out)], check=False)

    def pick_watermark(self):
        path = filedialog.askopenfilename(
            title="Вибери зображення водяного знаку",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"), ("All files", "*.*")]
        )
        if path:
            self.wm_path_var.set(path)

    def pick_font(self):
        path = filedialog.askopenfilename(
            title="Вибери шрифт (.ttf/.otf)",
            filetypes=[("Fonts", "*.ttf *.otf"), ("All files", "*.*")]
        )
        if path:
            self.text_font_var.set(path)

    def load_media_from_folder(self, folder: Path):
        if not folder.exists():
            messagebox.showerror("Помилка", "Папка не існує.")
            return
        files = [p for p in folder.rglob("*") if p.is_file()]
        self.add_files(files)

    def add_files(self, files: List[Path]):
        added = 0
        skipped = 0
        existing = {p.resolve() for p, _ in self.tasks}

        for f in files:
            if not f.exists() or not f.is_file():
                continue
            t = media_type(f)
            if t is None:
                skipped += 1
                continue
            r = f.resolve()
            if r in existing:
                continue
            self.tasks.append((f, t))
            existing.add(r)
            added += 1

        self.refresh_listbox()
        if added:
            self._queue_log("INFO", f"Додано: {added}. Всього: {len(self.tasks)}")
        if skipped:
            self._queue_log("WARN", f"Пропущено (непідтримувані розширення): {skipped}")
        self._reset_progress(len(self.tasks), 0.0)

    def clear_list(self):
        self.tasks.clear()
        self.media_info.clear()
        self.refresh_listbox()
        self._reset_progress(0, 0.0)

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        for idx in reversed(sel):
            path, _ = self.tasks[idx]
            if path in self.media_info:
                del self.media_info[path]
            del self.tasks[idx]
        self.refresh_listbox()
        self._reset_progress(len(self.tasks), 0.0)

    def _reset_progress(self, total_files: int, total_duration: float):
        self.file_progress["maximum"] = 100
        self.file_progress["value"] = 0
        self.file_progress_var.set("0%")
        self.file_eta_var.set("ETA: --:--")

        self.total_progress["maximum"] = max(total_duration if total_duration > 0 else total_files, 1)
        self.total_progress["value"] = 0
        if total_duration > 0:
            self.total_progress_var.set(f"{format_time(0)} / {format_time(total_duration)}")
        else:
            self.total_progress_var.set(f"0 / {total_files}")
        self.total_eta_var.set("Загальний ETA: --:--")
        self.total_elapsed_var.set("Минуло: 00:00")

    def _update_total_progress(self, done_files: int, total_files: int, done_duration: float, total_duration: float):
        if total_duration > 0:
            self.total_progress["maximum"] = max(total_duration, 1)
            self.total_progress["value"] = min(done_duration, total_duration)
            self.total_progress_var.set(f"{format_time(done_duration)} / {format_time(total_duration)}")
        else:
            self.total_progress["maximum"] = max(total_files, 1)
            self.total_progress["value"] = min(done_files, total_files)
            self.total_progress_var.set(f"{done_files} / {total_files}")

        if self.total_start_time:
            elapsed = time.time() - self.total_start_time
            self.total_elapsed_var.set(f"Минуло: {format_time(elapsed)}")
            if total_duration > 0 and done_duration > 0:
                speed = done_duration / elapsed if elapsed > 0 else 0
                if speed > 0:
                    eta = (total_duration - done_duration) / speed
                    self.total_eta_var.set(f"Загальний ETA: {format_time(eta)}")

    def _update_file_progress(self, out_time: float, duration: float, speed: Optional[float]):
        if duration and duration > 0:
            percent = min((out_time / duration) * 100.0, 100.0)
            self.file_progress["maximum"] = 100
            self.file_progress["value"] = percent
            self.file_progress_var.set(f"{percent:.1f}% ({format_time(out_time)} / {format_time(duration)})")
            eta = None
            if speed and speed > 0:
                eta = (duration - out_time) / speed
            elif self.current_file_start and out_time > 0:
                elapsed = time.time() - self.current_file_start
                if elapsed > 0:
                    speed_calc = out_time / elapsed
                    if speed_calc > 0:
                        eta = (duration - out_time) / speed_calc
            self.file_eta_var.set(f"ETA: {format_time(eta)}" if eta is not None else "ETA: --:--")
        else:
            self.file_progress["maximum"] = 100
            self.file_progress["value"] = 0
            self.file_progress_var.set("0%")
            self.file_eta_var.set("ETA: --:--")

    def _mark_file_complete(self, duration: Optional[float]):
        self.file_progress["maximum"] = 100
        self.file_progress["value"] = 100
        if duration and duration > 0:
            self.file_progress_var.set(f"100% ({format_time(duration)} / {format_time(duration)})")
        else:
            self.file_progress_var.set("100%")
        self.file_eta_var.set("ETA: 00:00")

    def _refresh_ffmpeg_tools(self, log_initial: bool = False):
        if not self.ffmpeg_path:
            self.encoder_caps = set()
            self.ffprobe_path = None
            self.encoder_info_var.set("Доступні: --")
            return
        self.ffprobe_path = find_ffprobe(self.ffmpeg_path)
        self.encoder_caps = self._detect_encoders()
        summary = []
        if {"h264_nvenc", "hevc_nvenc", "av1_nvenc"} & self.encoder_caps:
            summary.append("NVENC")
        if {"h264_qsv", "hevc_qsv", "av1_qsv"} & self.encoder_caps:
            summary.append("QSV")
        if {"h264_amf", "hevc_amf", "av1_amf"} & self.encoder_caps:
            summary.append("AMF")
        if "libx265" in self.encoder_caps:
            summary.append("x265")
        if {"libsvtav1", "libaom-av1"} & self.encoder_caps:
            summary.append("AV1")
        if "libvpx-vp9" in self.encoder_caps:
            summary.append("VP9")
        self.encoder_info_var.set(f"Доступні: {', '.join(summary) if summary else 'немає'}")
        if log_initial:
            if self.ffprobe_path:
                self._log("OK", f"FFprobe знайдено: {self.ffprobe_path}")
            else:
                self._log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")

    def _detect_encoders(self) -> set[str]:
        try:
            r = subprocess.run([self.ffmpeg_path, "-hide_banner", "-encoders"], capture_output=True, text=True)
        except Exception:
            return set()
        if r.returncode != 0:
            return set()
        encoders = set()
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("Encoders:") or line.startswith("--"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                encoders.add(parts[1])
        return encoders

    def _probe_media(self, path: Path) -> Optional[MediaInfo]:
        if not self.ffprobe_path:
            return None
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration,size,format_name:stream=codec_type,codec_name,width,height",
            "-of", "json",
            str(path),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            self._queue_log("WARN", f"FFprobe помилка для {path.name}: {e}")
            return None
        if r.returncode != 0:
            self._queue_log("WARN", f"FFprobe помилка для {path.name}")
            return None
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            return None

        info = MediaInfo()
        fmt = data.get("format", {})
        dur = fmt.get("duration")
        if dur is not None:
            try:
                info.duration = float(dur)
            except ValueError:
                pass
        info.format_name = fmt.get("format_name")
        size = fmt.get("size")
        if size is not None:
            try:
                info.size_bytes = int(size)
            except ValueError:
                pass

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and info.vcodec is None:
                info.vcodec = stream.get("codec_name")
                info.width = stream.get("width")
                info.height = stream.get("height")
            if stream.get("codec_type") == "audio" and info.acodec is None:
                info.acodec = stream.get("codec_name")

        if info.size_bytes is None:
            try:
                info.size_bytes = path.stat().st_size
            except Exception:
                pass
        return info

    def _log_media_info(self, path: Path, info: MediaInfo):
        parts = []
        if info.duration is not None:
            parts.append(format_time(info.duration))
        if info.vcodec or info.acodec:
            parts.append(f"{info.vcodec or '-'} / {info.acodec or '-'}")
        if info.width and info.height:
            parts.append(f"{info.width}x{info.height}")
        if info.size_bytes is not None:
            parts.append(format_bytes(info.size_bytes))
        if info.format_name:
            parts.append(info.format_name)
        if parts:
            self._queue_log("INFO", f"ffprobe: {path.name} | " + " | ".join(parts))

    def _validate_inputs(self):
        if self.trim_start_var.get().strip() and parse_time_to_seconds(self.trim_start_var.get()) is None:
            self._queue_log("WARN", "Некоректний формат trim start.")
        if self.trim_end_var.get().strip() and parse_time_to_seconds(self.trim_end_var.get()) is None:
            self._queue_log("WARN", "Некоректний формат trim end.")
        if self.speed_var.get().strip():
            speed = parse_float(self.speed_var.get())
            if speed is None or speed <= 0:
                self._queue_log("WARN", "Некоректна швидкість. Використовується 1.0.")
        if self.resize_w_var.get().strip() and parse_int(self.resize_w_var.get()) is None:
            self._queue_log("WARN", "Некоректний resize W.")
        if self.resize_h_var.get().strip() and parse_int(self.resize_h_var.get()) is None:
            self._queue_log("WARN", "Некоректний resize H.")
        if self.crop_w_var.get().strip() and parse_int(self.crop_w_var.get()) is None:
            self._queue_log("WARN", "Некоректний crop W.")
        if self.crop_h_var.get().strip() and parse_int(self.crop_h_var.get()) is None:
            self._queue_log("WARN", "Некоректний crop H.")
        if self.wm_path_var.get().strip():
            if not Path(self.wm_path_var.get().strip()).expanduser().exists():
                self._queue_log("WARN", "Файл водяного знаку не знайдено.")
        if self.text_font_var.get().strip():
            if not Path(self.text_font_var.get().strip()).expanduser().exists():
                self._queue_log("WARN", "Файл шрифту не знайдено.")

    def _trim_args(self) -> List[str]:
        start = parse_time_to_seconds(self.trim_start_var.get())
        end = parse_time_to_seconds(self.trim_end_var.get())
        args = []
        if start is not None:
            args += ["-ss", f"{start:.3f}"]
        if end is not None:
            if start is not None and end <= start:
                self._queue_log("WARN", "Trim end <= start. Ігнорую end.")
            else:
                args += ["-to", f"{end:.3f}"]
        return args

    def _get_resize_filter(self) -> Optional[str]:
        w = parse_int(self.resize_w_var.get())
        h = parse_int(self.resize_h_var.get())
        if w is None and h is None:
            return None
        if w is None:
            w = -1
        if h is None:
            h = -1
        return f"scale={w}:{h}"

    def _get_crop_filter(self) -> Optional[str]:
        w = parse_int(self.crop_w_var.get())
        h = parse_int(self.crop_h_var.get())
        if w is None or h is None:
            return None
        x = parse_int(self.crop_x_var.get()) or 0
        y = parse_int(self.crop_y_var.get()) or 0
        return f"crop={w}:{h}:{x}:{y}"

    def _get_speed_value(self) -> Optional[float]:
        speed = parse_float(self.speed_var.get())
        if speed is None or speed <= 0:
            return None
        return speed

    def _build_audio_speed_filter(self) -> Optional[str]:
        speed = self._get_speed_value()
        if speed is None or abs(speed - 1.0) < 0.001:
            return None
        chain = build_atempo_chain(speed)
        if not chain:
            return None
        return ",".join([f"atempo={f:.3f}" for f in chain])

    def _build_text_filter(self) -> Optional[str]:
        text = self.text_wm_var.get().strip()
        if not text:
            return None
        size = int(self.text_size_var.get())
        color = self.text_color_var.get().strip() or "white"
        fontfile = self.text_font_var.get().strip()
        pos = self.text_pos_var.get()
        pos_map = {
            "Верх-ліворуч": "10:10",
            "Верх-праворуч": "W-tw-10:10",
            "Низ-ліворуч": "10:H-th-10",
            "Низ-праворуч": "W-tw-10:H-th-10",
            "Центр": "(W-tw)/2:(H-th)/2",
        }
        x_y = pos_map.get(pos, "10:10")
        x, y = x_y.split(":", 1)
        draw = f"drawtext=text='{escape_drawtext(text)}':x={x}:y={y}:fontsize={size}:fontcolor={color}"
        if fontfile:
            draw += f":fontfile='{escape_filter_path(fontfile)}'"
        return draw

    def _build_video_filter_spec(self, out_ext: str) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
        filters = []

        resize_filter = self._get_resize_filter()
        if resize_filter:
            filters.append(resize_filter)

        crop_filter = self._get_crop_filter()
        if crop_filter:
            filters.append(crop_filter)

        rotate_filter = ROTATE_MAP.get(self.rotate_var.get())
        if rotate_filter:
            filters.append(rotate_filter)

        speed = self._get_speed_value()
        if speed and abs(speed - 1.0) > 0.001:
            filters.append(f"setpts=PTS/{speed}")

        text_filter = self._build_text_filter()
        if text_filter:
            filters.append(text_filter)

        portrait = PORTRAIT_PRESETS.get(self.portrait_var.get())
        use_blur = False
        blur_graph = ""
        if portrait:
            mode, w, h = portrait
            if mode == "crop":
                filters.insert(0, f"scale='if(gt(a,9/16),-2,{w})':'if(gt(a,9/16),{h},-2)',crop={w}:{h},setsar=1")
            else:
                use_blur = True
                blur_graph = (
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,boxblur=20:1,crop={w}:{h}[bg];"
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
                )

        if out_ext == ".gif":
            filters.append("fps=12")
            if resize_filter is None:
                filters.append("scale=640:-1:flags=lanczos")

        watermark_inputs = []
        watermark_path = self.wm_path_var.get().strip()
        if watermark_path:
            wm_path = Path(watermark_path).expanduser()
            if wm_path.exists():
                watermark_inputs.append(str(wm_path))
            else:
                self._queue_log("WARN", f"Водяний знак не знайдено: {watermark_path}")

        if not use_blur and not watermark_inputs:
            if filters:
                return "-vf", ",".join(filters), None, []
            return None, None, None, []

        base_label = "vbase"
        graph_parts = []
        if use_blur:
            graph = blur_graph
            if filters:
                graph += f",{','.join(filters)}"
            graph += f"[{base_label}]"
            graph_parts.append(graph)
        else:
            chain = ",".join(filters) if filters else "null"
            graph_parts.append(f"[0:v]{chain}[{base_label}]")

        out_label = base_label
        if watermark_inputs:
            wm_chain = "[1:v]format=rgba"
            wm_scale = max(1, int(self.wm_scale_var.get())) / 100.0
            wm_opacity = max(0, min(100, int(self.wm_opacity_var.get()))) / 100.0
            wm_chain += f",scale=iw*{wm_scale}:ih*{wm_scale}"
            wm_chain += f",colorchannelmixer=aa={wm_opacity}"
            wm_chain += "[wm]"
            graph_parts.append(wm_chain)
            pos_expr = POSITION_MAP.get(self.wm_pos_var.get(), "10:10")
            graph_parts.append(f"[{base_label}][wm]overlay={pos_expr}[vout]")
            out_label = "vout"

        return "-filter_complex", ";".join(graph_parts), f"[{out_label}]", watermark_inputs

    def _build_image_filter_spec(self) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
        filters = []

        resize_filter = self._get_resize_filter()
        if resize_filter:
            filters.append(resize_filter)

        crop_filter = self._get_crop_filter()
        if crop_filter:
            filters.append(crop_filter)

        rotate_filter = ROTATE_MAP.get(self.rotate_var.get())
        if rotate_filter:
            filters.append(rotate_filter)

        text_filter = self._build_text_filter()
        if text_filter:
            filters.append(text_filter)

        watermark_inputs = []
        watermark_path = self.wm_path_var.get().strip()
        if watermark_path:
            wm_path = Path(watermark_path).expanduser()
            if wm_path.exists():
                watermark_inputs.append(str(wm_path))
            else:
                self._queue_log("WARN", f"Водяний знак не знайдено: {watermark_path}")

        if not watermark_inputs:
            if filters:
                return "-vf", ",".join(filters), None, []
            return None, None, None, []

        base_label = "vbase"
        graph_parts = []
        chain = ",".join(filters) if filters else "null"
        graph_parts.append(f"[0:v]{chain}[{base_label}]")

        wm_chain = "[1:v]format=rgba"
        wm_scale = max(1, int(self.wm_scale_var.get())) / 100.0
        wm_opacity = max(0, min(100, int(self.wm_opacity_var.get()))) / 100.0
        wm_chain += f",scale=iw*{wm_scale}:ih*{wm_scale}"
        wm_chain += f",colorchannelmixer=aa={wm_opacity}"
        wm_chain += "[wm]"
        graph_parts.append(wm_chain)
        pos_expr = POSITION_MAP.get(self.wm_pos_var.get(), "10:10")
        graph_parts.append(f"[{base_label}][wm]overlay={pos_expr}[vout]")

        return "-filter_complex", ";".join(graph_parts), "[vout]", watermark_inputs

    def _metadata_args(self) -> List[str]:
        args = []
        if self.strip_metadata_var.get():
            args += ["-map_metadata", "-1"]
        elif self.copy_metadata_var.get():
            args += ["-map_metadata", "0"]
        title = self.meta_title_var.get().strip()
        if title:
            args += ["-metadata", f"title={title}"]
        comment = self.meta_comment_var.get().strip()
        if comment:
            args += ["-metadata", f"comment={comment}"]
        author = self.meta_author_var.get().strip()
        if author:
            args += ["-metadata", f"artist={author}"]
        return args

    def _fast_copy_allowed(self, inp: Path, outp: Path, filters_used: bool, audio_filter_used: bool) -> Tuple[bool, str]:
        if outp.suffix.lower() == ".gif":
            return False, "GIF потребує перекодування"
        if filters_used or audio_filter_used:
            return False, "є фільтри/зміна швидкості"
        if inp.suffix.lower() != outp.suffix.lower():
            return False, "контейнер відрізняється"
        return True, ""

    def _merge_copy_allowed(
        self,
        inputs: List[Path],
        outp: Path,
        filters_used: bool,
        audio_filter_used: bool,
        trim_args: List[str],
    ) -> Tuple[bool, str]:
        if filters_used or audio_filter_used or trim_args:
            return False, "є фільтри/trim"
        if outp.suffix.lower() != inputs[0].suffix.lower():
            return False, "контейнер відрізняється"
        vcodecs = set()
        acodecs = set()
        for path in inputs:
            info = self.media_info.get(path)
            if not info or not info.vcodec:
                return False, "немає даних ffprobe"
            vcodecs.add(info.vcodec)
            if info.acodec:
                acodecs.add(info.acodec)
        if len(vcodecs) > 1 or len(acodecs) > 1:
            return False, "різні кодеки"
        return True, ""

    def _resolve_codec(self, out_ext: str) -> str:
        choice = VIDEO_CODEC_MAP.get(self.codec_var.get(), "auto")
        if out_ext == ".gif":
            return "gif"
        if choice == "auto":
            if out_ext == ".webm":
                return "vp9"
            return "h264"
        if out_ext == ".webm" and choice not in {"vp9", "av1"}:
            self._queue_log("WARN", "WebM підтримує VP9/AV1. Перемикаю на VP9.")
            return "vp9"
        if out_ext in {".mp4", ".mov", ".m4v", ".avi"} and choice == "vp9":
            self._queue_log("WARN", "VP9 не сумісний з MP4/MOV/AVI. Перемикаю на H.264.")
            return "h264"
        return choice

    def _select_encoder(self, codec: str, hw_pref: str) -> Tuple[Optional[str], bool]:
        cpu_map = {
            "h264": "libx264",
            "h265": "libx265",
            "av1": "libsvtav1" if "libsvtav1" in self.encoder_caps else "libaom-av1",
            "vp9": "libvpx-vp9",
        }
        hw_map = {
            "nvidia": {"h264": "h264_nvenc", "h265": "hevc_nvenc", "av1": "av1_nvenc"},
            "intel": {"h264": "h264_qsv", "h265": "hevc_qsv", "av1": "av1_qsv"},
            "amd": {"h264": "h264_amf", "h265": "hevc_amf", "av1": "av1_amf"},
        }
        if codec not in cpu_map:
            return None, False

        if hw_pref == "cpu":
            return cpu_map[codec], False

        if hw_pref == "auto":
            for vendor in ["nvidia", "intel", "amd"]:
                enc = hw_map.get(vendor, {}).get(codec)
                if enc and enc in self.encoder_caps:
                    return enc, True
            return cpu_map[codec], False

        enc = hw_map.get(hw_pref, {}).get(codec)
        if enc and enc in self.encoder_caps:
            return enc, True

        self._queue_log("WARN", "Обраний GPU-енкодер недоступний. Використовую CPU.")
        return cpu_map[codec], False

    def _encoder_quality_args(self, encoder: str, crf: int) -> List[str]:
        if encoder in {"libx264", "libx265", "libsvtav1", "libaom-av1"}:
            return ["-crf", str(crf)]
        if encoder == "libvpx-vp9":
            return ["-crf", str(crf), "-b:v", "0"]
        if encoder.endswith("_nvenc"):
            return ["-rc:v", "vbr", "-cq", str(crf), "-b:v", "0"]
        if encoder.endswith("_qsv"):
            return ["-global_quality", str(crf)]
        if encoder.endswith("_amf"):
            return ["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-qp_b", str(crf)]
        return []

    def _build_cmd_video(self, inp: Path, outp: Path, info: Optional[MediaInfo]) -> List[str]:
        overwrite = "-y" if self.overwrite_var.get() else "-n"
        out_ext = outp.suffix.lower()

        trim_args = self._trim_args()
        filter_arg, filter_val, map_label, extra_inputs = self._build_video_filter_spec(out_ext)
        audio_filter = self._build_audio_speed_filter()
        filters_used = filter_arg is not None

        fast_copy_requested = self.fast_copy_var.get()
        fast_copy_ok, reason = self._fast_copy_allowed(inp, outp, filters_used, audio_filter is not None)
        if fast_copy_requested and not fast_copy_ok:
            self._queue_log("WARN", f"Fast copy вимкнено для {inp.name}: {reason}")

        if fast_copy_requested and fast_copy_ok:
            cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
            cmd += trim_args
            cmd += ["-map", "0", "-c", "copy"]
            cmd += self._metadata_args()
            if out_ext in {".mp4", ".mov", ".m4v"}:
                cmd += ["-movflags", "+faststart"]
            cmd.append(str(outp))
            return cmd

        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        cmd += trim_args

        if filter_arg:
            cmd += [filter_arg, filter_val]
            cmd += ["-map", map_label]
        else:
            cmd += ["-map", "0:v:0?"]

        if out_ext != ".gif":
            cmd += ["-map", "0:a:0?"]
            if audio_filter:
                cmd += ["-filter:a", audio_filter]
        else:
            cmd += ["-an"]

        if out_ext == ".gif":
            cmd += self._metadata_args()
            cmd.append(str(outp))
            return cmd

        codec = self._resolve_codec(out_ext)
        encoder, is_hw = self._select_encoder(codec, HW_ENCODER_MAP.get(self.hw_var.get(), "auto"))
        if not encoder:
            encoder = "libx264"
        cmd += ["-c:v", encoder]
        if not is_hw and encoder in {"libx264", "libx265"}:
            preset = (self.preset_var.get() or "medium").strip()
            cmd += ["-preset", preset]
        elif is_hw:
            self._queue_log("INFO", "GPU-кодування: preset CPU ігнорується.")
        cmd += self._encoder_quality_args(encoder, int(self.crf_var.get()))
        if encoder in {
            "libx264", "libx265",
            "h264_nvenc", "hevc_nvenc",
            "h264_qsv", "hevc_qsv",
            "h264_amf", "hevc_amf",
        }:
            cmd += ["-pix_fmt", "yuv420p"]

        if out_ext == ".webm":
            cmd += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]

        cmd += self._metadata_args()
        cmd.append(str(outp))
        return cmd

    def _build_cmd_image(self, inp: Path, outp: Path) -> List[str]:
        overwrite = "-y" if self.overwrite_var.get() else "-n"
        ext = outp.suffix.lower()

        filter_arg, filter_val, map_label, extra_inputs = self._build_image_filter_spec()
        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        if filter_arg:
            cmd += [filter_arg, filter_val]
            cmd += ["-map", map_label]

        cmd += self._metadata_args()

        q = int(self.img_quality_var.get())
        if ext in {".jpg", ".jpeg"}:
            qv = max(2, min(31, int(round(31 - (q / 100) * 29))))
            cmd += ["-q:v", str(qv)]
        elif ext == ".webp":
            cmd += ["-q:v", str(max(0, min(100, q)))]

        cmd.append(str(outp))
        return cmd

    def _write_concat_list(self, inputs: List[Path]) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
        with tmp as fh:
            for p in inputs:
                safe = str(p.resolve()).replace("'", "'\\''")
                fh.write(f"file '{safe}'\n")
        return tmp.name

    def _build_cmd_merge(self, inputs: List[Path], outp: Path) -> Tuple[List[str], str]:
        overwrite = "-y" if self.overwrite_var.get() else "-n"
        list_path = self._write_concat_list(inputs)
        out_ext = outp.suffix.lower()

        trim_args = self._trim_args()
        filter_arg, filter_val, map_label, extra_inputs = self._build_video_filter_spec(out_ext)
        audio_filter = self._build_audio_speed_filter()
        filters_used = filter_arg is not None

        fast_copy_requested = self.fast_copy_var.get()
        fast_copy_ok, reason = self._merge_copy_allowed(inputs, outp, filters_used, audio_filter is not None, trim_args)
        if fast_copy_requested and not fast_copy_ok:
            self._queue_log("WARN", f"Fast copy (merge) вимкнено: {reason}")

        cmd = [self.ffmpeg_path, overwrite, "-f", "concat", "-safe", "0", "-i", list_path]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        cmd += trim_args

        if fast_copy_requested and fast_copy_ok:
            cmd += ["-map", "0", "-c", "copy"]
            cmd += self._metadata_args()
            if out_ext in {".mp4", ".mov", ".m4v"}:
                cmd += ["-movflags", "+faststart"]
            cmd.append(str(outp))
            return cmd, list_path

        if filter_arg:
            cmd += [filter_arg, filter_val]
            cmd += ["-map", map_label]
        else:
            cmd += ["-map", "0:v:0?"]

        if out_ext != ".gif":
            cmd += ["-map", "0:a:0?"]
            if audio_filter:
                cmd += ["-filter:a", audio_filter]
        else:
            cmd += ["-an"]

        if out_ext == ".gif":
            cmd += self._metadata_args()
            cmd.append(str(outp))
            return cmd, list_path

        codec = self._resolve_codec(out_ext)
        encoder, is_hw = self._select_encoder(codec, HW_ENCODER_MAP.get(self.hw_var.get(), "auto"))
        if not encoder:
            encoder = "libx264"
        cmd += ["-c:v", encoder]
        if not is_hw and encoder in {"libx264", "libx265"}:
            preset = (self.preset_var.get() or "medium").strip()
            cmd += ["-preset", preset]
        cmd += self._encoder_quality_args(encoder, int(self.crf_var.get()))
        if encoder in {
            "libx264", "libx265",
            "h264_nvenc", "hevc_nvenc",
            "h264_qsv", "hevc_qsv",
            "h264_amf", "hevc_amf",
        }:
            cmd += ["-pix_fmt", "yuv420p"]

        if out_ext == ".webm":
            cmd += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]

        cmd += self._metadata_args()
        cmd.append(str(outp))
        return cmd, list_path

    def _load_presets(self) -> Dict[str, Dict[str, Any]]:
        if not self.presets_path.exists():
            return {}
        try:
            with self.presets_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
        return {}

    def _save_presets(self):
        try:
            with self.presets_path.open("w", encoding="utf-8") as fh:
                json.dump(self.presets, fh, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log("ERROR", f"Не вдалося зберегти пресети: {e}")

    def _refresh_preset_list(self):
        names = sorted(self.presets.keys())
        self.preset_combo.configure(values=names)
        if names and self.preset_select_var.get() not in names:
            self.preset_select_var.set(names[0])

    def _collect_preset_data(self) -> Dict[str, Any]:
        return {
            "out_video_fmt": self.out_video_fmt_var.get(),
            "out_image_fmt": self.out_image_fmt_var.get(),
            "crf": int(self.crf_var.get()),
            "preset": self.preset_var.get(),
            "portrait": self.portrait_var.get(),
            "img_quality": int(self.img_quality_var.get()),
            "overwrite": bool(self.overwrite_var.get()),
            "fast_copy": bool(self.fast_copy_var.get()),
            "trim_start": self.trim_start_var.get(),
            "trim_end": self.trim_end_var.get(),
            "merge": bool(self.merge_var.get()),
            "merge_name": self.merge_name_var.get(),
            "resize_w": self.resize_w_var.get(),
            "resize_h": self.resize_h_var.get(),
            "crop_w": self.crop_w_var.get(),
            "crop_h": self.crop_h_var.get(),
            "crop_x": self.crop_x_var.get(),
            "crop_y": self.crop_y_var.get(),
            "rotate": self.rotate_var.get(),
            "speed": self.speed_var.get(),
            "wm_path": self.wm_path_var.get(),
            "wm_pos": self.wm_pos_var.get(),
            "wm_opacity": int(self.wm_opacity_var.get()),
            "wm_scale": int(self.wm_scale_var.get()),
            "text_wm": self.text_wm_var.get(),
            "text_pos": self.text_pos_var.get(),
            "text_size": int(self.text_size_var.get()),
            "text_color": self.text_color_var.get(),
            "text_font": self.text_font_var.get(),
            "codec": self.codec_var.get(),
            "hw": self.hw_var.get(),
            "strip_metadata": bool(self.strip_metadata_var.get()),
            "copy_metadata": bool(self.copy_metadata_var.get()),
            "meta_title": self.meta_title_var.get(),
            "meta_comment": self.meta_comment_var.get(),
            "meta_author": self.meta_author_var.get(),
        }

    def _apply_preset_data(self, data: Dict[str, Any]):
        self.out_video_fmt_var.set(data.get("out_video_fmt", "mp4"))
        self.out_image_fmt_var.set(data.get("out_image_fmt", "jpg"))
        self.crf_var.set(data.get("crf", 23))
        self.preset_var.set(data.get("preset", "medium"))
        self.portrait_var.set(data.get("portrait", "Вимкнено"))
        self.img_quality_var.set(data.get("img_quality", 90))
        self.overwrite_var.set(data.get("overwrite", False))
        self.fast_copy_var.set(data.get("fast_copy", False))
        self.trim_start_var.set(data.get("trim_start", ""))
        self.trim_end_var.set(data.get("trim_end", ""))
        self.merge_var.set(data.get("merge", False))
        self.merge_name_var.set(data.get("merge_name", "merged"))
        self.resize_w_var.set(data.get("resize_w", ""))
        self.resize_h_var.set(data.get("resize_h", ""))
        self.crop_w_var.set(data.get("crop_w", ""))
        self.crop_h_var.set(data.get("crop_h", ""))
        self.crop_x_var.set(data.get("crop_x", ""))
        self.crop_y_var.set(data.get("crop_y", ""))
        self.rotate_var.set(data.get("rotate", "0"))
        self.speed_var.set(data.get("speed", "1.0"))
        self.wm_path_var.set(data.get("wm_path", ""))
        self.wm_pos_var.set(data.get("wm_pos", POSITION_OPTIONS[3]))
        self.wm_opacity_var.set(data.get("wm_opacity", 80))
        self.wm_scale_var.set(data.get("wm_scale", 30))
        self.text_wm_var.set(data.get("text_wm", ""))
        self.text_pos_var.set(data.get("text_pos", POSITION_OPTIONS[3]))
        self.text_size_var.set(data.get("text_size", 24))
        self.text_color_var.set(data.get("text_color", "white"))
        self.text_font_var.set(data.get("text_font", ""))
        self.codec_var.set(data.get("codec", "Авто"))
        self.hw_var.set(data.get("hw", "Авто"))
        self.strip_metadata_var.set(data.get("strip_metadata", False))
        self.copy_metadata_var.set(data.get("copy_metadata", False))
        self.meta_title_var.set(data.get("meta_title", ""))
        self.meta_comment_var.set(data.get("meta_comment", ""))
        self.meta_author_var.set(data.get("meta_author", ""))

    def save_preset(self):
        name = self.preset_name_var.get().strip()
        if not name:
            messagebox.showerror("Пресети", "Введи назву пресету.")
            return
        if name in self.presets:
            if not messagebox.askyesno("Пресети", "Пресет уже існує. Перезаписати?"):
                return
        self.presets[name] = self._collect_preset_data()
        self._save_presets()
        self._refresh_preset_list()
        self.preset_select_var.set(name)
        self._log("OK", f"Пресет збережено: {name}")

    def load_preset(self):
        name = self.preset_select_var.get().strip()
        if not name:
            return
        data = self.presets.get(name)
        if not data:
            return
        self._apply_preset_data(data)
        self._log("OK", f"Пресет завантажено: {name}")

    def delete_preset(self):
        name = self.preset_select_var.get().strip()
        if not name:
            return
        if not messagebox.askyesno("Пресети", f"Видалити пресет '{name}'?"):
            return
        if name in self.presets:
            del self.presets[name]
            self._save_presets()
            self._refresh_preset_list()
            self._log("OK", f"Пресет видалено: {name}")

    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        entry_path = self.ffmpeg_var.get().strip()
        if entry_path:
            self.ffmpeg_path = entry_path
            self._refresh_ffmpeg_tools(log_initial=False)

        if not self.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg не знайдено. Вкажи ffmpeg.exe або додай у PATH.")
            return

        if not self.tasks:
            messagebox.showinfo("Черга пуста", "Додай файли для конвертації.")
            return

        out_dir = Path(self.out_var.get()).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося створити папку виводу:\n{e}")
            return

        self.stop_requested = False
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set("Конвертація запущена...")

        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.stop_requested = True
        self.status_var.set("Зупинка після поточного файлу...")

    def _consume_stderr(self, pipe):
        for line in pipe:
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if "error" in low or "invalid" in low or "failed" in low:
                self._queue_log("WARN", line)

    def _run_ffmpeg(
        self,
        cmd: List[str],
        duration: Optional[float],
        total_done: float,
        total_duration: float,
        done_files: int,
        total_files: int,
    ) -> int:
        if len(cmd) < 2:
            return -1
        cmd_with_progress = cmd[:2] + ["-progress", "pipe:1", "-nostats", "-hide_banner"] + cmd[2:]
        proc = subprocess.Popen(
            cmd_with_progress,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,
        )
        self.current_proc = proc
        self.current_file_start = time.time()

        assert proc.stderr is not None
        err_thread = threading.Thread(target=self._consume_stderr, args=(proc.stderr,), daemon=True)
        err_thread.start()

        out_time = 0.0
        speed = None
        if proc.stdout is not None:
            for line in proc.stdout:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key == "out_time_ms":
                    try:
                        out_time = int(value) / 1_000_000
                    except ValueError:
                        pass
                elif key == "out_time_us":
                    try:
                        out_time = int(value) / 1_000_000
                    except ValueError:
                        pass
                elif key == "out_time":
                    parsed = parse_ffmpeg_time(value)
                    if parsed is not None:
                        out_time = parsed
                elif key == "speed":
                    try:
                        speed = float(value.replace("x", ""))
                    except ValueError:
                        pass

                if duration and duration > 0:
                    self.after(0, self._update_file_progress, out_time, duration, speed)
                    overall_done = total_done + out_time
                else:
                    overall_done = total_done
                self.after(0, self._update_total_progress, done_files, total_files, overall_done, total_duration)

        rc = proc.wait()
        err_thread.join(timeout=0.2)
        self.current_proc = None
        return rc

    def _worker(self):
        out_dir = Path(self.out_var.get()).expanduser()
        total_files = len(self.tasks)
        done_files = 0

        out_vid = (self.out_video_fmt_var.get().strip().lower() or "mp4")
        out_img = (self.out_image_fmt_var.get().strip().lower() or "jpg")

        self._queue_log("INFO", f"Старт. Файлів: {total_files}")
        self._queue_log("INFO", f"Відео → .{out_vid} | Фото → .{out_img}")

        self._validate_inputs()

        self.media_info.clear()
        self.total_duration = 0.0
        if self.ffprobe_path:
            for inp, t in self.tasks:
                info = self._probe_media(inp)
                if info:
                    self.media_info[inp] = info
                    self._log_media_info(inp, info)
                    if t == "video" and info.duration:
                        self.total_duration += info.duration
        else:
            self._queue_log("WARN", "FFprobe не знайдено: прогрес по часу буде приблизним.")

        self.done_duration = 0.0
        self.total_start_time = time.time()
        self._reset_progress(total_files, self.total_duration)

        merge_enabled = self.merge_var.get()
        video_inputs = [p for p, t in self.tasks if t == "video"]
        if merge_enabled and len(video_inputs) < 2:
            self._queue_log("WARN", "Merge увімкнено, але відео менше 2. Пропускаю merge.")
            merge_enabled = False

        if merge_enabled:
            name = self.merge_name_var.get().strip() or "merged"
            outp = Path(name)
            if not outp.suffix:
                outp = out_dir / f"{name}.{out_vid}"
            else:
                outp = out_dir / outp.name
            if not self.overwrite_var.get():
                outp = safe_output_name(out_dir, outp, outp.suffix.lstrip("."))

            duration = sum(self.media_info.get(p, MediaInfo()).duration or 0 for p in video_inputs)
            self.current_duration = duration if duration > 0 else None
            self.after(0, lambda name=outp.name: self.status_var.set(f"Обробка (merge): {name}"))
            self._queue_log("INFO", f"Merge відео: {len(video_inputs)} файлів → {outp.name}")

            list_path = ""
            try:
                cmd, list_path = self._build_cmd_merge(video_inputs, outp)
                rc = self._run_ffmpeg(cmd, self.current_duration, self.done_duration, self.total_duration, done_files, total_files)
                if rc == 0 and outp.exists():
                    self._queue_log("OK", f"Готово (merge): {outp.name}")
                else:
                    self._queue_log("ERROR", f"Помилка merge (код {rc})")
            except FileNotFoundError:
                self._queue_log("ERROR", "FFmpeg не знайдено під час запуску.")
                self.stop_requested = True
            except Exception as e:
                self._queue_log("ERROR", f"Merge помилка: {e}")
            finally:
                if list_path:
                    try:
                        Path(list_path).unlink(missing_ok=True)
                    except Exception:
                        pass

            done_files += len(video_inputs)
            if duration:
                self.done_duration += duration
            self.after(0, self._mark_file_complete, self.current_duration)
            self.after(0, self._update_total_progress, done_files, total_files, self.done_duration, self.total_duration)

        for inp, t in list(self.tasks):
            if self.stop_requested:
                self._queue_log("WARN", "Зупинено користувачем.")
                break
            if merge_enabled and t == "video":
                continue

            if not inp.exists():
                self._queue_log("ERROR", f"Файл не знайдено: {inp}")
                done_files += 1
                self.after(0, self._update_total_progress, done_files, total_files, self.done_duration, self.total_duration)
                continue

            out_ext = out_vid if t == "video" else out_img
            if self.overwrite_var.get():
                outp = out_dir / f"{inp.stem}.{out_ext}"
            else:
                outp = safe_output_name(out_dir, inp, out_ext)

            info = self.media_info.get(inp)
            self.current_duration = info.duration if info and t == "video" else None
            self.after(0, lambda name=inp.name: self.status_var.set(f"Обробка: {name}"))
            self._queue_log("INFO", f"→ {inp.name} ({t}) ==> {outp.name}")

            try:
                cmd = self._build_cmd_video(inp, outp, info) if t == "video" else self._build_cmd_image(inp, outp)
                rc = self._run_ffmpeg(cmd, self.current_duration, self.done_duration, self.total_duration, done_files, total_files)
                if rc == 0 and outp.exists():
                    self._queue_log("OK", f"Готово: {outp.name}")
                else:
                    self._queue_log("ERROR", f"Помилка конвертації: {inp.name} (код {rc})")
            except FileNotFoundError:
                self._queue_log("ERROR", "FFmpeg не знайдено під час запуску. Перевір шлях до ffmpeg.exe.")
                break
            except Exception as e:
                self._queue_log("ERROR", f"Несподівана помилка: {e}")

            done_files += 1
            if t == "video" and self.current_duration:
                self.done_duration += self.current_duration
            self.after(0, self._mark_file_complete, self.current_duration)
            self.after(0, self._update_total_progress, done_files, total_files, self.done_duration, self.total_duration)

        self.after(0, self._finish)

    def _finish(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set("Зупинено." if self.stop_requested else "Готово.")

    def run(self):
        self.mainloop()
if __name__ == "__main__":
    try:
        if os.name == "nt":
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ConverterUI()
    app.run()
