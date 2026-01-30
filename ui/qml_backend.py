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


class QueueModel(QtCore.QAbstractListModel):
    NameRole = QtCore.Qt.UserRole + 1
    TypeRole = QtCore.Qt.UserRole + 2
    PathRole = QtCore.Qt.UserRole + 3
    DisplayRole = QtCore.Qt.UserRole + 4

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._items: List[TaskItem] = []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == QtCore.Qt.DisplayRole or role == self.DisplayRole:
            return f"{item.path.name}  [{item.media_type}]"
        if role == self.NameRole:
            return item.path.name
        if role == self.TypeRole:
            return item.media_type
        if role == self.PathRole:
            return str(item.path)
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.NameRole: b"name",
            self.TypeRole: b"mediaType",
            self.PathRole: b"path",
            self.DisplayRole: b"display",
        }

    def items(self) -> List[TaskItem]:
        return list(self._items)

    def add_items(self, items: List[TaskItem]) -> None:
        if not items:
            return
        start = len(self._items)
        end = start + len(items) - 1
        self.beginInsertRows(QtCore.QModelIndex(), start, end)
        self._items.extend(items)
        self.endInsertRows()

    def set_items(self, items: List[TaskItem]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()


class Backend(QtCore.QObject):
    logAdded = QtCore.Signal(str, str)
    statusChanged = QtCore.Signal()
    fileProgressChanged = QtCore.Signal()
    totalProgressChanged = QtCore.Signal()
    fileProgressTextChanged = QtCore.Signal()
    totalProgressTextChanged = QtCore.Signal()
    encoderInfoChanged = QtCore.Signal()
    ffmpegPathChanged = QtCore.Signal()
    outputDirChanged = QtCore.Signal()
    infoChanged = QtCore.Signal()
    isRunningChanged = QtCore.Signal()
    presetLoaded = QtCore.Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.event_queue: "queue.Queue[tuple]" = queue.Queue()
        self.ffmpeg_service = FfmpegService(find_ffmpeg(), None)
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        self.converter = ConverterService(self.ffmpeg_service, self.event_queue)

        self.queue_model = QueueModel()
        self.media_info_cache: Dict[Path, MediaInfo] = {}
        self.presets: Dict[str, dict] = load_presets(PRESET_STORE)
        self.presets_model = QtCore.QStringListModel()

        self._ffmpeg_path = self.ffmpeg_service.ffmpeg_path or ""
        self._output_dir = str(DEFAULT_OUTPUT_DIR)
        self._encoder_info = "Доступні: --"
        self._status_text = "Готово"
        self._file_progress = 0.0
        self._total_progress = 0.0
        self._file_progress_text = "Файл: --"
        self._total_progress_text = "Всього: --"
        self._is_running = False

        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"

        self._refresh_presets()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._poll_events)
        self._timer.start()

    @QtCore.Property(str, constant=True)
    def appTitle(self) -> str:
        return APP_TITLE

    @QtCore.Property(QtCore.QObject, constant=True)
    def queueModel(self) -> QtCore.QObject:
        return self.queue_model

    @QtCore.Property(QtCore.QObject, constant=True)
    def presetsModel(self) -> QtCore.QObject:
        return self.presets_model

    @QtCore.Property(str, notify=ffmpegPathChanged)
    def ffmpegPath(self) -> str:
        return self._ffmpeg_path

    @ffmpegPath.setter
    def ffmpegPath(self, value: str) -> None:
        value = value.strip()
        if self._ffmpeg_path == value:
            return
        self._ffmpeg_path = value
        self.ffmpegPathChanged.emit()

    @QtCore.Property(str, notify=outputDirChanged)
    def outputDir(self) -> str:
        return self._output_dir

    @outputDir.setter
    def outputDir(self, value: str) -> None:
        value = value.strip()
        if self._output_dir == value:
            return
        self._output_dir = value
        self.outputDirChanged.emit()

    @QtCore.Property(str, notify=encoderInfoChanged)
    def encoderInfo(self) -> str:
        return self._encoder_info

    @QtCore.Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @QtCore.Property(float, notify=fileProgressChanged)
    def fileProgress(self) -> float:
        return self._file_progress

    @QtCore.Property(float, notify=totalProgressChanged)
    def totalProgress(self) -> float:
        return self._total_progress

    @QtCore.Property(str, notify=fileProgressTextChanged)
    def fileProgressText(self) -> str:
        return self._file_progress_text

    @QtCore.Property(str, notify=totalProgressTextChanged)
    def totalProgressText(self) -> str:
        return self._total_progress_text

    @QtCore.Property(bool, notify=isRunningChanged)
    def isRunning(self) -> bool:
        return self._is_running

    @QtCore.Property(str, notify=infoChanged)
    def infoName(self) -> str:
        return self._info_name

    @QtCore.Property(str, notify=infoChanged)
    def infoDuration(self) -> str:
        return self._info_duration

    @QtCore.Property(str, notify=infoChanged)
    def infoCodec(self) -> str:
        return self._info_codec

    @QtCore.Property(str, notify=infoChanged)
    def infoRes(self) -> str:
        return self._info_res

    @QtCore.Property(str, notify=infoChanged)
    def infoSize(self) -> str:
        return self._info_size

    @QtCore.Property(str, notify=infoChanged)
    def infoContainer(self) -> str:
        return self._info_container

    def _append_log(self, level: str, msg: str) -> None:
        self.logAdded.emit(level, msg)

    def _refresh_presets(self) -> None:
        names = sorted(self.presets.keys())
        self.presets_model.setStringList(names)

    def _set_status(self, text: str) -> None:
        if self._status_text != text:
            self._status_text = text
            self.statusChanged.emit()

    def _set_progress(self, file_pct: float, total_pct: float) -> None:
        if self._file_progress != file_pct:
            self._file_progress = file_pct
            self.fileProgressChanged.emit()
        if self._total_progress != total_pct:
            self._total_progress = total_pct
            self.totalProgressChanged.emit()

    @QtCore.Slot()
    def refreshEncoders(self) -> None:
        ffmpeg_path = self.ffmpegPath
        if ffmpeg_path:
            self.ffmpeg_service.ffmpeg_path = ffmpeg_path
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
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
        info = f"Доступні: {', '.join(summary) if summary else 'немає'}"
        if self._encoder_info != info:
            self._encoder_info = info
            self.encoderInfoChanged.emit()
        self._append_log("OK", f"FFmpeg знайдено: {self.ffmpeg_service.ffmpeg_path}")
        if self.ffmpeg_service.ffprobe_path:
            self._append_log("OK", f"FFprobe знайдено: {self.ffmpeg_service.ffprobe_path}")
        else:
            self._append_log("WARN", "FFprobe не знайдено. Прогрес/ETA можуть бути неточні.")

    @QtCore.Slot()
    def pickFfmpeg(self) -> None:
        filt = "FFmpeg (ffmpeg.exe)" if os.name == "nt" else "FFmpeg (ffmpeg)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вкажи ffmpeg", "", f"{filt};;All Files (*)")
        if path:
            self.ffmpegPath = path
            self.refreshEncoders()

    @QtCore.Slot()
    def pickOutputDir(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Папка виводу", self.outputDir)
        if folder:
            self.outputDir = folder

    @QtCore.Slot()
    def openOutputDir(self) -> None:
        folder = Path(self.outputDir).expanduser()
        if not folder.exists():
            QtWidgets.QMessageBox.critical(None, "Папка", "Папка виводу не існує.")
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    @QtCore.Slot()
    def addFiles(self) -> None:
        filt = "Media Files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts *.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif);;All Files (*)"
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Додати файли", "", filt)
        self._add_paths([Path(p) for p in files])

    @QtCore.Slot()
    def addFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Додати папку")
        if folder:
            base = Path(folder)
            items = [p for p in base.rglob("*") if p.is_file()]
            self._add_paths(items)

    def _add_paths(self, paths: List[Path]) -> None:
        added: List[TaskItem] = []
        for path in paths:
            mtype = media_type(path)
            if not mtype:
                continue
            added.append(TaskItem(path=path, media_type=mtype))
        if added:
            self.queue_model.add_items(added)
            self._append_log("OK", f"Додано файлів: {len(added)}")
        else:
            self._append_log("WARN", "Не знайдено підтримуваних файлів.")

    @QtCore.Slot('QVariantList')
    def removeSelected(self, indices: List[int]) -> None:
        if not indices:
            return
        keep = []
        remove_set = set(indices)
        for idx, item in enumerate(self.queue_model.items()):
            if idx not in remove_set:
                keep.append(item)
        self.queue_model.set_items(keep)
        self._append_log("INFO", f"Видалено: {len(indices)}")
        self._clear_info()

    @QtCore.Slot()
    def clearQueue(self) -> None:
        self.queue_model.set_items([])
        self._append_log("INFO", "Чергу очищено")
        self._clear_info()

    @QtCore.Slot(int)
    def selectQueueIndex(self, index: int) -> None:
        items = self.queue_model.items()
        if index < 0 or index >= len(items):
            self._clear_info()
            return
        task = items[index]
        self._info_name = task.path.name
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self.infoChanged.emit()
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
        self._info_duration = format_time(info.duration)
        self._info_codec = f"{info.vcodec or '-'} / {info.acodec or '-'}"
        self._info_res = f"{info.width}x{info.height}" if info.width and info.height else "—"
        self._info_size = format_bytes(info.size_bytes)
        self._info_container = info.format_name or "—"
        self.infoChanged.emit()

    def _clear_info(self) -> None:
        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self.infoChanged.emit()

    @QtCore.Slot()
    def pickWatermark(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати водяний знак", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)")
        if path:
            self._append_log("INFO", "Водяний знак вибрано")
            self.watermarkPicked.emit(path)

    watermarkPicked = QtCore.Signal(str)

    @QtCore.Slot()
    def pickFont(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати шрифт", "", "Fonts (*.ttf *.otf);;All Files (*)")
        if path:
            self.fontPicked.emit(path)

    fontPicked = QtCore.Signal(str)

    @QtCore.Slot('QVariantMap')
    def startConversion(self, settings_map: dict) -> None:
        if self.converter.thread and self.converter.thread.is_alive():
            return
        entry_path = self.ffmpegPath
        if entry_path:
            self.ffmpeg_service.ffmpeg_path = entry_path
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            QtWidgets.QMessageBox.critical(None, "FFmpeg", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.")
            return
        if not self.queue_model.items():
            QtWidgets.QMessageBox.information(None, "Черга порожня", "Додай файли для конвертації.")
            return

        out_dir = Path(self.outputDir).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, "Помилка", f"Не вдалося створити папку виводу:\n{exc}")
            return

        settings = ConversionSettings()
        settings.out_video_format = (settings_map.get("out_video_fmt") or "mp4").strip().lower()
        settings.out_image_format = (settings_map.get("out_image_fmt") or "jpg").strip().lower()
        settings.crf = int(settings_map.get("crf", 23))
        settings.preset = (settings_map.get("preset") or "medium").strip()
        settings.portrait = settings_map.get("portrait") or "Вимкнено"
        settings.img_quality = int(settings_map.get("img_quality", 90))
        settings.overwrite = bool(settings_map.get("overwrite", False))
        settings.fast_copy = bool(settings_map.get("fast_copy", False))

        settings.trim_start = parse_time_to_seconds(settings_map.get("trim_start", ""))
        settings.trim_end = parse_time_to_seconds(settings_map.get("trim_end", ""))
        settings.merge = bool(settings_map.get("merge", False))
        settings.merge_name = (settings_map.get("merge_name") or "merged").strip()

        settings.resize_w = parse_int(settings_map.get("resize_w", ""))
        settings.resize_h = parse_int(settings_map.get("resize_h", ""))
        settings.crop_w = parse_int(settings_map.get("crop_w", ""))
        settings.crop_h = parse_int(settings_map.get("crop_h", ""))
        settings.crop_x = parse_int(settings_map.get("crop_x", ""))
        settings.crop_y = parse_int(settings_map.get("crop_y", ""))
        settings.rotate = settings_map.get("rotate") or ROTATE_OPTIONS[0]
        speed = parse_float(settings_map.get("speed", ""))
        settings.speed = speed if speed and speed > 0 else None

        settings.watermark_path = settings_map.get("wm_path", "")
        settings.watermark_pos = settings_map.get("wm_pos") or POSITION_OPTIONS[3]
        settings.watermark_opacity = int(settings_map.get("wm_opacity", 80))
        settings.watermark_scale = int(settings_map.get("wm_scale", 30))

        settings.text_wm = settings_map.get("text_wm", "")
        settings.text_pos = settings_map.get("text_pos") or POSITION_OPTIONS[3]
        settings.text_size = int(settings_map.get("text_size", 24))
        settings.text_color = settings_map.get("text_color") or "white"
        settings.text_box = bool(settings_map.get("text_box", False))
        settings.text_box_color = settings_map.get("text_box_color") or "black"
        settings.text_box_opacity = int(settings_map.get("text_box_opacity", 50))
        settings.text_font = settings_map.get("text_font", "")

        settings.video_codec = settings_map.get("codec") or VIDEO_CODEC_OPTIONS[0]
        settings.hw_encoder = settings_map.get("hw") or HW_ENCODER_OPTIONS[0]

        settings.copy_metadata = bool(settings_map.get("copy_metadata", True))
        settings.strip_metadata = bool(settings_map.get("strip_metadata", False))
        settings.meta_title = settings_map.get("meta_title", "")
        settings.meta_comment = settings_map.get("meta_comment", "")
        settings.meta_author = settings_map.get("meta_author", "")
        settings.meta_copyright = settings_map.get("meta_copyright", "")

        self._validate_settings(settings, settings_map)
        self._is_running = True
        self.isRunningChanged.emit()
        self._set_status("Конвертація запущена...")
        self.converter.start(self.queue_model.items(), settings, out_dir)

    @QtCore.Slot()
    def stopConversion(self) -> None:
        self._set_status("Зупинка після поточного файлу...")
        self.converter.stop()

    def _validate_settings(self, settings: ConversionSettings, raw: dict) -> None:
        if str(raw.get("resize_w", "")).strip() and settings.resize_w is None:
            self._append_log("WARN", "Некоректний Resize W.")
        if str(raw.get("resize_h", "")).strip() and settings.resize_h is None:
            self._append_log("WARN", "Некоректний Resize H.")
        if str(raw.get("crop_w", "")).strip() and settings.crop_w is None:
            self._append_log("WARN", "Некоректний Crop W.")
        if str(raw.get("crop_h", "")).strip() and settings.crop_h is None:
            self._append_log("WARN", "Некоректний Crop H.")
        if str(raw.get("speed", "")).strip() and settings.speed is None:
            self._append_log("WARN", "Некоректна швидкість.")
        if settings.watermark_path and not Path(settings.watermark_path).expanduser().exists():
            self._append_log("WARN", "Файл водяного знаку не знайдено.")
        if settings.text_font and not Path(settings.text_font).expanduser().exists():
            self._append_log("WARN", "Файл шрифту не знайдено.")

    @QtCore.Slot(str)
    def loadPreset(self, name: str) -> None:
        data = self.presets.get(name)
        if not data:
            return
        self.presetLoaded.emit(data)
        self._append_log("OK", f"Пресет завантажено: {name}")

    @QtCore.Slot(str, 'QVariantMap')
    def savePreset(self, name: str, settings_map: dict) -> None:
        if not name:
            QtWidgets.QMessageBox.warning(None, "Пресети", "Введи назву пресету.")
            return
        if name in self.presets:
            if QtWidgets.QMessageBox.question(None, "Пресети", "Пресет уже існує. Перезаписати?") != QtWidgets.QMessageBox.Yes:
                return
        self.presets[name] = settings_map
        save_presets(PRESET_STORE, self.presets)
        self._refresh_presets()
        self._append_log("OK", f"Пресет збережено: {name}")

    @QtCore.Slot(str)
    def deletePreset(self, name: str) -> None:
        if not name:
            return
        if QtWidgets.QMessageBox.question(None, "Пресети", f"Видалити пресет '{name}'?") != QtWidgets.QMessageBox.Yes:
            return
        if name in self.presets:
            del self.presets[name]
            save_presets(PRESET_STORE, self.presets)
            self._refresh_presets()
            self._append_log("OK", f"Пресет видалено: {name}")

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
                    self._set_status(msg)
                elif etype == "progress":
                    _, file_pct, out_time, duration, file_eta, total_pct, total_eta = event
                    if file_pct is not None:
                        self._file_progress_text = (
                            f"Файл: {int(file_pct * 100):02d}% • {format_time(out_time)} / {format_time(duration)} • ETA {format_time(file_eta)}"
                        )
                    else:
                        self._file_progress_text = "Файл: --"
                    self.fileProgressTextChanged.emit()
                    self._total_progress_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
                    self.totalProgressTextChanged.emit()
                    self._set_progress(file_pct or 0.0, total_pct)
                elif etype == "set_total":
                    self._set_progress(0.0, 0.0)
                elif etype == "done":
                    _, stopped = event
                    self._is_running = False
                    self.isRunningChanged.emit()
                    self._set_status("Зупинено." if stopped else "Готово.")
                elif etype == "media_info":
                    _, path, info = event
                    self.media_info_cache[path] = info
                    items = self.queue_model.items()
                    if items:
                        for idx, task in enumerate(items):
                            if task.path == path:
                                self._update_info(info)
                                break
        except queue.Empty:
            return
