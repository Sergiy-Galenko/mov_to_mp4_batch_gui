import os
import queue
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

from config.constants import (
    APP_TITLE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_THEME,
    OUT_IMAGE_FORMATS,
    OUT_VIDEO_FORMATS,
    POSITION_OPTIONS,
    PORTRAIT_PRESETS,
    ROTATE_OPTIONS,
    VIDEO_CODEC_OPTIONS,
    HW_ENCODER_OPTIONS,
    PRESET_STORE,
    THEME_STORE,
)
from config.paths import find_ffmpeg, find_ffprobe
from core.models import ConversionSettings, MediaInfo, TaskItem
from core.presets import load_presets, save_presets
from services.ffmpeg_service import FfmpegService
from services.converter_service import ConverterService
from ui.styles import THEMES, apply_theme, load_custom_theme, save_custom_theme
from utils.files import media_type
from utils.formatting import format_bytes, format_time, parse_float, parse_int, parse_time_to_seconds

SPACE_1 = 8
SPACE_2 = 16
SPACE_3 = 24
SPACE_4 = 32
CONTENT_MAX_WIDTH = 1160
CONTENT_MIN_PAD = 16
COMPACT_BREAKPOINT = 980


class MediaConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x820")
        self.minsize(860, 720)

        self.event_queue: "queue.Queue[tuple]" = queue.Queue()
        self.ffmpeg_service = FfmpegService(find_ffmpeg(), None)
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        self.converter = ConverterService(self.ffmpeg_service, self.event_queue)

        self.tasks: List[TaskItem] = []
        self.media_info_cache: Dict[Path, MediaInfo] = {}
        self.presets: Dict[str, dict] = load_presets(PRESET_STORE)
        self.custom_theme: Optional[Dict[str, str]] = load_custom_theme(THEME_STORE)
        self.theme_colors: Dict[str, str] = {}
        self._scroll_canvases: List[tk.Canvas] = []
        self.max_content_width = CONTENT_MAX_WIDTH
        self.min_side_padding = CONTENT_MIN_PAD
        self._current_side_pad: Optional[int] = None
        self._layout_mode: Optional[str] = None

        self._build_vars()
        self._build_ui()
        self._apply_theme(DEFAULT_THEME)
        self._refresh_encoders(initial=True)
        self._refresh_presets()
        self._poll_events()

    def _build_vars(self) -> None:
        self.ffmpeg_path_var = tk.StringVar(value=self.ffmpeg_service.ffmpeg_path or "")
        self.output_dir_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.theme_var = tk.StringVar(value=DEFAULT_THEME)

        self.out_video_fmt_var = tk.StringVar(value="mp4")
        self.out_image_fmt_var = tk.StringVar(value="jpg")
        self.crf_var = tk.IntVar(value=23)
        self.preset_var = tk.StringVar(value="medium")
        self.portrait_var = tk.StringVar(value="Вимкнено")
        self.img_quality_var = tk.IntVar(value=90)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.fast_copy_var = tk.BooleanVar(value=False)

        self.trim_start_var = tk.StringVar(value="")
        self.trim_end_var = tk.StringVar(value="")
        self.merge_var = tk.BooleanVar(value=False)
        self.merge_name_var = tk.StringVar(value="merged")

        self.resize_w_var = tk.StringVar(value="")
        self.resize_h_var = tk.StringVar(value="")
        self.crop_w_var = tk.StringVar(value="")
        self.crop_h_var = tk.StringVar(value="")
        self.crop_x_var = tk.StringVar(value="")
        self.crop_y_var = tk.StringVar(value="")
        self.rotate_var = tk.StringVar(value=ROTATE_OPTIONS[0])
        self.speed_var = tk.StringVar(value="1.0")

        self.wm_path_var = tk.StringVar(value="")
        self.wm_pos_var = tk.StringVar(value=POSITION_OPTIONS[3])
        self.wm_opacity_var = tk.IntVar(value=80)
        self.wm_scale_var = tk.IntVar(value=30)

        self.text_wm_var = tk.StringVar(value="")
        self.text_pos_var = tk.StringVar(value=POSITION_OPTIONS[3])
        self.text_size_var = tk.IntVar(value=24)
        self.text_color_var = tk.StringVar(value="white")
        self.text_box_var = tk.BooleanVar(value=False)
        self.text_box_color_var = tk.StringVar(value="black")
        self.text_box_opacity_var = tk.IntVar(value=50)
        self.text_font_var = tk.StringVar(value="")

        self.codec_var = tk.StringVar(value=VIDEO_CODEC_OPTIONS[0])
        self.hw_var = tk.StringVar(value=HW_ENCODER_OPTIONS[0])
        self.encoder_info_var = tk.StringVar(value="Доступні: --")

        self.preset_name_var = tk.StringVar(value="")
        self.preset_select_var = tk.StringVar(value="")

        self.copy_metadata_var = tk.BooleanVar(value=True)
        self.strip_metadata_var = tk.BooleanVar(value=False)
        self.meta_title_var = tk.StringVar(value="")
        self.meta_comment_var = tk.StringVar(value="")
        self.meta_author_var = tk.StringVar(value="")
        self.meta_copyright_var = tk.StringVar(value="")

        self.status_var = tk.StringVar(value="Готово")
        self.file_progress_var = tk.DoubleVar(value=0.0)
        self.total_progress_var = tk.DoubleVar(value=0.0)
        self.file_progress_text_var = tk.StringVar(value="Файл: --")
        self.total_progress_text_var = tk.StringVar(value="Всього: --")

        self.info_name_var = tk.StringVar(value="—")
        self.info_duration_var = tk.StringVar(value="--:--")
        self.info_codec_var = tk.StringVar(value="—")
        self.info_res_var = tk.StringVar(value="—")
        self.info_size_var = tk.StringVar(value="—")
        self.info_container_var = tk.StringVar(value="—")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.header = ttk.Frame(self, style="Card.TFrame", padding=(SPACE_3, SPACE_2))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(self.header, style="Panel.TFrame")
        title_block.grid(row=0, column=0, sticky="w")
        title = ttk.Label(title_block, text=APP_TITLE, style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(
            title_block,
            text="Пакетна конвертація відео та фото через FFmpeg.",
            style="Subtitle.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))

        actions = ttk.Frame(self.header, style="Panel.TFrame")
        actions.grid(row=0, column=1, sticky="e")

        theme_box = ttk.Combobox(
            actions,
            textvariable=self.theme_var,
            values=["light", "dark", "custom"],
            state="readonly",
            width=10,
        )
        theme_box.grid(row=0, column=0, padx=(0, SPACE_1))
        theme_box.bind("<<ComboboxSelected>>", lambda _e: self._on_theme_change())

        ttk.Button(actions, text="Налаштувати тему", command=self._open_theme_editor, style="Ghost.TButton").grid(
            row=0, column=1
        )

        ffmpeg_frame = ttk.Frame(self.header, style="Panel.TFrame")
        ffmpeg_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_2, 0))
        ffmpeg_frame.columnconfigure(1, weight=1)
        ttk.Label(ffmpeg_frame, text="FFmpeg:").grid(row=0, column=0, sticky="w")
        ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_path_var).grid(row=0, column=1, sticky="ew", padx=SPACE_1)
        ttk.Button(ffmpeg_frame, text="Вказати", command=self.pick_ffmpeg, style="Secondary.TButton").grid(row=0, column=2, padx=SPACE_1)
        ttk.Button(ffmpeg_frame, text="Перевірити", command=self._refresh_encoders, style="Ghost.TButton").grid(
            row=0, column=3, padx=(0, SPACE_1)
        )

        self.main = ttk.Frame(self, padding=(SPACE_3, 0, SPACE_3, SPACE_3))
        self.main.grid(row=1, column=0, sticky="nsew")
        self.main.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(self.main, style="Card.TFrame", padding=SPACE_2)
        self.content = ttk.Frame(self.main, style="Card.TFrame", padding=SPACE_2)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self._build_sidebar(self.sidebar)
        self._build_content(self.content)
        self._set_layout("wide")

        self.status = ttk.Frame(self, style="Card.TFrame", padding=(SPACE_3, SPACE_2))
        self.status.grid(row=2, column=0, sticky="ew")
        self.status.columnconfigure(1, weight=1)
        self.status.columnconfigure(3, weight=1)

        ttk.Label(self.status, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Progressbar(self.status, variable=self.file_progress_var, maximum=100.0).grid(
            row=0, column=1, sticky="ew", padx=SPACE_2
        )
        ttk.Label(self.status, textvariable=self.file_progress_text_var).grid(row=0, column=2, sticky="w")
        ttk.Progressbar(self.status, variable=self.total_progress_var, maximum=100.0).grid(
            row=0, column=3, sticky="ew", padx=SPACE_2
        )
        ttk.Label(self.status, textvariable=self.total_progress_text_var).grid(row=0, column=4, sticky="w")

        self.bind("<Configure>", self._on_resize)
        self.after(0, self._sync_layout)

    def _sync_layout(self) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        if width <= 1:
            width = self.winfo_screenwidth()
        self._apply_content_padding(width)
        mode = "compact" if width < COMPACT_BREAKPOINT else "wide"
        self._set_layout(mode)

    def _on_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        width = max(event.width, 1)
        self._apply_content_padding(width)
        mode = "compact" if width < COMPACT_BREAKPOINT else "wide"
        self._set_layout(mode)

    def _apply_content_padding(self, width: int) -> None:
        side_pad = max((width - self.max_content_width) // 2, self.min_side_padding)
        if side_pad == self._current_side_pad:
            return
        for frame in (self.header, self.main, self.status):
            frame.grid_configure(padx=(side_pad, side_pad))
        self._current_side_pad = side_pad

    def _set_layout(self, mode: str) -> None:
        if mode == self._layout_mode:
            return
        self.sidebar.grid_forget()
        self.content.grid_forget()
        if mode == "compact":
            self.main.columnconfigure(0, weight=1)
            self.main.columnconfigure(1, weight=0)
            self.main.rowconfigure(0, weight=0)
            self.main.rowconfigure(1, weight=1)
            self.sidebar.grid(row=0, column=0, sticky="ew")
            self.content.grid(row=1, column=0, sticky="nsew", pady=(SPACE_2, 0))
        else:
            self.main.rowconfigure(0, weight=1)
            self.main.rowconfigure(1, weight=0)
            self.main.columnconfigure(0, weight=0)
            self.main.columnconfigure(1, weight=1)
            self.sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, SPACE_2))
            self.content.grid(row=0, column=1, sticky="nsew")
        self._layout_mode = mode

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        queue_frame = ttk.LabelFrame(parent, text="Черга", padding=SPACE_2)
        queue_frame.pack(fill="both", expand=False)

        self.queue_listbox = tk.Listbox(queue_frame, height=10, selectmode="extended")
        self.queue_listbox.pack(side="left", fill="both", expand=True)
        self.queue_listbox.bind("<<ListboxSelect>>", lambda _e: self._show_selected_info())
        sb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_listbox.yview)
        sb.pack(side="right", fill="y")
        self.queue_listbox.configure(yscrollcommand=sb.set)

        btns = ttk.Frame(parent, style="Panel.TFrame")
        btns.pack(fill="x", pady=(SPACE_1, 0))
        ttk.Button(btns, text="Додати файли", command=self.add_files, style="Secondary.TButton").pack(fill="x", pady=SPACE_1)
        ttk.Button(btns, text="Додати папку", command=self.add_folder, style="Secondary.TButton").pack(fill="x", pady=SPACE_1)
        ttk.Button(btns, text="Видалити вибрані", command=self.remove_selected, style="Secondary.TButton").pack(fill="x", pady=SPACE_1)
        ttk.Button(btns, text="Очистити", command=self.clear_list, style="Secondary.TButton").pack(fill="x", pady=SPACE_1)

        out_frame = ttk.LabelFrame(parent, text="Вивід", padding=SPACE_2)
        out_frame.pack(fill="x", pady=(SPACE_2, 0))
        out_frame.columnconfigure(0, weight=1)
        ttk.Entry(out_frame, textvariable=self.output_dir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(out_frame, text="Вибрати", command=self.pick_output, style="Secondary.TButton").grid(
            row=1, column=0, sticky="ew", pady=SPACE_1
        )
        ttk.Button(out_frame, text="Відкрити папку", command=self.open_output_folder, style="Ghost.TButton").grid(
            row=2, column=0, sticky="ew"
        )

        info_frame = ttk.LabelFrame(parent, text="Інформація", padding=SPACE_2)
        info_frame.pack(fill="x", pady=(SPACE_2, 0))
        self._info_row(info_frame, "Файл", self.info_name_var)
        self._info_row(info_frame, "Тривалість", self.info_duration_var)
        self._info_row(info_frame, "Кодеки", self.info_codec_var)
        self._info_row(info_frame, "Розмір", self.info_size_var)
        self._info_row(info_frame, "Роздільність", self.info_res_var)
        self._info_row(info_frame, "Контейнер", self.info_container_var)

        actions = ttk.LabelFrame(parent, text="Дії", padding=SPACE_2)
        actions.pack(fill="x", pady=(SPACE_2, 0))
        self.btn_start = ttk.Button(actions, text="Старт", command=self.start, style="TButton")
        self.btn_start.pack(fill="x", pady=SPACE_1)
        self.btn_stop = ttk.Button(actions, text="Стоп", command=self.stop, style="Secondary.TButton")
        self.btn_stop.pack(fill="x")
        self.btn_stop.configure(state="disabled")

    def _info_row(self, parent: ttk.Frame, label: str, var: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=SPACE_1)
        ttk.Label(row, text=f"{label}:", width=10).pack(side="left")
        ttk.Label(row, textvariable=var).pack(side="left", fill="x", expand=True)

    def _build_content(self, parent: ttk.Frame) -> None:
        paned = ttk.PanedWindow(parent, orient="vertical")
        paned.grid(row=0, column=0, sticky="nsew")

        options = ttk.Frame(paned, style="Panel.TFrame")
        log_frame = ttk.LabelFrame(paned, text="Лог", padding=SPACE_2)
        paned.add(options, weight=3)
        paned.add(log_frame, weight=1)

        options.columnconfigure(0, weight=1)
        options.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(options)
        notebook.grid(row=0, column=0, sticky="nsew")

        basic = ttk.Frame(notebook, padding=SPACE_2, style="Panel.TFrame")
        advanced = ttk.Frame(notebook, padding=SPACE_2, style="Panel.TFrame")
        codec_tab = ttk.Frame(notebook, padding=SPACE_2, style="Panel.TFrame")
        presets_tab = ttk.Frame(notebook, padding=SPACE_2, style="Panel.TFrame")
        enhance_tab = ttk.Frame(notebook, padding=SPACE_2, style="Panel.TFrame")
        metadata_tab = ttk.Frame(notebook, padding=SPACE_2, style="Panel.TFrame")

        notebook.add(basic, text="Базові")
        notebook.add(advanced, text="Розширені")
        notebook.add(codec_tab, text="Кодеки/GPU")
        notebook.add(presets_tab, text="Пресети")
        notebook.add(enhance_tab, text="Покращення")
        notebook.add(metadata_tab, text="Метадані")

        self._build_basic_tab(basic)
        advanced_inner = self._make_scrollable_tab(advanced)
        self._build_advanced_tab(advanced_inner)
        self._build_codec_tab(codec_tab)
        self._build_presets_tab(presets_tab)
        self._build_enhance_tab(enhance_tab)
        self._build_metadata_tab(metadata_tab)

        self.log_text = tk.Text(log_frame, height=6, wrap="word", state="disabled", padx=SPACE_1, pady=SPACE_1)
        self.log_text.configure(font=("Segoe UI", 11))
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _make_scrollable_tab(self, parent: ttk.Frame) -> ttk.Frame:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas, padding=SPACE_2, style="Panel.TFrame")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        self._scroll_canvases.append(canvas)
        return inner

    def _build_basic_tab(self, parent: ttk.Frame) -> None:
        video_frame = ttk.LabelFrame(parent, text="Відео", padding=SPACE_2)
        video_frame.pack(fill="x", pady=(0, SPACE_2))

        ttk.Label(video_frame, text="Формат:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(video_frame, textvariable=self.out_video_fmt_var, values=OUT_VIDEO_FORMATS, state="readonly", width=8).grid(
            row=0, column=1, sticky="w", padx=(SPACE_1, SPACE_3)
        )
        ttk.Label(video_frame, text="CRF:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(video_frame, from_=14, to=35, textvariable=self.crf_var, width=6).grid(
            row=0, column=3, sticky="w", padx=(SPACE_1, SPACE_3)
        )
        ttk.Label(video_frame, text="Preset:").grid(row=0, column=4, sticky="w")
        ttk.Combobox(
            video_frame,
            textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            state="readonly",
            width=10,
        ).grid(row=0, column=5, sticky="w")

        ttk.Label(video_frame, text="Портрет:").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Combobox(video_frame, textvariable=self.portrait_var, values=list(PORTRAIT_PRESETS.keys()), state="readonly", width=22).grid(
            row=1, column=1, sticky="w", padx=(SPACE_1, SPACE_3), pady=(SPACE_1, 0)
        )

        img_frame = ttk.LabelFrame(parent, text="Фото", padding=SPACE_2)
        img_frame.pack(fill="x", pady=(0, SPACE_2))
        ttk.Label(img_frame, text="Формат:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(img_frame, textvariable=self.out_image_fmt_var, values=OUT_IMAGE_FORMATS, state="readonly", width=8).grid(
            row=0, column=1, sticky="w", padx=(SPACE_1, SPACE_3)
        )
        ttk.Label(img_frame, text="Якість (1–100):").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(img_frame, from_=1, to=100, textvariable=self.img_quality_var, width=6).grid(
            row=0, column=3, sticky="w", padx=(SPACE_1, 0)
        )

        behavior = ttk.LabelFrame(parent, text="Поведінка", padding=SPACE_2)
        behavior.pack(fill="x", pady=(0, SPACE_2))
        ttk.Checkbutton(behavior, text="Перезаписувати існуючі файли", variable=self.overwrite_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="Fast copy (без перекодування, якщо можливо)", variable=self.fast_copy_var).grid(
            row=1, column=0, sticky="w", pady=(SPACE_1, 0)
        )

    def _build_advanced_tab(self, parent: ttk.Frame) -> None:
        time_frame = ttk.LabelFrame(parent, text="Час / Merge", padding=SPACE_2)
        time_frame.pack(fill="x", pady=(0, SPACE_2))
        ttk.Label(time_frame, text="Початок (hh:mm:ss або сек):").grid(row=0, column=0, sticky="w")
        ttk.Entry(time_frame, textvariable=self.trim_start_var, width=12).grid(
            row=0, column=1, sticky="w", padx=(SPACE_1, SPACE_3)
        )
        ttk.Label(time_frame, text="Кінець (hh:mm:ss або сек):").grid(row=0, column=2, sticky="w")
        ttk.Entry(time_frame, textvariable=self.trim_end_var, width=12).grid(row=0, column=3, sticky="w", padx=(SPACE_1, 0))

        ttk.Checkbutton(time_frame, text="Об'єднати всі відео в один файл", variable=self.merge_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(SPACE_1, 0)
        )
        ttk.Label(time_frame, text="Назва файлу:").grid(row=1, column=2, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(time_frame, textvariable=self.merge_name_var).grid(
            row=1, column=3, sticky="w", padx=(SPACE_1, 0), pady=(SPACE_1, 0)
        )

        transform = ttk.LabelFrame(parent, text="Трансформації", padding=SPACE_2)
        transform.pack(fill="x", pady=(0, SPACE_2))

        ttk.Label(transform, text="Resize W:").grid(row=0, column=0, sticky="w")
        ttk.Entry(transform, textvariable=self.resize_w_var, width=6).grid(row=0, column=1, sticky="w", padx=(SPACE_1, SPACE_2))
        ttk.Label(transform, text="H:").grid(row=0, column=2, sticky="w")
        ttk.Entry(transform, textvariable=self.resize_h_var, width=6).grid(row=0, column=3, sticky="w", padx=(SPACE_1, SPACE_2))
        ttk.Label(transform, text="Crop W:").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(transform, textvariable=self.crop_w_var, width=6).grid(
            row=1, column=1, sticky="w", padx=(SPACE_1, SPACE_2), pady=(SPACE_1, 0)
        )
        ttk.Label(transform, text="H:").grid(row=1, column=2, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(transform, textvariable=self.crop_h_var, width=6).grid(
            row=1, column=3, sticky="w", padx=(SPACE_1, SPACE_2), pady=(SPACE_1, 0)
        )
        ttk.Label(transform, text="X:").grid(row=1, column=4, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(transform, textvariable=self.crop_x_var, width=6).grid(
            row=1, column=5, sticky="w", padx=(SPACE_1, SPACE_2), pady=(SPACE_1, 0)
        )
        ttk.Label(transform, text="Y:").grid(row=1, column=6, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(transform, textvariable=self.crop_y_var, width=6).grid(
            row=1, column=7, sticky="w", padx=(SPACE_1, 0), pady=(SPACE_1, 0)
        )

        ttk.Label(transform, text="Поворот:").grid(row=2, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Combobox(transform, textvariable=self.rotate_var, values=ROTATE_OPTIONS, state="readonly", width=12).grid(
            row=2, column=1, sticky="w", padx=(SPACE_1, SPACE_2), pady=(SPACE_1, 0)
        )
        ttk.Label(transform, text="Speed:").grid(row=2, column=2, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(transform, textvariable=self.speed_var, width=6).grid(
            row=2, column=3, sticky="w", padx=(SPACE_1, 0), pady=(SPACE_1, 0)
        )

        watermark = ttk.LabelFrame(parent, text="Водяний знак", padding=SPACE_2)
        watermark.pack(fill="x", pady=(0, SPACE_2))
        watermark.columnconfigure(1, weight=1)
        ttk.Label(watermark, text="Файл:").grid(row=0, column=0, sticky="w")
        ttk.Entry(watermark, textvariable=self.wm_path_var).grid(row=0, column=1, sticky="ew", padx=SPACE_1)
        ttk.Button(watermark, text="Вибрати", command=self.pick_watermark, style="Secondary.TButton").grid(
            row=0, column=2, padx=SPACE_1
        )
        ttk.Label(watermark, text="Scale %:").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Spinbox(watermark, from_=1, to=200, textvariable=self.wm_scale_var, width=6).grid(
            row=1, column=1, sticky="w", padx=SPACE_1, pady=(SPACE_1, 0)
        )
        ttk.Label(watermark, text="Opacity %:").grid(row=1, column=2, sticky="w", pady=(SPACE_1, 0))
        ttk.Spinbox(watermark, from_=0, to=100, textvariable=self.wm_opacity_var, width=6).grid(
            row=1, column=3, sticky="w", padx=SPACE_1, pady=(SPACE_1, 0)
        )
        ttk.Label(watermark, text="Позиція:").grid(row=1, column=4, sticky="w", pady=(SPACE_1, 0))
        ttk.Combobox(watermark, textvariable=self.wm_pos_var, values=POSITION_OPTIONS, state="readonly", width=12).grid(
            row=1, column=5, sticky="w", padx=SPACE_1, pady=(SPACE_1, 0)
        )

        text = ttk.LabelFrame(parent, text="Текст", padding=SPACE_2)
        text.pack(fill="x", pady=(0, SPACE_2))
        text.columnconfigure(1, weight=1)
        ttk.Label(text, text="Текст:").grid(row=0, column=0, sticky="w")
        ttk.Entry(text, textvariable=self.text_wm_var).grid(row=0, column=1, sticky="ew", padx=SPACE_1)
        ttk.Label(text, text="Розмір:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(text, from_=8, to=120, textvariable=self.text_size_var, width=6).grid(
            row=0, column=3, sticky="w", padx=SPACE_1
        )
        ttk.Label(text, text="Колір:").grid(row=0, column=4, sticky="w")
        ttk.Entry(text, textvariable=self.text_color_var, width=10).grid(row=0, column=5, sticky="w", padx=SPACE_1)

        ttk.Label(text, text="Позиція:").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Combobox(text, textvariable=self.text_pos_var, values=POSITION_OPTIONS, state="readonly", width=12).grid(
            row=1, column=1, sticky="w", padx=SPACE_1, pady=(SPACE_1, 0)
        )
        ttk.Label(text, text="Шрифт (.ttf):").grid(row=1, column=2, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(text, textvariable=self.text_font_var).grid(row=1, column=3, sticky="ew", padx=SPACE_1, pady=(SPACE_1, 0))
        ttk.Button(text, text="Вибрати", command=self.pick_font, style="Secondary.TButton").grid(
            row=1, column=4, padx=SPACE_1, pady=(SPACE_1, 0)
        )

        ttk.Checkbutton(text, text="Фон тексту", variable=self.text_box_var).grid(row=2, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Label(text, text="Колір:").grid(row=2, column=1, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(text, textvariable=self.text_box_color_var, width=10).grid(
            row=2, column=2, sticky="w", padx=SPACE_1, pady=(SPACE_1, 0)
        )
        ttk.Label(text, text="Opacity %:").grid(row=2, column=3, sticky="w", pady=(SPACE_1, 0))
        ttk.Spinbox(text, from_=0, to=100, textvariable=self.text_box_opacity_var, width=6).grid(
            row=2, column=4, sticky="w", padx=SPACE_1, pady=(SPACE_1, 0)
        )

    def _build_codec_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Кодек відео:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(parent, textvariable=self.codec_var, values=VIDEO_CODEC_OPTIONS, state="readonly", width=18).grid(
            row=0, column=1, sticky="w", padx=(SPACE_1, 0)
        )
        ttk.Label(parent, text="GPU/CPU:").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Combobox(parent, textvariable=self.hw_var, values=HW_ENCODER_OPTIONS, state="readonly", width=18).grid(
            row=1, column=1, sticky="w", padx=(SPACE_1, 0), pady=(SPACE_1, 0)
        )
        ttk.Label(parent, textvariable=self.encoder_info_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(SPACE_2, 0))

    def _build_presets_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Збережені:").grid(row=0, column=0, sticky="w")
        self.preset_combo = ttk.Combobox(parent, textvariable=self.preset_select_var, values=[], state="readonly")
        self.preset_combo.grid(row=0, column=1, sticky="ew", padx=SPACE_1)
        ttk.Button(parent, text="Завантажити", command=self.load_preset, style="Secondary.TButton").grid(row=0, column=2, padx=SPACE_1)
        ttk.Button(parent, text="Видалити", command=self.delete_preset, style="Ghost.TButton").grid(row=0, column=3, padx=SPACE_1)

        ttk.Label(parent, text="Назва нового:").grid(row=1, column=0, sticky="w", pady=(SPACE_2, 0))
        ttk.Entry(parent, textvariable=self.preset_name_var).grid(row=1, column=1, sticky="ew", padx=SPACE_1, pady=(SPACE_2, 0))
        ttk.Button(parent, text="Зберегти", command=self.save_preset).grid(row=1, column=2, padx=SPACE_1, pady=(SPACE_2, 0))

    def _build_enhance_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        header = ttk.Label(parent, text="Швидкі профілі покращення відео")
        header.grid(row=0, column=0, sticky="w", pady=(0, SPACE_2))

        card = ttk.LabelFrame(parent, text="Масштабування (resize)", padding=SPACE_2)
        card.grid(row=1, column=0, sticky="ew")
        for col in range(3):
            card.columnconfigure(col, weight=1)

        ttk.Label(card, text="Обери цільову роздільність для upscale:").grid(row=0, column=0, columnspan=3, sticky="w")
        presets = [
            ("360p (640x360)", 640, 360),
            ("480p (854x480)", 854, 480),
            ("540p (960x540)", 960, 540),
            ("720p (1280x720)", 1280, 720),
            ("900p (1600x900)", 1600, 900),
            ("1080p (1920x1080)", 1920, 1080),
            ("1440p (2560x1440)", 2560, 1440),
            ("4K (3840x2160)", 3840, 2160),
            ("8K (7680x4320)", 7680, 4320),
            ("16K (15360x8640)", 15360, 8640),
        ]
        row = 1
        col = 0
        for label, w, h in presets:
            ttk.Button(card, text=f"До {label}", command=lambda ww=w, hh=h: self._apply_upscale(ww, hh), style="Secondary.TButton").grid(
                row=row, column=col, sticky="ew", padx=SPACE_1, pady=(SPACE_1, 0)
            )
            col += 1
            if col >= 3:
                col = 0
                row += 1

        hint = ttk.Label(
            parent,
            text="Порада: апскейл збільшує розмір/час. Використовуй адекватні параметри CRF і кодеки (H.265/AV1).",
            style="Muted.TLabel",
            wraplength=640,
        )
        hint.grid(row=2, column=0, sticky="w", pady=(SPACE_2, 0))

    def _build_metadata_tab(self, parent: ttk.Frame) -> None:
        ttk.Checkbutton(parent, text="Копіювати метадані з джерела", variable=self.copy_metadata_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(parent, text="Очистити метадані", variable=self.strip_metadata_var).grid(
            row=1, column=0, sticky="w", pady=(SPACE_1, 0)
        )

        form = ttk.LabelFrame(parent, text="Поля", padding=SPACE_2)
        form.grid(row=2, column=0, sticky="ew", pady=(SPACE_2, 0))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Title:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.meta_title_var).grid(row=0, column=1, sticky="ew", padx=SPACE_1)
        ttk.Label(form, text="Author:").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(form, textvariable=self.meta_author_var).grid(row=1, column=1, sticky="ew", padx=SPACE_1, pady=(SPACE_1, 0))
        ttk.Label(form, text="Comment:").grid(row=2, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(form, textvariable=self.meta_comment_var).grid(row=2, column=1, sticky="ew", padx=SPACE_1, pady=(SPACE_1, 0))
        ttk.Label(form, text="Copyright:").grid(row=3, column=0, sticky="w", pady=(SPACE_1, 0))
        ttk.Entry(form, textvariable=self.meta_copyright_var).grid(row=3, column=1, sticky="ew", padx=SPACE_1, pady=(SPACE_1, 0))

    def _on_theme_change(self) -> None:
        choice = self.theme_var.get()
        if choice == "custom" and not self.custom_theme:
            self._open_theme_editor()
            if not self.custom_theme:
                self.theme_var.set(DEFAULT_THEME)
                self._apply_theme(DEFAULT_THEME)
            return
        self._apply_theme(choice)

    def _open_theme_editor(self) -> None:
        base = dict(self.custom_theme or THEMES.get(self.theme_var.get(), THEMES["light"]))

        dialog = tk.Toplevel(self)
        dialog.title("Налаштування теми")
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=SPACE_2)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        fields = [
            ("bg", "Background"),
            ("panel", "Panel"),
            ("text", "Text"),
            ("muted", "Muted"),
            ("accent", "Accent"),
            ("accent_alt", "Accent Alt"),
            ("border", "Border"),
        ]
        entries: Dict[str, tk.Entry] = {}

        for idx, (key, label) in enumerate(fields):
            ttk.Label(frame, text=label + ":").grid(row=idx, column=0, sticky="w", pady=SPACE_1)
            entry = ttk.Entry(frame)
            entry.insert(0, base.get(key, ""))
            entry.grid(row=idx, column=1, sticky="ew", padx=SPACE_1, pady=SPACE_1)
            entries[key] = entry
            ttk.Button(frame, text="...", width=3, command=lambda k=key: self._pick_color(entries[k]), style="Ghost.TButton").grid(
                row=idx, column=2, padx=SPACE_1, pady=SPACE_1
            )

        btns = ttk.Frame(frame)
        btns.grid(row=len(fields), column=0, columnspan=3, sticky="e", pady=(SPACE_2, 0))

        def _save():
            theme = dict(base)
            for key, entry in entries.items():
                value = entry.get().strip()
                if value:
                    theme[key] = value
            self.custom_theme = theme
            save_custom_theme(THEME_STORE, theme)
            self.theme_var.set("custom")
            self._apply_theme("custom")
            dialog.destroy()

        ttk.Button(btns, text="Скасувати", command=dialog.destroy, style="Secondary.TButton").pack(side="right", padx=SPACE_1)
        ttk.Button(btns, text="Зберегти", command=_save).pack(side="right")

    def _pick_color(self, entry: tk.Entry) -> None:
        current = entry.get().strip() or None
        color = colorchooser.askcolor(initialcolor=current, parent=self)
        if color and color[1]:
            entry.delete(0, "end")
            entry.insert(0, color[1])

    def _apply_theme(self, theme_name: str) -> None:
        self.theme_colors = apply_theme(self, theme_name, custom=self.custom_theme)
        if hasattr(self, "queue_listbox"):
            bg = self.theme_colors["panel"]
            fg = self.theme_colors["text"]
            self.queue_listbox.configure(
                background=bg,
                foreground=fg,
                selectbackground=self.theme_colors["accent"],
                selectforeground=self.theme_colors["panel"],
            )
        if hasattr(self, "log_text"):
            self.log_text.configure(background=self.theme_colors["panel"], foreground=self.theme_colors["text"], insertbackground=self.theme_colors["text"])
        for canvas in self._scroll_canvases:
            canvas.configure(background=self.theme_colors["panel"])

    def _refresh_encoders(self, initial: bool = False) -> None:
        ffmpeg_path = self.ffmpeg_path_var.get().strip()
        if ffmpeg_path:
            self.ffmpeg_service.ffmpeg_path = ffmpeg_path
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            if initial:
                self._append_log("ERROR", "FFmpeg не знайдено. Вкажи ffmpeg.exe або додай у PATH.")
            return
        self.ffmpeg_service.encoder_caps = self.ffmpeg_service.detect_encoders()
        summary = []
        caps = self.ffmpeg_service.encoder_caps
        if {"h264_nvenc", "hevc_nvenc", "av1_nvenc"} & caps:
            summary.append("NVENC")
        if {"h264_qsv", "hevc_qsv", "av1_qsv"} & caps:
            summary.append("QSV")
        if {"h264_amf", "hevc_amf", "av1_amf"} & caps:
            summary.append("AMF")
        if "libx265" in caps:
            summary.append("x265")
        if {"libsvtav1", "libaom-av1"} & caps:
            summary.append("AV1")
        if "libvpx-vp9" in caps:
            summary.append("VP9")
        self.encoder_info_var.set(f"Доступні: {', '.join(summary) if summary else 'немає'}")
        if initial:
            self._append_log("OK", f"FFmpeg знайдено: {self.ffmpeg_service.ffmpeg_path}")
            if self.ffmpeg_service.ffprobe_path:
                self._append_log("OK", f"FFprobe знайдено: {self.ffmpeg_service.ffprobe_path}")
            else:
                self._append_log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")

    def pick_ffmpeg(self) -> None:
        path = filedialog.askopenfilename(title="Вкажи ffmpeg.exe", filetypes=[("FFmpeg", "ffmpeg.exe"), ("All", "*.*")])
        if path:
            self.ffmpeg_path_var.set(path)
            self._refresh_encoders()

    def pick_output(self) -> None:
        folder = filedialog.askdirectory(title="Папка виводу")
        if folder:
            self.output_dir_var.set(folder)

    def open_output_folder(self) -> None:
        folder = Path(self.output_dir_var.get()).expanduser()
        if not folder.exists():
            messagebox.showerror("Папка", "Папка виводу не існує.")
            return
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            try:
                os.system(f"xdg-open '{folder}'")
            except Exception:
                pass

    def add_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Додати файли",
            filetypes=[("Media", "*.mp4 *.mov *.mkv *.webm *.avi *.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif"), ("All", "*.*")],
        )
        self._add_paths([Path(p) for p in files])

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Додати папку")
        if folder:
            base = Path(folder)
            items = [p for p in base.rglob("*") if p.is_file()]
            self._add_paths(items)

    def _add_paths(self, paths: List[Path]) -> None:
        added = 0
        for path in paths:
            mtype = media_type(path)
            if not mtype:
                continue
            self.tasks.append(TaskItem(path=path, media_type=mtype))
            label = f"{path.name}  [{mtype}]"
            self.queue_listbox.insert("end", label)
            added += 1
        if added:
            self._append_log("OK", f"Додано файлів: {added}")
        else:
            self._append_log("WARN", "Не знайдено підтримуваних файлів.")

    def remove_selected(self) -> None:
        indices = list(self.queue_listbox.curselection())
        if not indices:
            return
        for idx in reversed(indices):
            self.queue_listbox.delete(idx)
            del self.tasks[idx]
        self._append_log("INFO", f"Видалено: {len(indices)}")
        self._clear_info()

    def clear_list(self) -> None:
        self.queue_listbox.delete(0, "end")
        self.tasks.clear()
        self._append_log("INFO", "Чергу очищено")
        self._clear_info()

    def _clear_info(self) -> None:
        self.info_name_var.set("—")
        self.info_duration_var.set("--:--")
        self.info_codec_var.set("—")
        self.info_res_var.set("—")
        self.info_size_var.set("—")
        self.info_container_var.set("—")

    def _show_selected_info(self) -> None:
        selection = self.queue_listbox.curselection()
        if not selection:
            self._clear_info()
            return
        idx = selection[0]
        if idx >= len(self.tasks):
            return
        task = self.tasks[idx]
        self.info_name_var.set(task.path.name)
        info = self.media_info_cache.get(task.path)
        if info:
            self._update_info(info)
            return
        if not self.ffmpeg_service.ffprobe_path:
            return
        threading.Thread(target=self._probe_media_async, args=(task.path,), daemon=True).start()

    def _probe_media_async(self, path: Path) -> None:
        info = self.ffmpeg_service.probe_media(path)
        if info:
            self.event_queue.put(("media_info", path, info))

    def _update_info(self, info: MediaInfo) -> None:
        self.info_duration_var.set(format_time(info.duration))
        self.info_codec_var.set(f"{info.vcodec or '-'} / {info.acodec or '-'}")
        if info.width and info.height:
            self.info_res_var.set(f"{info.width}x{info.height}")
        else:
            self.info_res_var.set("—")
        self.info_size_var.set(format_bytes(info.size_bytes))
        self.info_container_var.set(info.format_name or "—")

    def pick_watermark(self) -> None:
        path = filedialog.askopenfilename(title="Вибрати водяний знак", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All", "*.*")])
        if path:
            self.wm_path_var.set(path)

    def pick_font(self) -> None:
        path = filedialog.askopenfilename(title="Вибрати шрифт", filetypes=[("Fonts", "*.ttf *.otf"), ("All", "*.*")])
        if path:
            self.text_font_var.set(path)

    def _apply_upscale(self, width: int, height: int) -> None:
        self.resize_w_var.set(str(width))
        self.resize_h_var.set(str(height))
        self._append_log("INFO", f"Покращення: resize {width}x{height}")

    def _collect_settings(self) -> ConversionSettings:
        settings = ConversionSettings()
        settings.out_video_format = self.out_video_fmt_var.get().strip().lower() or "mp4"
        settings.out_image_format = self.out_image_fmt_var.get().strip().lower() or "jpg"
        settings.crf = int(self.crf_var.get())
        settings.preset = self.preset_var.get().strip() or "medium"
        settings.portrait = self.portrait_var.get()
        settings.img_quality = int(self.img_quality_var.get())
        settings.overwrite = bool(self.overwrite_var.get())
        settings.fast_copy = bool(self.fast_copy_var.get())

        settings.trim_start = parse_time_to_seconds(self.trim_start_var.get())
        settings.trim_end = parse_time_to_seconds(self.trim_end_var.get())
        settings.merge = bool(self.merge_var.get())
        settings.merge_name = self.merge_name_var.get().strip() or "merged"

        settings.resize_w = parse_int(self.resize_w_var.get())
        settings.resize_h = parse_int(self.resize_h_var.get())
        settings.crop_w = parse_int(self.crop_w_var.get())
        settings.crop_h = parse_int(self.crop_h_var.get())
        settings.crop_x = parse_int(self.crop_x_var.get())
        settings.crop_y = parse_int(self.crop_y_var.get())
        settings.rotate = self.rotate_var.get()
        speed = parse_float(self.speed_var.get())
        settings.speed = speed if speed and speed > 0 else None

        settings.watermark_path = self.wm_path_var.get().strip()
        settings.watermark_pos = self.wm_pos_var.get()
        settings.watermark_opacity = int(self.wm_opacity_var.get())
        settings.watermark_scale = int(self.wm_scale_var.get())

        settings.text_wm = self.text_wm_var.get().strip()
        settings.text_pos = self.text_pos_var.get()
        settings.text_size = int(self.text_size_var.get())
        settings.text_color = self.text_color_var.get().strip() or "white"
        settings.text_box = bool(self.text_box_var.get())
        settings.text_box_color = self.text_box_color_var.get().strip() or "black"
        settings.text_box_opacity = int(self.text_box_opacity_var.get())
        settings.text_font = self.text_font_var.get().strip()

        settings.video_codec = self.codec_var.get()
        settings.hw_encoder = self.hw_var.get()

        settings.copy_metadata = bool(self.copy_metadata_var.get())
        settings.strip_metadata = bool(self.strip_metadata_var.get())
        settings.meta_title = self.meta_title_var.get().strip()
        settings.meta_comment = self.meta_comment_var.get().strip()
        settings.meta_author = self.meta_author_var.get().strip()
        settings.meta_copyright = self.meta_copyright_var.get().strip()

        self._validate_settings(settings)
        return settings

    def _validate_settings(self, settings: ConversionSettings) -> None:
        if settings.resize_w is None and self.resize_w_var.get().strip():
            self._append_log("WARN", "Некоректний Resize W.")
        if settings.resize_h is None and self.resize_h_var.get().strip():
            self._append_log("WARN", "Некоректний Resize H.")
        if settings.crop_w is None and self.crop_w_var.get().strip():
            self._append_log("WARN", "Некоректний Crop W.")
        if settings.crop_h is None and self.crop_h_var.get().strip():
            self._append_log("WARN", "Некоректний Crop H.")
        if settings.speed is None and self.speed_var.get().strip():
            self._append_log("WARN", "Некоректна швидкість.")
        if settings.watermark_path and not Path(settings.watermark_path).expanduser().exists():
            self._append_log("WARN", "Файл водяного знаку не знайдено.")
        if settings.text_font and not Path(settings.text_font).expanduser().exists():
            self._append_log("WARN", "Файл шрифту не знайдено.")

    def start(self) -> None:
        if self.converter.thread and self.converter.thread.is_alive():
            return
        entry_path = self.ffmpeg_path_var.get().strip()
        if entry_path:
            self.ffmpeg_service.ffmpeg_path = entry_path
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.exe.")
            return
        if not self.tasks:
            messagebox.showinfo("Черга порожня", "Додай файли для конвертації.")
            return

        out_dir = Path(self.output_dir_var.get()).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Помилка", f"Не вдалося створити папку виводу:\n{exc}")
            return

        settings = self._collect_settings()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set("Конвертація запущена...")
        self.converter.start(self.tasks, settings, out_dir)

    def stop(self) -> None:
        self.status_var.set("Зупинка після поточного файлу...")
        self.converter.stop()

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                etype = event[0]
                if etype == "log":
                    _, level, msg = event
                    self._append_log(level, msg)
                elif etype == "status":
                    _, msg = event
                    self.status_var.set(msg)
                elif etype == "progress":
                    _, file_pct, out_time, duration, file_eta, total_pct, total_eta = event
                    self._update_progress(file_pct, out_time, duration, file_eta, total_pct, total_eta)
                elif etype == "set_total":
                    self.file_progress_var.set(0.0)
                    self.total_progress_var.set(0.0)
                elif etype == "file_done":
                    pass
                elif etype == "done":
                    _, stopped = event
                    self._finish(stopped)
                elif etype == "media_info":
                    _, path, info = event
                    self.media_info_cache[path] = info
                    selection = self.queue_listbox.curselection()
                    if selection:
                        idx = selection[0]
                        if idx < len(self.tasks) and self.tasks[idx].path == path:
                            self._update_info(info)
        except queue.Empty:
            pass
        self.after(120, self._poll_events)

    def _update_progress(
        self,
        file_pct: Optional[float],
        out_time: float,
        duration: Optional[float],
        file_eta: Optional[float],
        total_pct: float,
        total_eta: Optional[float],
    ) -> None:
        if file_pct is not None:
            self.file_progress_var.set(file_pct * 100)
            file_text = f"Файл: {int(file_pct * 100):02d}% • {format_time(out_time)} / {format_time(duration)} • ETA {format_time(file_eta)}"
        else:
            self.file_progress_var.set(0.0)
            file_text = "Файл: --"
        self.file_progress_text_var.set(file_text)

        self.total_progress_var.set(total_pct * 100)
        total_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
        self.total_progress_text_var.set(total_text)

    def _finish(self, stopped: bool) -> None:
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set("Зупинено." if stopped else "Готово.")

    def _append_log(self, level: str, msg: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {level}: {msg}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _collect_preset_data(self) -> dict:
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
            "text_box": bool(self.text_box_var.get()),
            "text_box_color": self.text_box_color_var.get(),
            "text_box_opacity": int(self.text_box_opacity_var.get()),
            "text_font": self.text_font_var.get(),
            "codec": self.codec_var.get(),
            "hw": self.hw_var.get(),
            "strip_metadata": bool(self.strip_metadata_var.get()),
            "copy_metadata": bool(self.copy_metadata_var.get()),
            "meta_title": self.meta_title_var.get(),
            "meta_comment": self.meta_comment_var.get(),
            "meta_author": self.meta_author_var.get(),
            "meta_copyright": self.meta_copyright_var.get(),
        }

    def _apply_preset_data(self, data: dict) -> None:
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
        self.rotate_var.set(data.get("rotate", ROTATE_OPTIONS[0]))
        self.speed_var.set(data.get("speed", "1.0"))
        self.wm_path_var.set(data.get("wm_path", ""))
        self.wm_pos_var.set(data.get("wm_pos", POSITION_OPTIONS[3]))
        self.wm_opacity_var.set(data.get("wm_opacity", 80))
        self.wm_scale_var.set(data.get("wm_scale", 30))
        self.text_wm_var.set(data.get("text_wm", ""))
        self.text_pos_var.set(data.get("text_pos", POSITION_OPTIONS[3]))
        self.text_size_var.set(data.get("text_size", 24))
        self.text_color_var.set(data.get("text_color", "white"))
        self.text_box_var.set(data.get("text_box", False))
        self.text_box_color_var.set(data.get("text_box_color", "black"))
        self.text_box_opacity_var.set(data.get("text_box_opacity", 50))
        self.text_font_var.set(data.get("text_font", ""))
        self.codec_var.set(data.get("codec", VIDEO_CODEC_OPTIONS[0]))
        self.hw_var.set(data.get("hw", HW_ENCODER_OPTIONS[0]))
        self.strip_metadata_var.set(data.get("strip_metadata", False))
        self.copy_metadata_var.set(data.get("copy_metadata", False))
        self.meta_title_var.set(data.get("meta_title", ""))
        self.meta_comment_var.set(data.get("meta_comment", ""))
        self.meta_author_var.set(data.get("meta_author", ""))
        self.meta_copyright_var.set(data.get("meta_copyright", ""))

    def _refresh_presets(self) -> None:
        names = sorted(self.presets.keys())
        self.preset_combo.configure(values=names)
        if names and self.preset_select_var.get() not in names:
            self.preset_select_var.set(names[0])

    def save_preset(self) -> None:
        name = self.preset_name_var.get().strip()
        if not name:
            messagebox.showerror("Пресети", "Введи назву пресету.")
            return
        if name in self.presets:
            if not messagebox.askyesno("Пресети", "Пресет уже існує. Перезаписати?"):
                return
        self.presets[name] = self._collect_preset_data()
        save_presets(PRESET_STORE, self.presets)
        self._refresh_presets()
        self.preset_select_var.set(name)
        self._append_log("OK", f"Пресет збережено: {name}")

    def load_preset(self) -> None:
        name = self.preset_select_var.get().strip()
        if not name:
            return
        data = self.presets.get(name)
        if not data:
            return
        self._apply_preset_data(data)
        self._append_log("OK", f"Пресет завантажено: {name}")

    def delete_preset(self) -> None:
        name = self.preset_select_var.get().strip()
        if not name:
            return
        if not messagebox.askyesno("Пресети", f"Видалити пресет '{name}'?"):
            return
        if name in self.presets:
            del self.presets[name]
            save_presets(PRESET_STORE, self.presets)
            self._refresh_presets()
            self._append_log("OK", f"Пресет видалено: {name}")


__all__ = ["MediaConverterApp"]
