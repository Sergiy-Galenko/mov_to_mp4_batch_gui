import os
import queue
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from config.constants import (
    APP_TITLE,
    DEFAULT_OUTPUT_DIR,
    OUT_IMAGE_FORMATS,
    OUT_VIDEO_FORMATS,
    POSITION_OPTIONS,
    PORTRAIT_PRESETS,
    ROTATE_OPTIONS,
    VIDEO_CODEC_OPTIONS,
    HW_ENCODER_OPTIONS,
    PRESET_STORE,
)
from config.paths import find_ffmpeg, find_ffprobe
from core.models import ConversionSettings, MediaInfo, TaskItem
from core.presets import load_presets, save_presets
from services.ffmpeg_service import FfmpegService
from services.converter_service import ConverterService
from utils.files import media_type
from utils.formatting import format_bytes, format_time, parse_float, parse_int, parse_time_to_seconds

SPACE_1 = 8
SPACE_2 = 16
SPACE_3 = 24
SPACE_4 = 32
CONTENT_MAX_WIDTH = 1160
COMPACT_BREAKPOINT = 980

ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
BG = "#0B1220"
PANEL = "#0F172A"
BORDER = "#1E293B"
TEXT = "#E2E8F0"
MUTED = "#94A3B8"
SECTION_BG = "#0B1324"
NAV_BG = "#0B1324"
INPUT_BG = "#0B1324"
HOVER_BG = "#1E293B"
DISABLED_BG = "#1F2937"
DISABLED_TEXT = "#64748B"


def _set_button_variant(button: QtWidgets.QPushButton, variant: str) -> None:
    button.setProperty("variant", variant)
    button.setCursor(QtCore.Qt.PointingHandCursor)


class Card(QtWidgets.QFrame):
    def __init__(self, title: str = "", header_right: Optional[QtWidgets.QWidget] = None):
        super().__init__()
        self.setProperty("card", True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        if title:
            header = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(title)
            label.setProperty("cardTitle", True)
            header.addWidget(label)
            header.addStretch(1)
            if header_right is not None:
                header.addWidget(header_right)
            layout.addLayout(header)

        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(SPACE_2)
        layout.addLayout(self.body)


class Section(QtWidgets.QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setProperty("section", True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(SPACE_2, SPACE_2, SPACE_2, SPACE_2)
        layout.setSpacing(SPACE_1)
        label = QtWidgets.QLabel(title)
        label.setProperty("sectionTitle", True)
        layout.addWidget(label)
        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(SPACE_1)
        layout.addLayout(self.body)


def _grid_layout() -> QtWidgets.QGridLayout:
    grid = QtWidgets.QGridLayout()
    grid.setHorizontalSpacing(SPACE_2)
    grid.setVerticalSpacing(SPACE_1)
    return grid


def _form_layout() -> QtWidgets.QFormLayout:
    form = QtWidgets.QFormLayout()
    form.setHorizontalSpacing(SPACE_2)
    form.setVerticalSpacing(SPACE_1)
    form.setLabelAlignment(QtCore.Qt.AlignLeft)
    form.setFormAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    return form


def _wrap_scroll(content: QtWidgets.QWidget) -> QtWidgets.QWidget:
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    scroll.setWidget(content)
    return scroll


class MediaConverterApp(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 820)
        self.setMinimumSize(860, 720)

        self.event_queue: "queue.Queue[tuple]" = queue.Queue()
        self.ffmpeg_service = FfmpegService(find_ffmpeg(), None)
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        self.converter = ConverterService(self.ffmpeg_service, self.event_queue)

        self.tasks: List[TaskItem] = []
        self.media_info_cache: Dict[Path, MediaInfo] = {}
        self.presets: Dict[str, dict] = load_presets(PRESET_STORE)

        self._layout_mode: Optional[str] = None

        self._build_ui()
        self._apply_styles()
        self._refresh_encoders(initial=True)
        self._refresh_presets()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._poll_events)
        self.timer.start()

    def _apply_styles(self) -> None:
        QtWidgets.QApplication.setStyle("Fusion")
        app = QtWidgets.QApplication.instance()
        if app is not None:
            base_font = QtGui.QFont()
            base_font.setFamilies(["Inter", "Segoe UI", "Arial", "Sans Serif"])
            base_font.setPointSize(11)
            app.setFont(base_font)

        qss = """
        QMainWindow {{ background: {BG}; }}
        QLabel {{ color: {TEXT}; }}
        QLabel[role=\"title\"] {{ font-size: 18px; font-weight: 600; }}
        QLabel[role=\"subtitle\"] {{ color: {MUTED}; }}
        QLabel[cardTitle=\"true\"] {{ font-size: 14px; font-weight: 600; }}
        QLabel[sectionTitle=\"true\"] {{ font-weight: 600; color: {TEXT}; }}

        QFrame[card=\"true\"] {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-radius: 16px;
        }}
        QFrame[section=\"true\"] {{
            background: {SECTION_BG};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}

        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            min-height: 32px;
            padding: 6px 10px;
            border-radius: 8px;
            border: 1px solid {BORDER};
            background: {INPUT_BG};
            color: {TEXT};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {ACCENT};
        }}
        QListWidget, QPlainTextEdit {{
            background: {INPUT_BG};
            border: 1px solid {BORDER};
            border-radius: 10px;
            color: {TEXT};
        }}
        QListWidget[nav=\"true\"] {{
            background: {NAV_BG};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 6px;
        }}
        QListWidget[nav=\"true\"]::item {{
            padding: 10px 12px;
            margin: 4px;
            border-radius: 8px;
            color: {TEXT};
        }}
        QListWidget[nav=\"true\"]::item:selected {{
            background: {ACCENT};
            color: #FFFFFF;
        }}

        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget {{
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}

        QPushButton {{
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        QPushButton[variant=\"primary\"] {{
            background: {ACCENT};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton[variant=\"primary\"]:hover {{ background: {ACCENT_HOVER}; }}
        QPushButton[variant=\"secondary\"] {{
            background: {PANEL};
            color: {TEXT};
            border: 1px solid {BORDER};
        }}
        QPushButton[variant=\"secondary\"]:hover {{ background: {HOVER_BG}; }}
        QPushButton[variant=\"ghost\"] {{
            background: transparent;
            color: {ACCENT};
            border: none;
        }}
        QPushButton[variant=\"ghost\"]:hover {{ background: {HOVER_BG}; }}
        QPushButton:disabled {{ background: {DISABLED_BG}; color: {DISABLED_TEXT}; border: none; }}

        QProgressBar {{
            border: 1px solid {BORDER};
            border-radius: 6px;
            text-align: center;
            background: {SECTION_BG};
            height: 12px;
        }}
        QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}
        """
        self.setStyleSheet(
            qss.format(
                BG=BG,
                TEXT=TEXT,
                MUTED=MUTED,
                PANEL=PANEL,
                BORDER=BORDER,
                SECTION_BG=SECTION_BG,
                INPUT_BG=INPUT_BG,
                NAV_BG=NAV_BG,
                ACCENT=ACCENT,
                ACCENT_HOVER=ACCENT_HOVER,
                HOVER_BG=HOVER_BG,
                DISABLED_BG=DISABLED_BG,
                DISABLED_TEXT=DISABLED_TEXT,
            )
        )

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        outer = QtWidgets.QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        self.content_wrapper = QtWidgets.QWidget()
        self.content_wrapper.setMaximumWidth(CONTENT_MAX_WIDTH)
        outer.addWidget(self.content_wrapper, 0)
        outer.addStretch(1)

        self.setCentralWidget(central)

        root = QtWidgets.QVBoxLayout(self.content_wrapper)
        root.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        root.setSpacing(SPACE_3)

        self.header_card = Card()
        header_layout = self.header_card.body

        title = QtWidgets.QLabel(APP_TITLE)
        title.setProperty("role", "title")
        subtitle = QtWidgets.QLabel("Пакетна конвертація відео та фото через FFmpeg.")
        subtitle.setProperty("role", "subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        ffmpeg_row = QtWidgets.QHBoxLayout()
        ffmpeg_label = QtWidgets.QLabel("FFmpeg:")
        self.ffmpeg_path_input = QtWidgets.QLineEdit(self.ffmpeg_service.ffmpeg_path or "")
        self.ffmpeg_path_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.ffmpeg_pick_btn = QtWidgets.QPushButton("Вказати")
        _set_button_variant(self.ffmpeg_pick_btn, "secondary")
        self.ffmpeg_pick_btn.clicked.connect(self.pick_ffmpeg)
        self.ffmpeg_check_btn = QtWidgets.QPushButton("Перевірити")
        _set_button_variant(self.ffmpeg_check_btn, "ghost")
        self.ffmpeg_check_btn.clicked.connect(self._refresh_encoders)

        ffmpeg_row.addWidget(ffmpeg_label)
        ffmpeg_row.addWidget(self.ffmpeg_path_input, 1)
        ffmpeg_row.addWidget(self.ffmpeg_pick_btn)
        ffmpeg_row.addWidget(self.ffmpeg_check_btn)

        header_layout.addLayout(ffmpeg_row)
        root.addWidget(self.header_card)

        self.main_card = Card()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(SPACE_2)

        self.main_grid = QtWidgets.QGridLayout()
        self.main_grid.setContentsMargins(0, 0, 0, 0)
        self.main_grid.setHorizontalSpacing(SPACE_2)
        self.main_grid.setVerticalSpacing(SPACE_2)
        main_layout.addLayout(self.main_grid)
        self.main_card.body.addLayout(main_layout)

        self.sidebar = self._build_sidebar()
        self.content = self._build_content()
        self._set_layout("wide")

        root.addWidget(self.main_card, 1)

        self.status_card = Card()
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(SPACE_2)

        self.status_label = QtWidgets.QLabel("Готово")
        self.file_progress = QtWidgets.QProgressBar()
        self.file_progress.setRange(0, 100)
        self.file_progress_text = QtWidgets.QLabel("Файл: --")
        self.total_progress = QtWidgets.QProgressBar()
        self.total_progress.setRange(0, 100)
        self.total_progress_text = QtWidgets.QLabel("Всього: --")

        status_layout.addWidget(self.status_label, 0)
        status_layout.addWidget(self.file_progress, 1)
        status_layout.addWidget(self.file_progress_text, 0)
        status_layout.addWidget(self.total_progress, 1)
        status_layout.addWidget(self.total_progress_text, 0)

        self.status_card.body.addLayout(status_layout)
        root.addWidget(self.status_card)

    def _set_layout(self, mode: str) -> None:
        if mode == self._layout_mode:
            return
        while self.main_grid.count():
            item = self.main_grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        if mode == "compact":
            self.main_grid.addWidget(self.sidebar, 0, 0)
            self.main_grid.addWidget(self.content, 1, 0)
            self.main_grid.setColumnStretch(0, 1)
            self.main_grid.setRowStretch(0, 0)
            self.main_grid.setRowStretch(1, 1)
        else:
            self.main_grid.addWidget(self.sidebar, 0, 0)
            self.main_grid.addWidget(self.content, 0, 1)
            self.main_grid.setColumnStretch(0, 0)
            self.main_grid.setColumnStretch(1, 1)
            self.main_grid.setRowStretch(0, 1)
        self._layout_mode = mode

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        mode = "compact" if event.size().width() < COMPACT_BREAKPOINT else "wide"
        self._set_layout(mode)
        super().resizeEvent(event)

    def _build_sidebar(self) -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        queue_card = Card("Черга")
        self.queue_list = QtWidgets.QListWidget()
        self.queue_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.queue_list.currentRowChanged.connect(self._show_selected_info)
        queue_card.body.addWidget(self.queue_list)

        queue_actions = QtWidgets.QGridLayout()
        queue_actions.setHorizontalSpacing(SPACE_1)
        queue_actions.setVerticalSpacing(SPACE_1)
        self.add_files_btn = QtWidgets.QPushButton("Додати файли")
        _set_button_variant(self.add_files_btn, "secondary")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn = QtWidgets.QPushButton("Додати папку")
        _set_button_variant(self.add_folder_btn, "secondary")
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.remove_btn = QtWidgets.QPushButton("Видалити вибрані")
        _set_button_variant(self.remove_btn, "ghost")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn = QtWidgets.QPushButton("Очистити")
        _set_button_variant(self.clear_btn, "ghost")
        self.clear_btn.clicked.connect(self.clear_list)

        queue_actions.addWidget(self.add_files_btn, 0, 0)
        queue_actions.addWidget(self.add_folder_btn, 0, 1)
        queue_actions.addWidget(self.remove_btn, 1, 0)
        queue_actions.addWidget(self.clear_btn, 1, 1)
        queue_card.body.addLayout(queue_actions)

        layout.addWidget(queue_card)

        output_card = Card("Вивід")
        self.output_dir_input = QtWidgets.QLineEdit(str(DEFAULT_OUTPUT_DIR))
        self.output_dir_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        output_card.body.addWidget(self.output_dir_input)
        output_actions = QtWidgets.QHBoxLayout()
        self.pick_output_btn = QtWidgets.QPushButton("Вибрати")
        _set_button_variant(self.pick_output_btn, "secondary")
        self.pick_output_btn.clicked.connect(self.pick_output)
        self.open_output_btn = QtWidgets.QPushButton("Відкрити папку")
        _set_button_variant(self.open_output_btn, "ghost")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        output_actions.addWidget(self.pick_output_btn)
        output_actions.addWidget(self.open_output_btn)
        output_actions.addStretch(1)
        output_card.body.addLayout(output_actions)
        layout.addWidget(output_card)

        info_card = Card("Інформація")
        info_form = _form_layout()
        self.info_name = QtWidgets.QLabel("—")
        self.info_duration = QtWidgets.QLabel("--:--")
        self.info_codec = QtWidgets.QLabel("—")
        self.info_res = QtWidgets.QLabel("—")
        self.info_size = QtWidgets.QLabel("—")
        self.info_container = QtWidgets.QLabel("—")
        info_form.addRow("Файл:", self.info_name)
        info_form.addRow("Тривалість:", self.info_duration)
        info_form.addRow("Кодеки:", self.info_codec)
        info_form.addRow("Роздільність:", self.info_res)
        info_form.addRow("Розмір:", self.info_size)
        info_form.addRow("Контейнер:", self.info_container)
        info_widget = QtWidgets.QWidget()
        info_widget.setLayout(info_form)
        info_card.body.addWidget(info_widget)
        layout.addWidget(info_card)

        actions_card = Card("Дії")
        self.start_btn = QtWidgets.QPushButton("Старт")
        _set_button_variant(self.start_btn, "primary")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QtWidgets.QPushButton("Стоп")
        _set_button_variant(self.stop_btn, "secondary")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)
        actions_card.body.addWidget(self.start_btn)
        actions_card.body.addWidget(self.stop_btn)
        layout.addWidget(actions_card)

        layout.addStretch(1)
        return wrapper

    def _build_content(self) -> QtWidgets.QWidget:
        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        settings_card = Card("Налаштування")
        settings_layout = QtWidgets.QHBoxLayout()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(SPACE_2)

        nav = QtWidgets.QListWidget()
        nav.setProperty("nav", True)
        nav.setFixedWidth(180)
        nav.setSpacing(2)
        nav.setFrameShape(QtWidgets.QFrame.NoFrame)
        nav.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        nav.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        nav.setFocusPolicy(QtCore.Qt.NoFocus)

        self.settings_stack = QtWidgets.QStackedWidget()
        self.settings_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        pages = [
            ("Основні", self._build_basic_tab()),
            ("Редагування", self._build_advanced_tab()),
            ("Кодеки", self._build_codec_tab()),
            ("Пресети", self._build_presets_tab()),
            ("Покращення", self._build_enhance_tab()),
            ("Метадані", self._build_metadata_tab()),
        ]
        for label, widget in pages:
            nav.addItem(label)
            self.settings_stack.addWidget(_wrap_scroll(widget))

        nav.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        nav.setCurrentRow(0)

        settings_layout.addWidget(nav, 0)
        settings_layout.addWidget(self.settings_stack, 1)
        settings_card.body.addLayout(settings_layout)

        splitter.addWidget(settings_card)

        log_card = Card("Лог")
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        log_card.body.addWidget(self.log_text)
        splitter.addWidget(log_card)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        return wrapper

    def _build_basic_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        video_section = Section("Відео")
        grid = _grid_layout()
        self.out_video_fmt = QtWidgets.QComboBox()
        self.out_video_fmt.addItems(OUT_VIDEO_FORMATS)
        self.crf_spin = QtWidgets.QSpinBox()
        self.crf_spin.setRange(14, 35)
        self.crf_spin.setValue(23)
        self.encoder_preset = QtWidgets.QComboBox()
        self.encoder_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.portrait_combo = QtWidgets.QComboBox()
        self.portrait_combo.addItems(list(PORTRAIT_PRESETS.keys()))

        grid.addWidget(QtWidgets.QLabel("Формат:"), 0, 0)
        grid.addWidget(self.out_video_fmt, 0, 1)
        grid.addWidget(QtWidgets.QLabel("CRF:"), 0, 2)
        grid.addWidget(self.crf_spin, 0, 3)
        grid.addWidget(QtWidgets.QLabel("Preset:"), 0, 4)
        grid.addWidget(self.encoder_preset, 0, 5)
        grid.addWidget(QtWidgets.QLabel("Портрет:"), 1, 0)
        grid.addWidget(self.portrait_combo, 1, 1, 1, 3)
        video_widget = QtWidgets.QWidget()
        video_widget.setLayout(grid)
        video_section.body.addWidget(video_widget)
        layout.addWidget(video_section)

        image_section = Section("Фото")
        img_grid = _grid_layout()
        self.out_image_fmt = QtWidgets.QComboBox()
        self.out_image_fmt.addItems(OUT_IMAGE_FORMATS)
        self.img_quality_spin = QtWidgets.QSpinBox()
        self.img_quality_spin.setRange(1, 100)
        self.img_quality_spin.setValue(90)
        img_grid.addWidget(QtWidgets.QLabel("Формат:"), 0, 0)
        img_grid.addWidget(self.out_image_fmt, 0, 1)
        img_grid.addWidget(QtWidgets.QLabel("Якість (1–100):"), 0, 2)
        img_grid.addWidget(self.img_quality_spin, 0, 3)
        img_widget = QtWidgets.QWidget()
        img_widget.setLayout(img_grid)
        image_section.body.addWidget(img_widget)
        layout.addWidget(image_section)

        behavior_section = Section("Поведінка")
        self.overwrite_check = QtWidgets.QCheckBox("Перезаписувати існуючі файли")
        self.fast_copy_check = QtWidgets.QCheckBox("Fast copy (без перекодування, якщо можливо)")
        behavior_section.body.addWidget(self.overwrite_check)
        behavior_section.body.addWidget(self.fast_copy_check)
        layout.addWidget(behavior_section)

        layout.addStretch(1)
        return page

    def _build_advanced_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        time_section = Section("Час / Merge")
        time_grid = _grid_layout()
        self.trim_start_input = QtWidgets.QLineEdit()
        self.trim_end_input = QtWidgets.QLineEdit()
        self.merge_check = QtWidgets.QCheckBox("Об'єднати всі відео в один файл")
        self.merge_name_input = QtWidgets.QLineEdit("merged")
        time_grid.addWidget(QtWidgets.QLabel("Початок (hh:mm:ss або сек):"), 0, 0)
        time_grid.addWidget(self.trim_start_input, 0, 1)
        time_grid.addWidget(QtWidgets.QLabel("Кінець (hh:mm:ss або сек):"), 0, 2)
        time_grid.addWidget(self.trim_end_input, 0, 3)
        time_grid.addWidget(self.merge_check, 1, 0, 1, 2)
        time_grid.addWidget(QtWidgets.QLabel("Назва файлу:"), 1, 2)
        time_grid.addWidget(self.merge_name_input, 1, 3)
        time_widget = QtWidgets.QWidget()
        time_widget.setLayout(time_grid)
        time_section.body.addWidget(time_widget)
        layout.addWidget(time_section)

        transform_section = Section("Трансформації")
        transform_grid = _grid_layout()
        self.resize_w_input = QtWidgets.QLineEdit()
        self.resize_h_input = QtWidgets.QLineEdit()
        self.crop_w_input = QtWidgets.QLineEdit()
        self.crop_h_input = QtWidgets.QLineEdit()
        self.crop_x_input = QtWidgets.QLineEdit()
        self.crop_y_input = QtWidgets.QLineEdit()
        self.rotate_combo = QtWidgets.QComboBox()
        self.rotate_combo.addItems(ROTATE_OPTIONS)
        self.speed_input = QtWidgets.QLineEdit("1.0")

        transform_grid.addWidget(QtWidgets.QLabel("Resize W:"), 0, 0)
        transform_grid.addWidget(self.resize_w_input, 0, 1)
        transform_grid.addWidget(QtWidgets.QLabel("H:"), 0, 2)
        transform_grid.addWidget(self.resize_h_input, 0, 3)
        transform_grid.addWidget(QtWidgets.QLabel("Crop W:"), 1, 0)
        transform_grid.addWidget(self.crop_w_input, 1, 1)
        transform_grid.addWidget(QtWidgets.QLabel("H:"), 1, 2)
        transform_grid.addWidget(self.crop_h_input, 1, 3)
        transform_grid.addWidget(QtWidgets.QLabel("X:"), 1, 4)
        transform_grid.addWidget(self.crop_x_input, 1, 5)
        transform_grid.addWidget(QtWidgets.QLabel("Y:"), 1, 6)
        transform_grid.addWidget(self.crop_y_input, 1, 7)
        transform_grid.addWidget(QtWidgets.QLabel("Поворот:"), 2, 0)
        transform_grid.addWidget(self.rotate_combo, 2, 1)
        transform_grid.addWidget(QtWidgets.QLabel("Speed:"), 2, 2)
        transform_grid.addWidget(self.speed_input, 2, 3)
        transform_widget = QtWidgets.QWidget()
        transform_widget.setLayout(transform_grid)
        transform_section.body.addWidget(transform_widget)
        layout.addWidget(transform_section)

        wm_section = Section("Водяний знак")
        wm_grid = _grid_layout()
        self.wm_path_input = QtWidgets.QLineEdit()
        self.wm_pick_btn = QtWidgets.QPushButton("Вибрати")
        _set_button_variant(self.wm_pick_btn, "secondary")
        self.wm_pick_btn.clicked.connect(self.pick_watermark)
        self.wm_scale_spin = QtWidgets.QSpinBox()
        self.wm_scale_spin.setRange(1, 200)
        self.wm_scale_spin.setValue(30)
        self.wm_opacity_spin = QtWidgets.QSpinBox()
        self.wm_opacity_spin.setRange(0, 100)
        self.wm_opacity_spin.setValue(80)
        self.wm_pos_combo = QtWidgets.QComboBox()
        self.wm_pos_combo.addItems(POSITION_OPTIONS)

        wm_grid.addWidget(QtWidgets.QLabel("Файл:"), 0, 0)
        wm_grid.addWidget(self.wm_path_input, 0, 1, 1, 3)
        wm_grid.addWidget(self.wm_pick_btn, 0, 4)
        wm_grid.addWidget(QtWidgets.QLabel("Scale %:"), 1, 0)
        wm_grid.addWidget(self.wm_scale_spin, 1, 1)
        wm_grid.addWidget(QtWidgets.QLabel("Opacity %:"), 1, 2)
        wm_grid.addWidget(self.wm_opacity_spin, 1, 3)
        wm_grid.addWidget(QtWidgets.QLabel("Позиція:"), 1, 4)
        wm_grid.addWidget(self.wm_pos_combo, 1, 5)
        wm_widget = QtWidgets.QWidget()
        wm_widget.setLayout(wm_grid)
        wm_section.body.addWidget(wm_widget)
        layout.addWidget(wm_section)

        text_section = Section("Текст")
        text_grid = _grid_layout()
        self.text_wm_input = QtWidgets.QLineEdit()
        self.text_size_spin = QtWidgets.QSpinBox()
        self.text_size_spin.setRange(8, 120)
        self.text_size_spin.setValue(24)
        self.text_color_input = QtWidgets.QLineEdit("white")
        self.text_color_btn = QtWidgets.QPushButton("…")
        _set_button_variant(self.text_color_btn, "ghost")
        self.text_color_btn.clicked.connect(lambda: self._pick_color(self.text_color_input))
        self.text_pos_combo = QtWidgets.QComboBox()
        self.text_pos_combo.addItems(POSITION_OPTIONS)
        self.text_font_input = QtWidgets.QLineEdit()
        self.text_font_btn = QtWidgets.QPushButton("Вибрати")
        _set_button_variant(self.text_font_btn, "secondary")
        self.text_font_btn.clicked.connect(self.pick_font)
        self.text_box_check = QtWidgets.QCheckBox("Фон тексту")
        self.text_box_color_input = QtWidgets.QLineEdit("black")
        self.text_box_color_btn = QtWidgets.QPushButton("…")
        _set_button_variant(self.text_box_color_btn, "ghost")
        self.text_box_color_btn.clicked.connect(lambda: self._pick_color(self.text_box_color_input))
        self.text_box_opacity_spin = QtWidgets.QSpinBox()
        self.text_box_opacity_spin.setRange(0, 100)
        self.text_box_opacity_spin.setValue(50)

        text_grid.addWidget(QtWidgets.QLabel("Текст:"), 0, 0)
        text_grid.addWidget(self.text_wm_input, 0, 1, 1, 3)
        text_grid.addWidget(QtWidgets.QLabel("Розмір:"), 0, 4)
        text_grid.addWidget(self.text_size_spin, 0, 5)
        text_grid.addWidget(QtWidgets.QLabel("Колір:"), 0, 6)
        text_grid.addWidget(self.text_color_input, 0, 7)
        text_grid.addWidget(self.text_color_btn, 0, 8)
        text_grid.addWidget(QtWidgets.QLabel("Позиція:"), 1, 0)
        text_grid.addWidget(self.text_pos_combo, 1, 1)
        text_grid.addWidget(QtWidgets.QLabel("Шрифт (.ttf):"), 1, 2)
        text_grid.addWidget(self.text_font_input, 1, 3, 1, 3)
        text_grid.addWidget(self.text_font_btn, 1, 6)
        text_grid.addWidget(self.text_box_check, 2, 0)
        text_grid.addWidget(QtWidgets.QLabel("Колір:"), 2, 1)
        text_grid.addWidget(self.text_box_color_input, 2, 2)
        text_grid.addWidget(self.text_box_color_btn, 2, 3)
        text_grid.addWidget(QtWidgets.QLabel("Opacity %:"), 2, 4)
        text_grid.addWidget(self.text_box_opacity_spin, 2, 5)
        text_widget = QtWidgets.QWidget()
        text_widget.setLayout(text_grid)
        text_section.body.addWidget(text_widget)
        layout.addWidget(text_section)

        layout.addStretch(1)
        return page

    def _build_codec_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        section = Section("Кодеки та GPU")
        grid = _grid_layout()
        self.codec_combo = QtWidgets.QComboBox()
        self.codec_combo.addItems(VIDEO_CODEC_OPTIONS)
        self.hw_combo = QtWidgets.QComboBox()
        self.hw_combo.addItems(HW_ENCODER_OPTIONS)
        self.encoder_info_label = QtWidgets.QLabel("Доступні: --")
        self.encoder_info_label.setProperty("role", "subtitle")

        grid.addWidget(QtWidgets.QLabel("Кодек відео:"), 0, 0)
        grid.addWidget(self.codec_combo, 0, 1)
        grid.addWidget(QtWidgets.QLabel("GPU/CPU:"), 1, 0)
        grid.addWidget(self.hw_combo, 1, 1)
        grid.addWidget(self.encoder_info_label, 2, 0, 1, 2)
        grid_widget = QtWidgets.QWidget()
        grid_widget.setLayout(grid)
        section.body.addWidget(grid_widget)
        layout.addWidget(section)

        layout.addStretch(1)
        return page

    def _build_presets_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        section = Section("Пресети")
        grid = _grid_layout()
        self.saved_presets_combo = QtWidgets.QComboBox()
        self.load_preset_btn = QtWidgets.QPushButton("Завантажити")
        _set_button_variant(self.load_preset_btn, "secondary")
        self.load_preset_btn.clicked.connect(self.load_preset)
        self.delete_preset_btn = QtWidgets.QPushButton("Видалити")
        _set_button_variant(self.delete_preset_btn, "ghost")
        self.delete_preset_btn.clicked.connect(self.delete_preset)
        self.new_preset_input = QtWidgets.QLineEdit()
        self.save_preset_btn = QtWidgets.QPushButton("Зберегти")
        _set_button_variant(self.save_preset_btn, "primary")
        self.save_preset_btn.clicked.connect(self.save_preset)

        grid.addWidget(QtWidgets.QLabel("Збережені:"), 0, 0)
        grid.addWidget(self.saved_presets_combo, 0, 1)
        grid.addWidget(self.load_preset_btn, 0, 2)
        grid.addWidget(self.delete_preset_btn, 0, 3)
        grid.addWidget(QtWidgets.QLabel("Назва нового:"), 1, 0)
        grid.addWidget(self.new_preset_input, 1, 1)
        grid.addWidget(self.save_preset_btn, 1, 2)
        grid_widget = QtWidgets.QWidget()
        grid_widget.setLayout(grid)
        section.body.addWidget(grid_widget)
        layout.addWidget(section)

        layout.addStretch(1)
        return page

    def _build_enhance_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        section = Section("Покращення")
        grid = _grid_layout()
        grid.addWidget(QtWidgets.QLabel("Обери цільову роздільність для upscale:"), 0, 0, 1, 3)
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
            btn = QtWidgets.QPushButton(f"До {label}")
            _set_button_variant(btn, "secondary")
            btn.clicked.connect(lambda _checked=False, ww=w, hh=h: self._apply_upscale(ww, hh))
            grid.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        grid_widget = QtWidgets.QWidget()
        grid_widget.setLayout(grid)
        section.body.addWidget(grid_widget)

        hint = QtWidgets.QLabel(
            "Порада: апскейл збільшує розмір/час. Використовуй адекватні параметри CRF і кодеки (H.265/AV1)."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "subtitle")
        section.body.addWidget(hint)

        layout.addWidget(section)
        layout.addStretch(1)
        return page

    def _build_metadata_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        section = Section("Метадані")
        self.copy_metadata_check = QtWidgets.QCheckBox("Копіювати метадані з джерела")
        self.copy_metadata_check.setChecked(True)
        self.strip_metadata_check = QtWidgets.QCheckBox("Очистити метадані")
        section.body.addWidget(self.copy_metadata_check)
        section.body.addWidget(self.strip_metadata_check)

        form = _form_layout()
        self.meta_title_input = QtWidgets.QLineEdit()
        self.meta_author_input = QtWidgets.QLineEdit()
        self.meta_comment_input = QtWidgets.QLineEdit()
        self.meta_copyright_input = QtWidgets.QLineEdit()
        form.addRow("Title:", self.meta_title_input)
        form.addRow("Author:", self.meta_author_input)
        form.addRow("Comment:", self.meta_comment_input)
        form.addRow("Copyright:", self.meta_copyright_input)
        form_widget = QtWidgets.QWidget()
        form_widget.setLayout(form)
        section.body.addWidget(form_widget)

        layout.addWidget(section)
        layout.addStretch(1)
        return page

    def _pick_color(self, target: QtWidgets.QLineEdit) -> None:
        color = QtWidgets.QColorDialog.getColor(parent=self)
        if color.isValid():
            target.setText(color.name())

    def _append_log(self, level: str, msg: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"[{timestamp}] {level}: {msg}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def _apply_upscale(self, width: int, height: int) -> None:
        self.resize_w_input.setText(str(width))
        self.resize_h_input.setText(str(height))
        self._append_log("INFO", f"Покращення: resize {width}x{height}")

    def _refresh_encoders(self, initial: bool = False) -> None:
        ffmpeg_path = self.ffmpeg_path_input.text().strip()
        if ffmpeg_path:
            self.ffmpeg_service.ffmpeg_path = ffmpeg_path
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            if initial:
                self._append_log("ERROR", "FFmpeg не знайдено. Вкажи ffmpeg або додай у PATH.")
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
        self.encoder_info_label.setText(f"Доступні: {', '.join(summary) if summary else 'немає'}")
        if initial:
            self._append_log("OK", f"FFmpeg знайдено: {self.ffmpeg_service.ffmpeg_path}")
            if self.ffmpeg_service.ffprobe_path:
                self._append_log("OK", f"FFprobe знайдено: {self.ffmpeg_service.ffprobe_path}")
            else:
                self._append_log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")

    def _refresh_presets(self) -> None:
        names = sorted(self.presets.keys())
        self.saved_presets_combo.clear()
        self.saved_presets_combo.addItems(names)
        if names:
            self.saved_presets_combo.setCurrentIndex(0)

    def _collect_settings(self) -> ConversionSettings:
        settings = ConversionSettings()
        settings.out_video_format = self.out_video_fmt.currentText().strip().lower() or "mp4"
        settings.out_image_format = self.out_image_fmt.currentText().strip().lower() or "jpg"
        settings.crf = int(self.crf_spin.value())
        settings.preset = self.encoder_preset.currentText().strip() or "medium"
        settings.portrait = self.portrait_combo.currentText()
        settings.img_quality = int(self.img_quality_spin.value())
        settings.overwrite = bool(self.overwrite_check.isChecked())
        settings.fast_copy = bool(self.fast_copy_check.isChecked())

        settings.trim_start = parse_time_to_seconds(self.trim_start_input.text())
        settings.trim_end = parse_time_to_seconds(self.trim_end_input.text())
        settings.merge = bool(self.merge_check.isChecked())
        settings.merge_name = self.merge_name_input.text().strip() or "merged"

        settings.resize_w = parse_int(self.resize_w_input.text())
        settings.resize_h = parse_int(self.resize_h_input.text())
        settings.crop_w = parse_int(self.crop_w_input.text())
        settings.crop_h = parse_int(self.crop_h_input.text())
        settings.crop_x = parse_int(self.crop_x_input.text())
        settings.crop_y = parse_int(self.crop_y_input.text())
        settings.rotate = self.rotate_combo.currentText()
        speed = parse_float(self.speed_input.text())
        settings.speed = speed if speed and speed > 0 else None

        settings.watermark_path = self.wm_path_input.text().strip()
        settings.watermark_pos = self.wm_pos_combo.currentText()
        settings.watermark_opacity = int(self.wm_opacity_spin.value())
        settings.watermark_scale = int(self.wm_scale_spin.value())

        settings.text_wm = self.text_wm_input.text().strip()
        settings.text_pos = self.text_pos_combo.currentText()
        settings.text_size = int(self.text_size_spin.value())
        settings.text_color = self.text_color_input.text().strip() or "white"
        settings.text_box = bool(self.text_box_check.isChecked())
        settings.text_box_color = self.text_box_color_input.text().strip() or "black"
        settings.text_box_opacity = int(self.text_box_opacity_spin.value())
        settings.text_font = self.text_font_input.text().strip()

        settings.video_codec = self.codec_combo.currentText()
        settings.hw_encoder = self.hw_combo.currentText()

        settings.copy_metadata = bool(self.copy_metadata_check.isChecked())
        settings.strip_metadata = bool(self.strip_metadata_check.isChecked())
        settings.meta_title = self.meta_title_input.text().strip()
        settings.meta_comment = self.meta_comment_input.text().strip()
        settings.meta_author = self.meta_author_input.text().strip()
        settings.meta_copyright = self.meta_copyright_input.text().strip()

        self._validate_settings(settings)
        return settings

    def _validate_settings(self, settings: ConversionSettings) -> None:
        if settings.resize_w is None and self.resize_w_input.text().strip():
            self._append_log("WARN", "Некоректний Resize W.")
        if settings.resize_h is None and self.resize_h_input.text().strip():
            self._append_log("WARN", "Некоректний Resize H.")
        if settings.crop_w is None and self.crop_w_input.text().strip():
            self._append_log("WARN", "Некоректний Crop W.")
        if settings.crop_h is None and self.crop_h_input.text().strip():
            self._append_log("WARN", "Некоректний Crop H.")
        if settings.speed is None and self.speed_input.text().strip():
            self._append_log("WARN", "Некоректна швидкість.")
        if settings.watermark_path and not Path(settings.watermark_path).expanduser().exists():
            self._append_log("WARN", "Файл водяного знаку не знайдено.")
        if settings.text_font and not Path(settings.text_font).expanduser().exists():
            self._append_log("WARN", "Файл шрифту не знайдено.")

    def _collect_preset_data(self) -> dict:
        return {
            "out_video_fmt": self.out_video_fmt.currentText(),
            "out_image_fmt": self.out_image_fmt.currentText(),
            "crf": int(self.crf_spin.value()),
            "preset": self.encoder_preset.currentText(),
            "portrait": self.portrait_combo.currentText(),
            "img_quality": int(self.img_quality_spin.value()),
            "overwrite": bool(self.overwrite_check.isChecked()),
            "fast_copy": bool(self.fast_copy_check.isChecked()),
            "trim_start": self.trim_start_input.text(),
            "trim_end": self.trim_end_input.text(),
            "merge": bool(self.merge_check.isChecked()),
            "merge_name": self.merge_name_input.text(),
            "resize_w": self.resize_w_input.text(),
            "resize_h": self.resize_h_input.text(),
            "crop_w": self.crop_w_input.text(),
            "crop_h": self.crop_h_input.text(),
            "crop_x": self.crop_x_input.text(),
            "crop_y": self.crop_y_input.text(),
            "rotate": self.rotate_combo.currentText(),
            "speed": self.speed_input.text(),
            "wm_path": self.wm_path_input.text(),
            "wm_pos": self.wm_pos_combo.currentText(),
            "wm_opacity": int(self.wm_opacity_spin.value()),
            "wm_scale": int(self.wm_scale_spin.value()),
            "text_wm": self.text_wm_input.text(),
            "text_pos": self.text_pos_combo.currentText(),
            "text_size": int(self.text_size_spin.value()),
            "text_color": self.text_color_input.text(),
            "text_box": bool(self.text_box_check.isChecked()),
            "text_box_color": self.text_box_color_input.text(),
            "text_box_opacity": int(self.text_box_opacity_spin.value()),
            "text_font": self.text_font_input.text(),
            "codec": self.codec_combo.currentText(),
            "hw": self.hw_combo.currentText(),
            "strip_metadata": bool(self.strip_metadata_check.isChecked()),
            "copy_metadata": bool(self.copy_metadata_check.isChecked()),
            "meta_title": self.meta_title_input.text(),
            "meta_comment": self.meta_comment_input.text(),
            "meta_author": self.meta_author_input.text(),
            "meta_copyright": self.meta_copyright_input.text(),
        }

    def _apply_preset_data(self, data: dict) -> None:
        self.out_video_fmt.setCurrentText(data.get("out_video_fmt", "mp4"))
        self.out_image_fmt.setCurrentText(data.get("out_image_fmt", "jpg"))
        self.crf_spin.setValue(int(data.get("crf", 23)))
        self.encoder_preset.setCurrentText(data.get("preset", "medium"))
        self.portrait_combo.setCurrentText(data.get("portrait", "Вимкнено"))
        self.img_quality_spin.setValue(int(data.get("img_quality", 90)))
        self.overwrite_check.setChecked(bool(data.get("overwrite", False)))
        self.fast_copy_check.setChecked(bool(data.get("fast_copy", False)))
        self.trim_start_input.setText(data.get("trim_start", ""))
        self.trim_end_input.setText(data.get("trim_end", ""))
        self.merge_check.setChecked(bool(data.get("merge", False)))
        self.merge_name_input.setText(data.get("merge_name", "merged"))
        self.resize_w_input.setText(data.get("resize_w", ""))
        self.resize_h_input.setText(data.get("resize_h", ""))
        self.crop_w_input.setText(data.get("crop_w", ""))
        self.crop_h_input.setText(data.get("crop_h", ""))
        self.crop_x_input.setText(data.get("crop_x", ""))
        self.crop_y_input.setText(data.get("crop_y", ""))
        self.rotate_combo.setCurrentText(data.get("rotate", ROTATE_OPTIONS[0]))
        self.speed_input.setText(data.get("speed", "1.0"))
        self.wm_path_input.setText(data.get("wm_path", ""))
        self.wm_pos_combo.setCurrentText(data.get("wm_pos", POSITION_OPTIONS[3]))
        self.wm_opacity_spin.setValue(int(data.get("wm_opacity", 80)))
        self.wm_scale_spin.setValue(int(data.get("wm_scale", 30)))
        self.text_wm_input.setText(data.get("text_wm", ""))
        self.text_pos_combo.setCurrentText(data.get("text_pos", POSITION_OPTIONS[3]))
        self.text_size_spin.setValue(int(data.get("text_size", 24)))
        self.text_color_input.setText(data.get("text_color", "white"))
        self.text_box_check.setChecked(bool(data.get("text_box", False)))
        self.text_box_color_input.setText(data.get("text_box_color", "black"))
        self.text_box_opacity_spin.setValue(int(data.get("text_box_opacity", 50)))
        self.text_font_input.setText(data.get("text_font", ""))
        self.codec_combo.setCurrentText(data.get("codec", VIDEO_CODEC_OPTIONS[0]))
        self.hw_combo.setCurrentText(data.get("hw", HW_ENCODER_OPTIONS[0]))
        self.strip_metadata_check.setChecked(bool(data.get("strip_metadata", False)))
        self.copy_metadata_check.setChecked(bool(data.get("copy_metadata", False)))
        self.meta_title_input.setText(data.get("meta_title", ""))
        self.meta_comment_input.setText(data.get("meta_comment", ""))
        self.meta_author_input.setText(data.get("meta_author", ""))
        self.meta_copyright_input.setText(data.get("meta_copyright", ""))

    def save_preset(self) -> None:
        name = self.new_preset_input.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Пресети", "Введи назву пресету.")
            return
        if name in self.presets:
            if QtWidgets.QMessageBox.question(self, "Пресети", "Пресет уже існує. Перезаписати?") != QtWidgets.QMessageBox.Yes:
                return
        self.presets[name] = self._collect_preset_data()
        save_presets(PRESET_STORE, self.presets)
        self._refresh_presets()
        self.saved_presets_combo.setCurrentText(name)
        self._append_log("OK", f"Пресет збережено: {name}")

    def load_preset(self) -> None:
        name = self.saved_presets_combo.currentText().strip()
        if not name:
            return
        data = self.presets.get(name)
        if not data:
            return
        self._apply_preset_data(data)
        self._append_log("OK", f"Пресет завантажено: {name}")

    def delete_preset(self) -> None:
        name = self.saved_presets_combo.currentText().strip()
        if not name:
            return
        if QtWidgets.QMessageBox.question(self, "Пресети", f"Видалити пресет '{name}'?") != QtWidgets.QMessageBox.Yes:
            return
        if name in self.presets:
            del self.presets[name]
            save_presets(PRESET_STORE, self.presets)
            self._refresh_presets()
            self._append_log("OK", f"Пресет видалено: {name}")

    def pick_ffmpeg(self) -> None:
        filt = "FFmpeg (ffmpeg.exe)" if os.name == "nt" else "FFmpeg (ffmpeg)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Вкажи ffmpeg", "", f"{filt};;All Files (*)")
        if path:
            self.ffmpeg_path_input.setText(path)
            self._refresh_encoders()

    def pick_output(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Папка виводу", self.output_dir_input.text())
        if folder:
            self.output_dir_input.setText(folder)

    def open_output_folder(self) -> None:
        folder = Path(self.output_dir_input.text()).expanduser()
        if not folder.exists():
            QtWidgets.QMessageBox.critical(self, "Папка", "Папка виводу не існує.")
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    def add_files(self) -> None:
        filt = "Media Files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts *.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif);;All Files (*)"
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Додати файли", "", filt)
        self._add_paths([Path(p) for p in files])

    def add_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Додати папку")
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
            self.queue_list.addItem(f"{path.name}  [{mtype}]")
            added += 1
        if added:
            self._append_log("OK", f"Додано файлів: {added}")
        else:
            self._append_log("WARN", "Не знайдено підтримуваних файлів.")

    def remove_selected(self) -> None:
        rows = sorted([item.row() for item in self.queue_list.selectedIndexes()], reverse=True)
        if not rows:
            return
        for idx in rows:
            self.queue_list.takeItem(idx)
            del self.tasks[idx]
        self._append_log("INFO", f"Видалено: {len(rows)}")
        self._clear_info()

    def clear_list(self) -> None:
        self.queue_list.clear()
        self.tasks.clear()
        self._append_log("INFO", "Чергу очищено")
        self._clear_info()

    def _clear_info(self) -> None:
        self.info_name.setText("—")
        self.info_duration.setText("--:--")
        self.info_codec.setText("—")
        self.info_res.setText("—")
        self.info_size.setText("—")
        self.info_container.setText("—")

    def _show_selected_info(self) -> None:
        idx = self.queue_list.currentRow()
        if idx < 0 or idx >= len(self.tasks):
            self._clear_info()
            return
        task = self.tasks[idx]
        self.info_name.setText(task.path.name)
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
        self.info_duration.setText(format_time(info.duration))
        self.info_codec.setText(f"{info.vcodec or '-'} / {info.acodec or '-'}")
        self.info_res.setText(f"{info.width}x{info.height}" if info.width and info.height else "—")
        self.info_size.setText(format_bytes(info.size_bytes))
        self.info_container.setText(info.format_name or "—")

    def pick_watermark(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Вибрати водяний знак", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)")
        if path:
            self.wm_path_input.setText(path)

    def pick_font(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Вибрати шрифт", "", "Fonts (*.ttf *.otf);;All Files (*)")
        if path:
            self.text_font_input.setText(path)

    def start(self) -> None:
        if self.converter.thread and self.converter.thread.is_alive():
            return
        entry_path = self.ffmpeg_path_input.text().strip()
        if entry_path:
            self.ffmpeg_service.ffmpeg_path = entry_path
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            QtWidgets.QMessageBox.critical(self, "FFmpeg", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.")
            return
        if not self.tasks:
            QtWidgets.QMessageBox.information(self, "Черга порожня", "Додай файли для конвертації.")
            return

        out_dir = Path(self.output_dir_input.text()).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Помилка", f"Не вдалося створити папку виводу:\n{exc}")
            return

        settings = self._collect_settings()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Конвертація запущена...")
        self.converter.start(self.tasks, settings, out_dir)

    def stop(self) -> None:
        self.status_label.setText("Зупинка після поточного файлу...")
        self.converter.stop()

    def _finish(self, stopped: bool) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Зупинено." if stopped else "Готово.")

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
                    self.status_label.setText(msg)
                elif etype == "progress":
                    _, file_pct, out_time, duration, file_eta, total_pct, total_eta = event
                    self._update_progress(file_pct, out_time, duration, file_eta, total_pct, total_eta)
                elif etype == "set_total":
                    self.file_progress.setValue(0)
                    self.total_progress.setValue(0)
                elif etype == "done":
                    _, stopped = event
                    self._finish(stopped)
                elif etype == "media_info":
                    _, path, info = event
                    self.media_info_cache[path] = info
                    idx = self.queue_list.currentRow()
                    if idx >= 0 and idx < len(self.tasks) and self.tasks[idx].path == path:
                        self._update_info(info)
        except queue.Empty:
            pass

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
            self.file_progress.setValue(int(file_pct * 100))
            file_text = f"Файл: {int(file_pct * 100):02d}% • {format_time(out_time)} / {format_time(duration)} • ETA {format_time(file_eta)}"
        else:
            self.file_progress.setValue(0)
            file_text = "Файл: --"
        self.file_progress_text.setText(file_text)

        self.total_progress.setValue(int(total_pct * 100))
        total_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
        self.total_progress_text.setText(total_text)


__all__ = ["MediaConverterApp"]
