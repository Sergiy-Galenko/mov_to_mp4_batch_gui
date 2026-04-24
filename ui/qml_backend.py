import hashlib
import os
import queue
import shutil
import subprocess
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
from utils.formatting import format_bytes, format_time, parse_float, parse_time_to_seconds
from utils.state import load_json_file, load_json_state, save_json_file, save_json_state


from ui.models import QueueModel, LogModel, HistoryModel
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
    isPausedChanged = QtCore.Signal()
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
        self.log_model = LogModel()
        self.history_model = HistoryModel()
        self.media_info_cache: Dict[Path, MediaInfo] = {}
        self.presets: Dict[str, dict] = load_presets(PRESET_STORE)
        self.presets_model = QtCore.QStringListModel()
        self.recent_folders_model = QtCore.QStringListModel()
        self._log_lines: List[str] = []
        self._selected_index = -1
        self._selected_path = ""
        self._last_settings_map: Dict[str, Any] = {}
        self._output_preview_text = "Preview ще не згенеровано."
        self._selected_preview_source = "—"
        self._selected_preview_output = "—"
        self._selected_preview_command = "—"
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
        self._is_paused = False

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
        self.history_model.set_entries(self._history_entries)

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
    def logModel(self) -> QtCore.QObject:
        return self.log_model

    @QtCore.Property(QtCore.QObject, constant=True)
    def historyModel(self) -> QtCore.QObject:
        return self.history_model

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

    @QtCore.Property(bool, notify=isPausedChanged)
    def isPaused(self) -> bool:
        return self._is_paused

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

    @QtCore.Property(str, notify=outputPreviewChanged)
    def selectedPreviewCommand(self) -> str:
        return self._selected_preview_command

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
            "duration_text": item.duration_text,
            "size_text": item.size_text,
            "thumbnail_path": item.thumbnail_path,
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
                    duration_text=str(raw.get("duration_text") or "—"),
                    size_text=str(raw.get("size_text") or "—"),
                    thumbnail_path=str(raw.get("thumbnail_path") or ""),
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
        self.history_model.set_entries(self._history_entries)
        self.historyChanged.emit()

    def _set_output_preview(self, value: str) -> None:
        if self._output_preview_text == value:
            return
        self._output_preview_text = value
        self.outputPreviewChanged.emit()

    def _set_selected_preview(self, source: str, output_name: str, command: str = "—") -> None:
        source_value = source or "—"
        output_value = output_name or "—"
        command_value = command or "—"
        if (
            self._selected_preview_source == source_value
            and self._selected_preview_output == output_value
            and self._selected_preview_command == command_value
        ):
            return
        self._selected_preview_source = source_value
        self._selected_preview_output = output_value
        self._selected_preview_command = command_value
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
        self.log_model.append(level, msg)
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

    def _open_path(self, path: Path) -> bool:
        path = path.expanduser()
        if not path.exists():
            return False
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
        return True

    @QtCore.Slot(str)
    def openSourcePath(self, path_text: str) -> None:
        path = Path(str(path_text or "").strip()).expanduser()
        if not self._open_path(path):
            QtWidgets.QMessageBox.warning(None, "Джерело", "Файл джерела не знайдено.")

    @QtCore.Slot(str)
    def openOutputForPath(self, path_text: str) -> None:
        task = self.queue_model.item_by_path(Path(str(path_text or "").strip()).expanduser())
        if task is None:
            return
        output_text = (task.last_output or task.preview_output or "").split(";", 1)[0].strip()
        if not output_text:
            QtWidgets.QMessageBox.information(None, "Output", "Output для цього файлу ще не розраховано.")
            return
        output = Path(output_text).expanduser()
        if output.exists():
            self._open_path(output)
            return
        if output.parent.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(output.parent)))
            return
        QtWidgets.QMessageBox.warning(None, "Output", "Output-файл і його папку не знайдено.")

    @QtCore.Slot(int)
    def copyLogLine(self, index: int) -> None:
        line = self.log_model.line_at(index)
        if line:
            QtWidgets.QApplication.clipboard().setText(line)

    @QtCore.Slot()
    def clearLog(self) -> None:
        self._log_lines = []
        self.log_model.clear()

    @QtCore.Slot(str)
    def openPathFromText(self, text: str) -> None:
        source = str(text or "")
        for item in self.queue_model.items():
            if str(item.path) in source or item.path.name in source:
                self.openSourcePath(str(item.path))
                return
        self._append_log("WARN", "Не вдалося знайти файл для цього повідомлення.")

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
        folders: List[Path] = []
        for value in urls:
            if isinstance(value, QtCore.QUrl):
                local_path = value.toLocalFile()
            else:
                local_path = QtCore.QUrl(str(value)).toLocalFile()
            if local_path:
                path = Path(local_path)
                if path.is_dir():
                    folders.append(path)
                else:
                    paths.append(path)
        if paths:
            self._remember_folder(str(paths[0].parent))
            self._add_paths(paths)
        for folder in folders:
            self._append_log("INFO", f"Сканую папку у фоні: {folder}")
            threading.Thread(target=self._collect_folder_async, args=(folder,), daemon=True).start()

    @QtCore.Slot()
    def addFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Додати папку")
        if folder:
            base = Path(folder)
            self._append_log("INFO", f"Сканую папку у фоні: {base}")
            threading.Thread(target=self._collect_folder_async, args=(base,), daemon=True).start()

    def _collect_folder_async(self, folder: Path) -> None:
        try:
            items = [p for p in folder.rglob("*") if p.is_file()]
        except Exception as exc:
            self.event_queue.put(("log", "ERROR", f"Не вдалося просканувати папку {folder}: {exc}"))
            return
        self.event_queue.put(("add_paths", items, str(folder)))

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
            for item in added:
                self.queue_model.set_file_size(item.path)
                self._ensure_thumbnail_async(item.path, item.media_type)
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
        if not items:
            return
        self._append_log("INFO", "Hash-дедуплікація запущена у фоні.")
        threading.Thread(target=self._deduplicate_hash_async, args=(items,), daemon=True).start()

    def _deduplicate_hash_async(self, items: List[TaskItem]) -> None:
        seen: Dict[tuple[int, str], TaskItem] = {}
        unique: List[TaskItem] = []
        removed = 0
        log_lines: List[str] = []
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
                    log_lines.append(f"Не вдалося порахувати hash для {item.path.name}: {exc}")
                    unique.append(item)
                    continue
            key = (size, item.content_hash)
            if item.content_hash and key in seen:
                removed += 1
                log_lines.append(f"Hash duplicate: {item.path.name} == {seen[key].path.name}")
                continue
            if item.content_hash:
                seen[key] = item
            unique.append(item)
        self.event_queue.put(("dedupe_hash_done", unique, removed, log_lines))

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
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    def _paths_from_payload(self, paths: List[Any]) -> set[Path]:
        normalized: set[Path] = set()
        for value in paths:
            text = str(value or "").strip()
            if not text:
                continue
            normalized.add(Path(text).expanduser())
        return normalized

    def _move_selected_paths(self, paths: List[Any], direction: str) -> None:
        selected_paths = self._paths_from_payload(paths)
        if not selected_paths:
            return
        items = self.queue_model.items()
        selected = [idx for idx, item in enumerate(items) if item.path in selected_paths]
        self._move_selected(selected, direction)

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
    def moveSelectedPathsUp(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "up")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsDown(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "down")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsTop(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "top")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsBottom(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "bottom")

    @QtCore.Slot(str, int)
    def movePathToIndex(self, path_text: str, target_index: int) -> None:
        source_path = Path(str(path_text or "").strip()).expanduser()
        items = self.queue_model.items()
        source_index = next((idx for idx, item in enumerate(items) if item.path == source_path), -1)
        if source_index < 0:
            return
        target_index = max(0, min(int(target_index), len(items) - 1))
        if source_index == target_index:
            return
        item = items.pop(source_index)
        target_index = max(0, min(target_index, len(items)))
        items.insert(target_index, item)
        self.queue_model.set_items(items)
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

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

    @QtCore.Slot("QVariantList")
    def removeSelectedPaths(self, paths: List[Any]) -> None:
        remove_paths = self._paths_from_payload(paths)
        if not remove_paths:
            return
        keep = [item for item in self.queue_model.items() if item.path not in remove_paths]
        removed = len(self.queue_model.items()) - len(keep)
        self.queue_model.set_items(keep)
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        if self._selected_index < 0:
            self._selected_path = ""
            self._clear_info()
            self._set_selected_preview("—", "—")
        self._notify_queue_stats()
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено: {removed}")

    @QtCore.Slot(str)
    def removeTaskPath(self, path_text: str) -> None:
        self.removeSelectedPaths([path_text])

    @QtCore.Slot()
    def clearQueue(self) -> None:
        self.queue_model.set_items([])
        self._selected_index = -1
        self._selected_path = ""
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
            self._selected_path = ""
            self._clear_info()
            self._set_selected_preview("—", "—")
            self.taskOverrideLoaded.emit({})
            return
        self._selected_path = str(task.path)
        self._set_selected_preview(str(task.path), task.preview_output or "—")
        if self._last_settings_map:
            self._refresh_output_preview(dict(self._last_settings_map))
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
        self._ensure_thumbnail_async(task.path, task.media_type)

    @QtCore.Slot(str)
    def selectQueuePath(self, path_text: str) -> None:
        task_path = Path(str(path_text or "").strip()).expanduser()
        self.selectQueueIndex(self.queue_model.index_for_path(task_path))

    def _probe_media_async(self, path: Path) -> None:
        info = self.ffmpeg_service.probe_media(path)
        if info:
            self.event_queue.put(("media_info", path, info))

    def _ensure_thumbnail_async(self, path: Path, media_kind: str) -> None:
        if media_kind == "image":
            self.queue_model.set_thumbnail(path, str(path))
            return
        if media_kind != "video" or not self.ffmpeg_service.ffmpeg_path:
            return
        current = self.queue_model.item_by_path(path)
        if current and current.thumbnail_path:
            return
        threading.Thread(target=self._create_video_thumbnail, args=(path,), daemon=True).start()

    def _create_video_thumbnail(self, path: Path) -> None:
        cache_dir = Path.home() / ".media_converter_gui_thumbnails"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha1(str(path).encode("utf-8", errors="ignore")).hexdigest()[:16]
            target = cache_dir / f"{digest}.jpg"
            if not target.exists():
                cmd = [
                    self.ffmpeg_service.ffmpeg_path,
                    "-y",
                    "-ss",
                    "1",
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=160:-1",
                    str(target),
                ]
                subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if target.exists():
                self.event_queue.put(("thumbnail", path, str(target)))
        except Exception:
            return

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

    def _validate_settings_map(
        self,
        raw: Dict[str, Any],
        *,
        include_queue: bool,
        only_paths: Optional[set[Path]] = None,
    ) -> Dict[str, Any]:
        errors: Dict[str, str] = {}
        warnings: List[str] = []

        def add_error(field: str, message: str) -> None:
            errors.setdefault(field, message)

        def add_warning(message: str) -> None:
            if message not in warnings:
                warnings.append(message)

        positive_int_fields = {
            "resize_w": "Resize W",
            "resize_h": "Resize H",
            "crop_w": "Crop W",
            "crop_h": "Crop H",
            "sheet_cols": "Sheet Cols",
            "sheet_rows": "Sheet Rows",
            "sheet_width": "Sheet Width",
            "sheet_interval": "Sheet Interval",
        }
        non_negative_int_fields = {
            "crop_x": "Crop X",
            "crop_y": "Crop Y",
        }
        for field, label in positive_int_fields.items():
            value = str(raw.get(field, "")).strip()
            if not value:
                continue
            if not value.isdigit() or int(value) <= 0:
                add_error(field, f"{label}: очікується додатне число.")
        for field, label in non_negative_int_fields.items():
            value = str(raw.get(field, "")).strip()
            if not value:
                continue
            if not value.isdigit():
                add_error(field, f"{label}: очікується 0 або додатне число.")

        for field, label in {"trim_start": "Початок", "trim_end": "Кінець", "thumbnail_time": "Thumbnail time"}.items():
            value = str(raw.get(field, "")).strip()
            if value and parse_time_to_seconds(value) is None:
                add_error(field, f"{label}: формат має бути секундами або hh:mm:ss.")

        speed_value = str(raw.get("speed", "")).strip()
        if speed_value:
            parsed_speed = parse_float(speed_value)
            if parsed_speed is None or parsed_speed <= 0:
                add_error("speed", "Швидкість має бути числом більше 0.")

        for field, label in {
            "audio_bitrate": "Audio bitrate",
            "silence_duration": "Тривалість тиші",
            "audio_peak_limit_db": "Peak limit",
        }.items():
            value = str(raw.get(field, "")).strip()
            if field == "audio_bitrate":
                if value and not any(ch.isdigit() for ch in value):
                    add_error(field, f"{label}: вкажи значення на кшталт 192k.")
                continue
            if value and parse_float(value) is None:
                add_error(field, f"{label}: очікується число.")

        for field, label in {
            "wm_path": "Водяний знак",
            "cover_art_path": "Cover art",
            "text_font": "Шрифт",
            "subtitle_path": "Субтитри",
            "replace_audio_path": "Аудіо для заміни",
        }.items():
            value = str(raw.get(field, "")).strip()
            if value and not Path(value).expanduser().exists():
                add_error(field, f"{label}: файл не знайдено.")

        subtitle_path = str(raw.get("subtitle_path", "")).strip()
        if subtitle_path and not is_subtitle(Path(subtitle_path).expanduser()):
            add_error("subtitle_path", "Субтитри: формат не підтримується.")

        output_dir = Path(self.outputDir).expanduser()
        if not str(self.outputDir).strip():
            add_error("output_dir", "Папка виводу не задана.")

        if include_queue:
            queue_items = [
                item
                for item in self.queue_model.items()
                if only_paths is None or item.path in only_paths
            ]
            if not self.ffmpegPath:
                add_error("ffmpeg", "FFmpeg не знайдено або не задано.")
            else:
                ffmpeg_text = str(self.ffmpegPath).strip()
                if not Path(ffmpeg_text).expanduser().exists() and shutil.which(ffmpeg_text) is None:
                    add_error("ffmpeg", "FFmpeg недоступний за вказаним шляхом.")
                probe_path = find_ffprobe(ffmpeg_text)
                if not probe_path:
                    add_warning("FFprobe не знайдено; аналіз медіа, ETA і preflight будуть обмежені.")
            if not queue_items:
                add_error("queue", "Черга порожня.")
            operation = settings_map_to_model(raw, defaults=ConversionSettings()).operation
            if operation in {"audio_only", "subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet", "auto_subtitle"}:
                image_items = [item.path.name for item in queue_items if item.media_type != "video"]
                if image_items:
                    add_error("queue", f"Операція працює тільки з відео. Несумісних файлів: {len(image_items)}.")
            for item in queue_items:
                if not item.path.exists():
                    add_error("queue", f"Файл не знайдено: {item.path}")
                    break
            try:
                resolved = settings_map_to_model(raw, defaults=ConversionSettings())
                for idx, item in enumerate(queue_items, start=1):
                    out_ext = self.ffmpeg_service.output_extension_for(item.media_type, resolved)
                    desired = build_output_path(
                        output_dir,
                        item.path,
                        out_ext,
                        template=resolved.output_template,
                        index=idx,
                        operation=resolved.operation,
                        media_type_name=item.media_type,
                        overwrite=True,
                        skip_existing=True,
                    )
                    if desired.exists():
                        if resolved.overwrite:
                            add_warning(f"{desired.name}: буде перезаписано.")
                        elif resolved.skip_existing:
                            add_warning(f"{desired.name}: буде пропущено.")
                        else:
                            add_warning(f"{desired.name}: є конфлікт імені, буде створено безпечну копію.")
                        break
            except Exception:
                pass

        out_video = str(raw.get("out_video_fmt", "")).strip().lower()
        codec = str(raw.get("codec", "")).strip()
        if out_video == "webm" and codec in {"H.264 (AVC)", "H.265 (HEVC)"}:
            add_warning("WebM не сумісний з H.264/H.265; буде використано VP9 або AV1.")
        if out_video in {"mp4", "mov", "avi"} and codec == "VP9 (WebM)":
            add_warning("VP9 краще виводити у WebM; для MP4/MOV буде заміна на H.264.")

        if include_queue and output_dir.exists():
            try:
                queue_items = [
                    item
                    for item in self.queue_model.items()
                    if only_paths is None or item.path in only_paths
                ]
                source_size = sum(item.path.stat().st_size for item in queue_items if item.path.exists())
                free = shutil.disk_usage(output_dir).free
                if source_size and free < max(source_size * 0.15, 256 * 1024 * 1024):
                    add_warning("Мало вільного місця у папці виводу для безпечного batch-запуску.")
            except Exception:
                pass

        summary_bits = []
        if errors:
            summary_bits.append(f"Критичних помилок: {len(errors)}")
        if warnings:
            summary_bits.append(f"Попереджень: {len(warnings)}")
        summary = " | ".join(summary_bits) if summary_bits else "Перевірка пройдена."
        return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": summary}

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def validateSettings(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        return self._validate_settings_map(dict(settings_map), include_queue=True)

    def _format_command(self, cmd: List[Any]) -> str:
        return subprocess.list2cmdline([str(part) for part in cmd])

    def _build_dry_run_command(self, task: TaskItem, settings: ConversionSettings, output_path: Path) -> str:
        if settings.operation == "auto_subtitle":
            return f"whisper {self._format_command([task.path])} -> {output_path}"
        if not self.ffmpeg_service.ffmpeg_path:
            return "FFmpeg не задано"
        try:
            op = settings.operation
            if op in {"convert", "subtitle_burn"}:
                if task.media_type == "video":
                    info = self.media_info_cache.get(task.path)
                    cmd = self.ffmpeg_service.build_video_command(
                        task.path,
                        output_path,
                        settings,
                        info,
                        False,
                    )
                else:
                    cmd = self.ffmpeg_service.build_image_command(task.path, output_path, settings)
            elif op == "audio_only":
                cmd = self.ffmpeg_service.build_audio_command(task.path, output_path, settings)
            elif op == "subtitle_extract":
                cmd = self.ffmpeg_service.build_subtitle_extract_command(task.path, output_path, settings)
            elif op == "thumbnail":
                cmd = self.ffmpeg_service.build_thumbnail_command(task.path, output_path, settings)
            elif op == "contact_sheet":
                cmd = self.ffmpeg_service.build_contact_sheet_command(task.path, output_path, settings)
            else:
                return "Dry-run недоступний для цієї операції"
            return self._format_command(cmd)
        except Exception as exc:
            return f"Не вдалося зібрати dry-run команду: {exc}"

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
            desired_path = build_output_path(
                out_dir,
                item.path,
                out_ext,
                template=resolved.output_template,
                index=index,
                operation=resolved.operation,
                media_type_name=item.media_type,
                overwrite=True,
                skip_existing=True,
            )
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
            conflict = ""
            if desired_path.exists():
                if resolved.overwrite:
                    conflict = " | конфлікт: буде перезаписано"
                elif resolved.skip_existing:
                    conflict = " | конфлікт: буде пропущено"
                elif desired_path != preview_path:
                    conflict = f" | конфлікт: буде перейменовано в {preview_path.name}"
            self.queue_model.set_preview_output(item.path, str(preview_path))
            command = self._build_dry_run_command(item, resolved, preview_path)
            current = self.queue_model.item_at(self._selected_index)
            if (current and current.path == item.path) or (not current and index == 1):
                self._set_selected_preview(str(item.path), str(preview_path), command)
            codec_label = resolved.video_codec if resolved.operation in {"convert", "subtitle_burn"} else resolved.operation
            lines.append(f"{index:02d}. {item.path} -> {preview_path} | {out_ext} | {codec_label}{conflict}")
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

    @QtCore.Slot("QVariantMap")
    def exportCommandScript(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        command = self._selected_preview_command
        if not command or command == "—":
            QtWidgets.QMessageBox.information(None, "FFmpeg command", "Немає команди для експорту.")
            return
        suffix = ".bat" if os.name == "nt" else ".sh"
        default_path = Path(self.outputDir).expanduser() / f"ffmpeg-command{suffix}"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експорт команди", str(default_path), f"Script (*{suffix});;All Files (*)")
        if not path:
            return
        script_path = Path(path)
        if os.name == "nt":
            content = f"@echo off\r\n{command}\r\n"
        else:
            content = f"#!/usr/bin/env sh\n{command}\n"
        script_path.write_text(content, encoding="utf-8")
        self._append_log("OK", f"Команду експортовано: {script_path}")

    @QtCore.Slot("QVariantMap")
    def copyDryRunCommand(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        if self._selected_preview_command and self._selected_preview_command != "—":
            QtWidgets.QApplication.clipboard().setText(self._selected_preview_command)
            self._append_log("OK", "Dry-run команду скопійовано.")

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
        self.history_model.set_entries(self._history_entries)
        self.historyChanged.emit()
        self._append_log("INFO", "Історію запусків очищено.")

    @QtCore.Slot(int)
    def openHistoryOutput(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        folder = Path(str(entry.get("output_dir") or "")).expanduser()
        if folder.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    @QtCore.Slot(int)
    def loadHistorySettings(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        settings = dict(entry.get("settings") or {})
        if not settings:
            self._append_log("WARN", "У цьому запуску немає збережених налаштувань.")
            return
        self._last_settings_map = settings
        self.presetLoaded.emit(settings)
        self._refresh_output_preview(settings)
        self._append_log("OK", "Налаштування запуску завантажено з історії.")

    @QtCore.Slot(int)
    def rerunHistory(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        settings = dict(entry.get("settings") or {})
        if not settings:
            self._append_log("WARN", "У цьому запуску немає налаштувань для повтору.")
            return
        paths: List[Path] = []
        for result in entry.get("results", []):
            path_text = str(result.get("path") or "").strip()
            if path_text:
                paths.append(Path(path_text))
        self._add_paths(paths)
        only_paths = {path.expanduser().resolve() for path in paths}
        self._start_conversion(settings, only_paths=only_paths)

    def _build_run_tasks(
        self,
        settings_map: Dict[str, Any],
        *,
        failed_only: bool = False,
        only_paths: Optional[set[Path]] = None,
    ) -> List[TaskItem]:
        tasks: List[TaskItem] = []
        for item in self.queue_model.items():
            if failed_only and item.status != "failed":
                continue
            if only_paths is not None and item.path not in only_paths:
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

    def _start_conversion(
        self,
        settings_map: Dict[str, Any],
        *,
        failed_only: bool = False,
        only_paths: Optional[set[Path]] = None,
    ) -> None:
        if self.converter.thread and self.converter.thread.is_alive():
            return
        entry_path = self.ffmpegPath
        if entry_path:
            self.ffmpeg_service.ffmpeg_path = entry_path
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        if not self.ffmpeg_service.ffmpeg_path:
            QtWidgets.QMessageBox.critical(None, "FFmpeg", "FFmpeg не знайдено. Вкажи шлях до ffmpeg.")
            return
        preflight = self._validate_settings_map(settings_map, include_queue=True, only_paths=only_paths)
        if not preflight.get("ok"):
            details = "\n".join(str(msg) for msg in dict(preflight.get("errors") or {}).values())
            QtWidgets.QMessageBox.critical(None, "Preflight", details or "Є критичні помилки.")
            self._append_log("ERROR", f"Preflight заблокував старт: {preflight.get('summary')}")
            return
        for warning in preflight.get("warnings") or []:
            self._append_log("WARN", f"Preflight: {warning}")

        run_tasks = self._build_run_tasks(settings_map, failed_only=failed_only, only_paths=only_paths)
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

    @QtCore.Slot(str)
    def retryTaskPath(self, path_text: str) -> None:
        if self._is_running:
            return
        if not self._last_settings_map:
            self._append_log("WARN", "Немає налаштувань для retry одного файлу.")
            return
        task_path = Path(str(path_text or "").strip()).expanduser()
        if self.queue_model.item_by_path(task_path) is None:
            return
        self.queue_model.clear_statuses(paths={task_path})
        self._append_log("INFO", f"Повторюю файл: {task_path.name}")
        self._start_conversion(dict(self._last_settings_map), only_paths={task_path})

    @QtCore.Slot()
    def stopConversion(self) -> None:
        self._set_status("Зупинка після поточного файлу...")
        self.converter.stop()

    @QtCore.Slot()
    def pauseConversion(self) -> None:
        if not self._is_running:
            return
        self.converter.pause()
        if not self._is_paused:
            self._is_paused = True
            self.isPausedChanged.emit()
        self._set_status("Пауза...")

    @QtCore.Slot()
    def resumeConversion(self) -> None:
        self.converter.resume()
        if self._is_paused:
            self._is_paused = False
            self.isPausedChanged.emit()
        if self._is_running:
            self._set_status("Конвертація продовжується...")

    @QtCore.Slot()
    def skipCurrentFile(self) -> None:
        if not self._is_running:
            return
        self.converter.skip_current()
        self._set_status("Пропускаю поточний файл...")

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

    @QtCore.Slot(str, "QVariantMap")
    def saveTaskOverrideByPath(self, path_text: str, override_map: Dict[str, Any]) -> None:
        index = self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser())
        self.saveTaskOverride(index, override_map)

    @QtCore.Slot("QVariantList", "QVariantMap")
    def saveBulkOverride(self, paths: List[Any], override_map: Dict[str, Any]) -> None:
        selected_paths = self._paths_from_payload(paths)
        if not selected_paths:
            return
        changed = 0
        for idx, task in enumerate(self.queue_model.items()):
            if task.path not in selected_paths:
                continue
            task.overrides = dict(override_map)
            self.queue_model.update_item(idx, task)
            changed += 1
        if changed:
            if self._last_settings_map:
                self._refresh_output_preview(dict(self._last_settings_map))
            self._save_state()
            self._append_log("OK", f"Bulk override застосовано: {changed}")
            current = self.queue_model.item_at(self._selected_index)
            if current:
                self.taskOverrideLoaded.emit(dict(current.overrides))

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

    @QtCore.Slot(str)
    def clearTaskOverrideByPath(self, path_text: str) -> None:
        index = self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser())
        self.clearTaskOverride(index)

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
                    if self._is_paused:
                        self._is_paused = False
                        self.isPausedChanged.emit()
                    self._set_status("Зупинено." if stopped else "Готово.")
                    self._save_state(pending_recovery=False)
                elif etype == "media_info":
                    _, path, info = event
                    self.media_info_cache[path] = info
                    self.queue_model.set_media_summary(path, info)
                    current = self.queue_model.item_at(self._selected_index)
                    if current and current.path == path:
                        self._update_info(info)
                    if self._last_settings_map:
                        self._refresh_output_preview(dict(self._last_settings_map))
                elif etype == "thumbnail":
                    _, path, thumbnail_path = event
                    self.queue_model.set_thumbnail(path, thumbnail_path)
                elif etype == "add_paths":
                    _, paths, remember_folder = event
                    if remember_folder:
                        self._remember_folder(remember_folder)
                    self._add_paths(paths)
                elif etype == "dedupe_hash_done":
                    _, unique, removed, log_lines = event
                    self.queue_model.set_items(unique)
                    self._notify_queue_stats()
                    if self._last_settings_map:
                        self._refresh_output_preview(dict(self._last_settings_map))
                    self._save_state()
                    for line in log_lines:
                        self._append_log("INFO", line)
                    self._append_log("INFO", f"Видалено hash-дублікатів: {removed}")
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
