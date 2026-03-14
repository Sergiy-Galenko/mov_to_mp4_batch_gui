import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from config.constants import (
    APP_TITLE,
    DEFAULT_OUTPUT_DIR,
    HISTORY_STORE,
    HW_ENCODER_OPTIONS,
    OPERATION_OPTIONS,
    OUT_AUDIO_FORMATS,
    OUT_IMAGE_FORMATS,
    OUT_SUBTITLE_FORMATS,
    OUT_VIDEO_FORMATS,
    POSITION_OPTIONS,
    PRESET_STORE,
    RECENT_FOLDERS_LIMIT,
    ROTATE_OPTIONS,
    STATE_STORE,
    VIDEO_CODEC_OPTIONS,
)
from config.paths import find_ffmpeg, find_ffprobe
from core.models import ConversionSettings, MediaInfo, TaskItem
from core.presets import load_presets, save_presets
from core.settings import merge_settings_maps, settings_map_to_model
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from utils.files import build_output_path, file_sha256, is_subtitle, media_type
from utils.formatting import format_bytes, format_time
from utils.state import load_json_file, load_json_state, save_json_file, save_json_state


class QueueModel(QtCore.QAbstractListModel):
    NameRole = QtCore.Qt.UserRole + 1
    TypeRole = QtCore.Qt.UserRole + 2
    PathRole = QtCore.Qt.UserRole + 3
    DisplayRole = QtCore.Qt.UserRole + 4
    StatusRole = QtCore.Qt.UserRole + 5
    ErrorRole = QtCore.Qt.UserRole + 6
    AttemptsRole = QtCore.Qt.UserRole + 7
    HasOverrideRole = QtCore.Qt.UserRole + 8
    OutputRole = QtCore.Qt.UserRole + 9
    PreviewRole = QtCore.Qt.UserRole + 10

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
        if role == self.StatusRole:
            return item.status
        if role == self.ErrorRole:
            return item.last_error
        if role == self.AttemptsRole:
            return item.attempts
        if role == self.HasOverrideRole:
            return bool(item.overrides)
        if role == self.OutputRole:
            return item.last_output
        if role == self.PreviewRole:
            return item.preview_output
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.NameRole: b"name",
            self.TypeRole: b"mediaType",
            self.PathRole: b"path",
            self.DisplayRole: b"display",
            self.StatusRole: b"status",
            self.ErrorRole: b"errorText",
            self.AttemptsRole: b"attempts",
            self.HasOverrideRole: b"hasOverride",
            self.OutputRole: b"outputPath",
            self.PreviewRole: b"previewOutput",
        }

    def items(self) -> List[TaskItem]:
        return list(self._items)

    def item_at(self, index: int) -> Optional[TaskItem]:
        if index < 0 or index >= len(self._items):
            return None
        return self._items[index]

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

    def update_item(self, index: int, item: TaskItem) -> None:
        if index < 0 or index >= len(self._items):
            return
        self._items[index] = item
        model_index = self.index(index, 0)
        self.dataChanged.emit(model_index, model_index, list(self.roleNames().keys()))

    def update_task_state(self, task_path: Path, status: str, message: str = "", output_path: str = "") -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            if status == "running":
                item.attempts += 1
            item.status = status
            if status == "success":
                item.last_error = ""
            elif status in {"failed", "skipped"}:
                item.last_error = message
            if output_path:
                item.last_output = output_path
            self.update_item(idx, item)
            return

    def set_preview_output(self, task_path: Path, preview_output: str) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            if item.preview_output == preview_output:
                return
            item.preview_output = preview_output
            self.update_item(idx, item)
            return

    def paths_set(self) -> set[Path]:
        return {item.path for item in self._items}

    def clear_statuses(self, *, paths: Optional[set[Path]] = None) -> None:
        for idx, item in enumerate(self._items):
            if paths is not None and item.path not in paths:
                continue
            item.status = "queued"
            item.last_error = ""
            item.last_output = ""
            self.update_item(idx, item)


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
    recentFoldersChanged = QtCore.Signal()
    watchFolderChanged = QtCore.Signal()
    watchRunningChanged = QtCore.Signal()
    outputPreviewChanged = QtCore.Signal()
    historyChanged = QtCore.Signal()
    queueStatsChanged = QtCore.Signal()
    onboardingChanged = QtCore.Signal()
    taskOverrideLoaded = QtCore.Signal(dict)
    watermarkPicked = QtCore.Signal(str)
    fontPicked = QtCore.Signal(str)
    subtitlePicked = QtCore.Signal(str)
    coverArtPicked = QtCore.Signal(str)
    audioReplacePicked = QtCore.Signal(str)

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
        self.recent_folders_model = QtCore.QStringListModel()
        self._log_lines: List[str] = []
        self._selected_index = -1
        self._last_settings_map: Dict[str, Any] = {}
        self._output_preview_text = "Preview ще не згенеровано."
        self._selected_preview_source = "—"
        self._selected_preview_output = "—"
        self._history_entries = load_json_file(HISTORY_STORE) or []
        if not isinstance(self._history_entries, list):
            self._history_entries = []

        app_state = load_json_state(STATE_STORE)
        self._recent_folders: List[str] = [
            folder for folder in app_state.get("recent_folders", []) if isinstance(folder, str) and folder
        ][:RECENT_FOLDERS_LIMIT]
        self._watch_folder = str(app_state.get("watch_folder") or "")
        self._watch_running = False
        self._watch_seen: set[Path] = set()

        self._ffmpeg_path = str(app_state.get("ffmpeg_path") or self.ffmpeg_service.ffmpeg_path or "")
        self._output_dir = str(app_state.get("output_dir") or DEFAULT_OUTPUT_DIR)
        self._encoder_info = "Доступні: --"
        self._status_text = "Готово"
        self._show_onboarding = not bool(app_state.get("onboarding_completed"))
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
        self._info_analysis = "—"
        self._info_warnings = "—"

        restored_items = self._deserialize_queue_items(app_state.get("queue_items", []), pending_recovery=bool(app_state.get("pending_recovery")))
        if restored_items:
            self.queue_model.set_items(restored_items)
        restored_settings = app_state.get("last_settings")
        if isinstance(restored_settings, dict):
            self._last_settings_map = dict(restored_settings)

        self._refresh_presets()
        self._refresh_recent_folders()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._poll_events)
        self._timer.start()

        self._watch_timer = QtCore.QTimer(self)
        self._watch_timer.setInterval(3000)
        self._watch_timer.timeout.connect(self._scan_watch_folder)

    @QtCore.Property(str, constant=True)
    def appTitle(self) -> str:
        return APP_TITLE

    @QtCore.Property(QtCore.QObject, constant=True)
    def queueModel(self) -> QtCore.QObject:
        return self.queue_model

    @QtCore.Property(QtCore.QObject, constant=True)
    def presetsModel(self) -> QtCore.QObject:
        return self.presets_model

    @QtCore.Property(QtCore.QObject, notify=recentFoldersChanged)
    def recentFoldersModel(self) -> QtCore.QObject:
        return self.recent_folders_model

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
        self._save_state()

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
        self._remember_folder(value)
        self._save_state()

    @QtCore.Property(str, notify=watchFolderChanged)
    def watchFolder(self) -> str:
        return self._watch_folder

    @watchFolder.setter
    def watchFolder(self, value: str) -> None:
        value = value.strip()
        if self._watch_folder == value:
            return
        self._watch_folder = value
        self.watchFolderChanged.emit()
        if value:
            self._remember_folder(value)
        self._save_state()

    @QtCore.Property(bool, notify=watchRunningChanged)
    def watchRunning(self) -> bool:
        return self._watch_running

    @QtCore.Property(bool, notify=onboardingChanged)
    def onboardingVisible(self) -> bool:
        return self._show_onboarding

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

    @QtCore.Property(str, notify=infoChanged)
    def infoAnalysis(self) -> str:
        return self._info_analysis

    @QtCore.Property(str, notify=infoChanged)
    def infoWarnings(self) -> str:
        return self._info_warnings

    @QtCore.Property(str, notify=outputPreviewChanged)
    def outputPreviewText(self) -> str:
        return self._output_preview_text

    @QtCore.Property(str, notify=outputPreviewChanged)
    def selectedPreviewSource(self) -> str:
        return self._selected_preview_source

    @QtCore.Property(str, notify=outputPreviewChanged)
    def selectedPreviewOutput(self) -> str:
        return self._selected_preview_output

    @QtCore.Property(str, notify=historyChanged)
    def historyText(self) -> str:
        if not self._history_entries:
            return "Історія запусків порожня."
        lines: List[str] = []
        for raw_entry in self._history_entries[:8]:
            if not isinstance(raw_entry, dict):
                continue
            entry = raw_entry
            started_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("started_at", 0) or 0))
            results = entry.get("results", [])
            failed = sum(1 for item in results if item.get("status") == "failed")
            skipped = sum(1 for item in results if item.get("status") == "skipped")
            lines.append(
                f"{started_at} | {entry.get('operation', '—')} | файлів {entry.get('total_files', 0)} | "
                f"failed {failed} | skipped {skipped} | {entry.get('output_dir', '—')}"
            )
        return "\n".join(lines) or "Історія запусків порожня."

    @QtCore.Property(int, notify=queueStatsChanged)
    def queueCount(self) -> int:
        return len(self.queue_model.items())

    @QtCore.Property(int, notify=queueStatsChanged)
    def completedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {"success", "skipped"})

    @QtCore.Property(int, notify=queueStatsChanged)
    def failedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == "failed")

    @QtCore.Property(int, notify=queueStatsChanged)
    def runningCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == "running")

    def _serialize_task(self, item: TaskItem) -> Dict[str, Any]:
        return {
            "path": str(item.path),
            "media_type": item.media_type,
            "status": item.status,
            "last_error": item.last_error,
            "attempts": item.attempts,
            "last_output": item.last_output,
            "preview_output": item.preview_output,
            "content_hash": item.content_hash,
            "overrides": dict(item.overrides),
        }

    def _deserialize_queue_items(self, payload: Any, *, pending_recovery: bool) -> List[TaskItem]:
        if not isinstance(payload, list):
            return []
        items: List[TaskItem] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            path_value = str(raw.get("path") or "").strip()
            media_kind = str(raw.get("media_type") or "").strip()
            if not path_value or not media_kind:
                continue
            status = str(raw.get("status") or "queued")
            if pending_recovery and status == "running":
                status = "queued"
            items.append(
                TaskItem(
                    path=Path(path_value).expanduser(),
                    media_type=media_kind,
                    status=status,
                    last_error=str(raw.get("last_error") or ""),
                    attempts=int(raw.get("attempts") or 0),
                    last_output=str(raw.get("last_output") or ""),
                    preview_output=str(raw.get("preview_output") or ""),
                    content_hash=str(raw.get("content_hash") or ""),
                    overrides=dict(raw.get("overrides") or {}),
                )
            )
        return items

    def _save_state(self, *, pending_recovery: Optional[bool] = None) -> None:
        if pending_recovery is None:
            pending_recovery = self._is_running
        save_json_state(
            STATE_STORE,
            {
                "recent_folders": self._recent_folders[:RECENT_FOLDERS_LIMIT],
                "watch_folder": self._watch_folder,
                "output_dir": self._output_dir,
                "ffmpeg_path": self._ffmpeg_path,
                "last_settings": self._last_settings_map,
                "queue_items": [self._serialize_task(item) for item in self.queue_model.items()],
                "pending_recovery": bool(pending_recovery),
                "onboarding_completed": not self._show_onboarding,
            },
        )

    def _record_history(self, entry: Dict[str, Any]) -> None:
        self._history_entries.insert(0, entry)
        self._history_entries = self._history_entries[:30]
        save_json_file(HISTORY_STORE, self._history_entries)
        self.historyChanged.emit()

    def _set_output_preview(self, value: str) -> None:
        if self._output_preview_text == value:
            return
        self._output_preview_text = value
        self.outputPreviewChanged.emit()

    def _set_selected_preview(self, source: str, output_name: str) -> None:
        source_value = source or "—"
        output_value = output_name or "—"
        if self._selected_preview_source == source_value and self._selected_preview_output == output_value:
            return
        self._selected_preview_source = source_value
        self._selected_preview_output = output_value
        self.outputPreviewChanged.emit()

    def _notify_queue_stats(self) -> None:
        self.queueStatsChanged.emit()

    def _refresh_recent_folders(self) -> None:
        self.recent_folders_model.setStringList(self._recent_folders)
        self.recentFoldersChanged.emit()

    def _remember_folder(self, folder: str) -> None:
        value = folder.strip()
        if not value:
            return
        path = str(Path(value).expanduser())
        if path in self._recent_folders:
            self._recent_folders.remove(path)
        self._recent_folders.insert(0, path)
        self._recent_folders = self._recent_folders[:RECENT_FOLDERS_LIMIT]
        self._refresh_recent_folders()
        self._save_state()

    def _append_log(self, level: str, msg: str) -> None:
        self._log_lines.append(f"{level}: {msg}")
        self.logAdded.emit(level, msg)

    def _refresh_presets(self) -> None:
        self.presets_model.setStringList(sorted(self.presets.keys()))

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
        if self.ffmpegPath:
            self.ffmpeg_service.ffmpeg_path = self.ffmpegPath
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
    def dismissOnboarding(self) -> None:
        if not self._show_onboarding:
            return
        self._show_onboarding = False
        self.onboardingChanged.emit()
        self._save_state()

    @QtCore.Slot(int, str)
    def useRecentFolder(self, index: int, target: str) -> None:
        if index < 0 or index >= len(self._recent_folders):
            return
        folder = self._recent_folders[index]
        if target == "watch":
            self.watchFolder = folder
        else:
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
        filt = (
            "Media Files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts "
            "*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif);;All Files (*)"
        )
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Додати файли", "", filt)
        paths = [Path(p) for p in files]
        if paths:
            self._remember_folder(str(paths[0].parent))
        self._add_paths(paths)

    @QtCore.Slot("QVariantList")
    def addDroppedUrls(self, urls: List[Any]) -> None:
        paths: List[Path] = []
        for value in urls:
            if isinstance(value, QtCore.QUrl):
                local_path = value.toLocalFile()
            else:
                local_path = QtCore.QUrl(str(value)).toLocalFile()
            if local_path:
                path = Path(local_path)
                if path.is_dir():
                    paths.extend([p for p in path.rglob("*") if p.is_file()])
                else:
                    paths.append(path)
        if paths:
            self._remember_folder(str(paths[0].parent))
            self._add_paths(paths)

    @QtCore.Slot()
    def addFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Додати папку")
        if folder:
            self._remember_folder(folder)
            base = Path(folder)
            items = [p for p in base.rglob("*") if p.is_file()]
            self._add_paths(items)

    def _add_paths(self, paths: List[Path]) -> None:
        existing = self.queue_model.paths_set()
        added: List[TaskItem] = []
        duplicate_count = 0
        for path in paths:
            mtype = media_type(path)
            if not mtype:
                continue
            resolved = path.expanduser().resolve()
            if resolved in existing or any(item.path == resolved for item in added):
                duplicate_count += 1
                continue
            added.append(TaskItem(path=resolved, media_type=mtype))
        if added:
            self.queue_model.add_items(added)
            self._notify_queue_stats()
            self._append_log("OK", f"Додано файлів: {len(added)}")
            if self._last_settings_map:
                self._refresh_output_preview(dict(self._last_settings_map))
            self._save_state()
        if duplicate_count:
            self._append_log("INFO", f"Пропущено дублікатів: {duplicate_count}")
        if not added and not duplicate_count:
            self._append_log("WARN", "Не знайдено підтримуваних файлів.")

    @QtCore.Slot()
    def deduplicateQueue(self) -> None:
        seen: set[Path] = set()
        unique: List[TaskItem] = []
        removed = 0
        for item in self.queue_model.items():
            if item.path in seen:
                removed += 1
                continue
            seen.add(item.path)
            unique.append(item)
        self.queue_model.set_items(unique)
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено дублікатів: {removed}")

    @QtCore.Slot()
    def deduplicateQueueByHash(self) -> None:
        items = self.queue_model.items()
        seen: Dict[tuple[int, str], TaskItem] = {}
        unique: List[TaskItem] = []
        removed = 0
        for item in items:
            try:
                size = item.path.stat().st_size
            except Exception:
                unique.append(item)
                continue
            if not item.content_hash and item.path.exists():
                try:
                    item.content_hash = file_sha256(item.path)
                except Exception as exc:
                    self._append_log("WARN", f"Не вдалося порахувати hash для {item.path.name}: {exc}")
                    unique.append(item)
                    continue
            key = (size, item.content_hash)
            if item.content_hash and key in seen:
                removed += 1
                self._append_log("INFO", f"Hash duplicate: {item.path.name} == {seen[key].path.name}")
                continue
            if item.content_hash:
                seen[key] = item
            unique.append(item)
        self.queue_model.set_items(unique)
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено hash-дублікатів: {removed}")

    def _move_selected(self, indices: List[int], direction: str) -> None:
        if not indices:
            return
        items = self.queue_model.items()
        selected = sorted({idx for idx in indices if 0 <= idx < len(items)})
        if not selected:
            return
        if direction == "up":
            for idx in selected:
                if idx > 0 and idx - 1 not in selected:
                    items[idx - 1], items[idx] = items[idx], items[idx - 1]
        elif direction == "down":
            for idx in reversed(selected):
                if idx < len(items) - 1 and idx + 1 not in selected:
                    items[idx + 1], items[idx] = items[idx], items[idx + 1]
        elif direction == "top":
            moved = [items[idx] for idx in selected]
            rest = [item for idx, item in enumerate(items) if idx not in selected]
            items = moved + rest
        elif direction == "bottom":
            moved = [items[idx] for idx in selected]
            rest = [item for idx, item in enumerate(items) if idx not in selected]
            items = rest + moved
        self.queue_model.set_items(items)
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Slot("QVariantList")
    def moveSelectedUp(self, indices: List[int]) -> None:
        self._move_selected(indices, "up")

    @QtCore.Slot("QVariantList")
    def moveSelectedDown(self, indices: List[int]) -> None:
        self._move_selected(indices, "down")

    @QtCore.Slot("QVariantList")
    def moveSelectedTop(self, indices: List[int]) -> None:
        self._move_selected(indices, "top")

    @QtCore.Slot("QVariantList")
    def moveSelectedBottom(self, indices: List[int]) -> None:
        self._move_selected(indices, "bottom")

    @QtCore.Slot("QVariantList")
    def removeSelected(self, indices: List[int]) -> None:
        if not indices:
            return
        remove_set = set(indices)
        keep = [item for idx, item in enumerate(self.queue_model.items()) if idx not in remove_set]
        self.queue_model.set_items(keep)
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено: {len(remove_set)}")
        self._clear_info()

    @QtCore.Slot()
    def clearQueue(self) -> None:
        self.queue_model.set_items([])
        self._notify_queue_stats()
        self._set_output_preview("Черга порожня.")
        self._set_selected_preview("—", "—")
        self._save_state()
        self._append_log("INFO", "Чергу очищено")
        self._clear_info()

    @QtCore.Slot()
    def exportLog(self) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-log.txt"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати лог", str(default_path), "Text (*.txt)")
        if not path:
            return
        Path(path).write_text("\n".join(self._log_lines), encoding="utf-8")
        self._append_log("OK", f"Лог збережено: {path}")

    @QtCore.Slot()
    def pickWatchFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Watch folder", self.watchFolder or "")
        if folder:
            self.watchFolder = folder

    @QtCore.Slot()
    def startWatching(self) -> None:
        folder = Path(self.watchFolder).expanduser()
        if not self.watchFolder or not folder.exists():
            QtWidgets.QMessageBox.warning(None, "Watch folder", "Оберіть існуючу папку для моніторингу.")
            return
        self._watch_seen = {path.resolve() for path in folder.rglob("*") if path.is_file()}
        self._watch_running = True
        self.watchRunningChanged.emit()
        self._watch_timer.start()
        self._append_log("OK", f"Watch folder активовано: {folder}")

    @QtCore.Slot()
    def stopWatching(self) -> None:
        self._watch_running = False
        self.watchRunningChanged.emit()
        self._watch_timer.stop()
        self._append_log("INFO", "Watch folder зупинено")

    def _scan_watch_folder(self) -> None:
        if not self._watch_running or not self.watchFolder:
            return
        base = Path(self.watchFolder).expanduser()
        if not base.exists():
            self.stopWatching()
            return
        current = {path.resolve() for path in base.rglob("*") if path.is_file()}
        new_paths = sorted(current - self._watch_seen)
        if new_paths:
            self._add_paths(new_paths)
            self._append_log("INFO", f"Watch folder додав файлів: {len(new_paths)}")
        self._watch_seen = current

    @QtCore.Slot(int)
    def selectQueueIndex(self, index: int) -> None:
        self._selected_index = index
        task = self.queue_model.item_at(index)
        if task is None:
            self._clear_info()
            self._set_selected_preview("—", "—")
            self.taskOverrideLoaded.emit({})
            return
        self._set_selected_preview(task.path.name, task.preview_output or "—")
        self._info_name = task.path.name
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self.infoChanged.emit()
        self.taskOverrideLoaded.emit(dict(task.overrides))
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
        analysis_bits: List[str] = []
        if info.fps:
            fps_label = f"{info.fps:.3f} fps"
            if info.frame_rate_mode:
                fps_label += f" ({info.frame_rate_mode})"
            analysis_bits.append(fps_label)
        if info.dynamic_range:
            analysis_bits.append(info.dynamic_range)
        if info.color_space:
            analysis_bits.append(info.color_space)
        if info.rotation not in (None, 0):
            analysis_bits.append(f"rotation {info.rotation}°")
        analysis_bits.append(f"audio {info.audio_streams}")
        analysis_bits.append(f"subs {info.subtitle_streams}")
        if info.chapters:
            analysis_bits.append(f"chapters {len(info.chapters)}")
        self._info_analysis = " | ".join(bit for bit in analysis_bits if bit) or "—"
        self._info_warnings = " | ".join(info.warnings) if info.warnings else "—"
        self.infoChanged.emit()

    def _clear_info(self) -> None:
        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self._info_analysis = "—"
        self._info_warnings = "—"
        self.infoChanged.emit()

    @QtCore.Slot()
    def pickWatermark(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Вибрати водяний знак",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        if path:
            self.watermarkPicked.emit(path)

    @QtCore.Slot()
    def pickCoverArt(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Вибрати cover art",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        if path:
            self.coverArtPicked.emit(path)

    @QtCore.Slot()
    def pickAudioReplace(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Вибрати аудіо для заміни",
            "",
            "Audio (*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.mp4 *.mov *.mkv);;All Files (*)",
        )
        if path:
            self.audioReplacePicked.emit(path)

    @QtCore.Slot()
    def pickFont(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати шрифт", "", "Fonts (*.ttf *.otf);;All Files (*)")
        if path:
            self.fontPicked.emit(path)

    @QtCore.Slot()
    def pickSubtitle(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Вибрати субтитри",
            "",
            "Subtitles (*.srt *.ass *.ssa *.vtt *.webvtt);;All Files (*)",
        )
        if path:
            self.subtitlePicked.emit(path)

    def _validate_settings(self, settings: ConversionSettings, raw: Dict[str, Any]) -> None:
        numeric_fields = {
            "resize_w": "Resize W",
            "resize_h": "Resize H",
            "crop_w": "Crop W",
            "crop_h": "Crop H",
            "crop_x": "Crop X",
            "crop_y": "Crop Y",
            "sheet_cols": "Sheet Cols",
            "sheet_rows": "Sheet Rows",
            "sheet_width": "Sheet Width",
            "sheet_interval": "Sheet Interval",
        }
        for key, label in numeric_fields.items():
            value = str(raw.get(key, "")).strip()
            if value and not value.lstrip("-").isdigit():
                self._append_log("WARN", f"Некоректне поле: {label}.")
        if str(raw.get("speed", "")).strip() and settings.speed is None:
            self._append_log("WARN", "Некоректна швидкість.")
        if settings.watermark_path and not Path(settings.watermark_path).expanduser().exists():
            self._append_log("WARN", "Файл водяного знаку не знайдено.")
        if settings.cover_art_path and not Path(settings.cover_art_path).expanduser().exists():
            self._append_log("WARN", "Файл cover art не знайдено.")
        if settings.text_font and not Path(settings.text_font).expanduser().exists():
            self._append_log("WARN", "Файл шрифту не знайдено.")
        if settings.subtitle_path:
            subtitle = Path(settings.subtitle_path).expanduser()
            if not subtitle.exists() or not is_subtitle(subtitle):
                self._append_log("WARN", "Файл субтитрів не знайдено або формат не підтримується.")
        if settings.replace_audio_path and not Path(settings.replace_audio_path).expanduser().exists():
            self._append_log("WARN", "Файл заміни аудіо не знайдено.")

    def _refresh_output_preview(self, settings_map: Dict[str, Any]) -> None:
        if not self.queue_model.items():
            self._set_output_preview("Черга порожня.")
            self._set_selected_preview("—", "—")
            return
        out_dir = Path(self.outputDir).expanduser()
        lines: List[str] = []
        for index, item in enumerate(self.queue_model.items(), start=1):
            merged_map = merge_settings_maps(settings_map, item.overrides)
            resolved = settings_map_to_model(merged_map, defaults=ConversionSettings())
            out_ext = self.ffmpeg_service.output_extension_for(item.media_type, resolved)
            preview_path = build_output_path(
                out_dir,
                item.path,
                out_ext,
                template=resolved.output_template,
                index=index,
                operation=resolved.operation,
                media_type_name=item.media_type,
                overwrite=resolved.overwrite,
                skip_existing=resolved.skip_existing,
            )
            self.queue_model.set_preview_output(item.path, preview_path.name)
            if self._selected_index >= 0:
                current = self.queue_model.item_at(self._selected_index)
                if current and current.path == item.path:
                    self._set_selected_preview(item.path.name, preview_path.name)
            lines.append(f"{item.path.name} -> {preview_path.name}")
        if len(lines) > 14:
            remaining = len(lines) - 14
            lines = lines[:14] + [f"... ще {remaining} файлів"]
        self._set_output_preview("\n".join(lines))

    @QtCore.Slot("QVariantMap")
    def refreshOutputPreview(self, settings_map: Dict[str, Any]) -> None:
        payload = dict(settings_map)
        self._last_settings_map = payload
        self._refresh_output_preview(payload)
        self._save_state()

    @QtCore.Slot()
    def restoreSession(self) -> None:
        if self.queue_model.rowCount() > 0:
            self._append_log("INFO", f"Відновлено чергу: {self.queue_model.rowCount()} елементів.")
        state = load_json_state(STATE_STORE)
        if state.get("pending_recovery"):
            self._append_log("WARN", "Відновлення після попереднього аварійного завершення.")
        if self._last_settings_map:
            self.presetLoaded.emit(dict(self._last_settings_map))
            self._refresh_output_preview(dict(self._last_settings_map))

    @QtCore.Slot("QVariantMap")
    def exportProject(self, settings_map: Dict[str, Any]) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-project.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати проєкт", str(default_path), "JSON (*.json)")
        if not path:
            return
        payload = {
            "version": 1,
            "exported_at": time.time(),
            "output_dir": self.outputDir,
            "ffmpeg_path": self.ffmpegPath,
            "settings": dict(settings_map),
            "queue_items": [self._serialize_task(item) for item in self.queue_model.items()],
        }
        save_json_file(Path(path), payload)
        self._append_log("OK", f"Проєкт збережено: {path}")

    @QtCore.Slot()
    def importProject(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Імпортувати проєкт", "", "JSON (*.json)")
        if not path:
            return
        payload = load_json_file(Path(path))
        if not isinstance(payload, dict):
            QtWidgets.QMessageBox.warning(None, "Проєкт", "Некоректний JSON проєкту.")
            return
        queue_items = self._deserialize_queue_items(payload.get("queue_items", []), pending_recovery=False)
        self.queue_model.set_items(queue_items)
        self._notify_queue_stats()
        self._last_settings_map = dict(payload.get("settings") or {})
        self.outputDir = str(payload.get("output_dir") or self.outputDir)
        imported_ffmpeg = str(payload.get("ffmpeg_path") or "").strip()
        if imported_ffmpeg:
            self.ffmpegPath = imported_ffmpeg
        self._save_state()
        if self._last_settings_map:
            self.presetLoaded.emit(dict(self._last_settings_map))
            self._refresh_output_preview(dict(self._last_settings_map))
        self._append_log("OK", f"Проєкт імпортовано: {path}")

    @QtCore.Slot()
    def clearHistory(self) -> None:
        self._history_entries = []
        save_json_file(HISTORY_STORE, self._history_entries)
        self.historyChanged.emit()
        self._append_log("INFO", "Історію запусків очищено.")

    def _build_run_tasks(self, settings_map: Dict[str, Any], *, failed_only: bool = False) -> List[TaskItem]:
        tasks: List[TaskItem] = []
        for item in self.queue_model.items():
            if failed_only and item.status != "failed":
                continue
            merged_map = merge_settings_maps(settings_map, item.overrides)
            resolved = settings_map_to_model(merged_map)
            tasks.append(
                TaskItem(
                    path=item.path,
                    media_type=item.media_type,
                    status="queued",
                    last_error="",
                    attempts=item.attempts,
                    last_output=item.last_output,
                    preview_output=item.preview_output,
                    overrides=dict(item.overrides),
                    resolved_settings=resolved,
                )
            )
        return tasks

    def _start_conversion(self, settings_map: Dict[str, Any], *, failed_only: bool = False) -> None:
        if self.converter.thread and self.converter.thread.is_alive():
            return
        entry_path = self.ffmpegPath
        if entry_path:
            self.ffmpeg_service.ffmpeg_path = entry_path
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            QtWidgets.QMessageBox.critical(None, "FFmpeg", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.")
            return
        run_tasks = self._build_run_tasks(settings_map, failed_only=failed_only)
        if not run_tasks:
            QtWidgets.QMessageBox.information(None, "Черга", "Немає задач для запуску.")
            return

        out_dir = Path(self.outputDir).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, "Помилка", f"Не вдалося створити папку виводу:\n{exc}")
            return

        base_settings = settings_map_to_model(settings_map)
        self._validate_settings(base_settings, settings_map)
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        self._set_progress(0.0, 0.0)
        self._file_progress_text = "Файл: --"
        self.fileProgressTextChanged.emit()
        self._total_progress_text = "Всього: --"
        self.totalProgressTextChanged.emit()
        self._is_running = True
        self.isRunningChanged.emit()
        self._set_status("Конвертація запущена...")
        self._save_state(pending_recovery=True)

        if failed_only:
            paths = {task.path for task in run_tasks}
            self.queue_model.clear_statuses(paths=paths)
            self._notify_queue_stats()
        self.converter.start(run_tasks, base_settings, out_dir)

    @QtCore.Slot("QVariantMap")
    def startConversion(self, settings_map: Dict[str, Any]) -> None:
        self._start_conversion(dict(settings_map), failed_only=False)

    @QtCore.Slot()
    def retryFailed(self) -> None:
        if self._is_running:
            return
        if not self._last_settings_map:
            self._append_log("WARN", "Немає попередніх налаштувань для retry.")
            return
        self._append_log("INFO", "Повторюю тільки помилкові задачі.")
        self._start_conversion(dict(self._last_settings_map), failed_only=True)

    @QtCore.Slot()
    def stopConversion(self) -> None:
        self._set_status("Зупинка після поточного файлу...")
        self.converter.stop()

    @QtCore.Slot(str)
    def loadPreset(self, name: str) -> None:
        data = self.presets.get(name)
        if not data:
            return
        self.presetLoaded.emit(data)
        self._append_log("OK", f"Пресет завантажено: {name}")

    @QtCore.Slot(str, "QVariantMap")
    def savePreset(self, name: str, settings_map: Dict[str, Any]) -> None:
        if not name:
            QtWidgets.QMessageBox.warning(None, "Пресети", "Введи назву пресету.")
            return
        if name in self.presets:
            if QtWidgets.QMessageBox.question(None, "Пресети", "Пресет уже існує. Перезаписати?") != QtWidgets.QMessageBox.Yes:
                return
        self.presets[name] = dict(settings_map)
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

    @QtCore.Slot(int, "QVariantMap")
    def saveTaskOverride(self, index: int, override_map: Dict[str, Any]) -> None:
        task = self.queue_model.item_at(index)
        if task is None:
            return
        task.overrides = dict(override_map)
        self.queue_model.update_item(index, task)
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("OK", f"Оверрайд збережено для: {task.path.name}")
        if self._selected_index == index:
            self.taskOverrideLoaded.emit(dict(task.overrides))

    @QtCore.Slot(int)
    def clearTaskOverride(self, index: int) -> None:
        task = self.queue_model.item_at(index)
        if task is None:
            return
        task.overrides = {}
        self.queue_model.update_item(index, task)
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Оверрайд очищено: {task.path.name}")
        if self._selected_index == index:
            self.taskOverrideLoaded.emit({})

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
                    self._save_state(pending_recovery=False)
                elif etype == "media_info":
                    _, path, info = event
                    self.media_info_cache[path] = info
                    current = self.queue_model.item_at(self._selected_index)
                    if current and current.path == path:
                        self._update_info(info)
                elif etype == "task_state":
                    _, path, status, message, output_path = event
                    self.queue_model.update_task_state(path, status, message, output_path)
                    self._notify_queue_stats()
                    self._save_state()
                elif etype == "run_summary":
                    _, summary = event
                    if isinstance(summary, dict):
                        self._record_history(summary)
        except queue.Empty:
            return
