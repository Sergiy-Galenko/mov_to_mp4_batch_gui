from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from app.constants import (
    ANALYTICS_EMIT_INTERVAL_SEC,
    APP_TITLE,
    EVENT_POLL_INTERVAL_MS,
    RECENT_FOLDERS_LIMIT,
    RESOURCE_SAMPLE_INTERVAL_SEC,
    WATCH_SCAN_INTERVAL_MS,
)
from app.paths import find_ffmpeg, find_ffprobe
from app.localization import normalize_language, translate
from app.models import ConversionSettings, MediaInfo, TaskItem, TaskStatus
from app.performance_profiles import prediction_factor
from app.settings import merge_settings_maps, settings_map_to_model
from services.ffmpeg_service import FfmpegService
from services.history_store import HistoryStore
from services.preset_manager import PresetManager
from services.queue_manager import QueueManager
from services.settings_manager import SettingsManager
from services.watch_service import WatchService
from ui.models import HistoryModel, LogModel, QueueModel
from utils.formatting import format_bytes, format_time
from utils.state import load_json_file, save_json_file


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
    uiLanguageChanged = QtCore.Signal()
    languageChanged = QtCore.Signal()
    speedHistoryChanged = QtCore.Signal(list)
    fileTimingsChanged = QtCore.Signal(list)
    codecDistributionChanged = QtCore.Signal(dict)
    resourceHistoryChanged = QtCore.Signal(list)
    sessionStatsChanged = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.event_queue: "queue.Queue[tuple]" = queue.Queue()
        self.ffmpeg_service = FfmpegService(find_ffmpeg(), None)
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        self._converter_service = None
        self._runner = None
        self._media_analysis = None
        self._preview_builder = None
        self._validation = None
        self.queue_manager = QueueManager()
        self.settings_manager = SettingsManager()
        self.preset_manager = PresetManager()
        self.history_store = HistoryStore()
        self.watch_service = WatchService(
            on_new_files=self._on_watch_files,
            poll_interval_sec=max(WATCH_SCAN_INTERVAL_MS / 1000.0, 0.5),
        )

        self.queue_model = QueueModel()
        self.log_model = LogModel()
        self.history_model = HistoryModel()
        self.presets_model = QtCore.QStringListModel()
        self.recent_folders_model = QtCore.QStringListModel()

        state = self.settings_manager.state
        self._recent_folders = self.settings_manager.recent_folders()
        self._watch_folder = self.settings_manager.watch_folder()
        self._ui_language = self.settings_manager.ui_language()
        self._watch_running = False
        self._watch_seen: set[Path] = set()
        self._ffmpeg_path = self.settings_manager.ffmpeg_path(self.ffmpeg_service.ffmpeg_path)
        self._output_dir = self.settings_manager.output_dir()
        self._last_settings_map = self.settings_manager.last_settings()
        self._show_onboarding = False

        restored_items = self.queue_manager.deserialize_tasks(
            state.get("queue_items", []),
            pending_recovery=bool(state.get("pending_recovery")),
        )
        self.queue_model.set_items(restored_items)

        self.media_info_cache: Dict[Path, MediaInfo] = {}
        self._probe_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ffprobe-prefetch")
        self._probe_pending: set[Path] = set()
        self._log_lines: List[str] = []
        self._selected_index = -1
        self._selected_path = ""
        self._output_preview_text = "Preview ще не згенеровано."
        self._selected_preview_source = "—"
        self._selected_preview_output = "—"
        self._selected_preview_command = "—"
        self._encoder_info = "Доступні: --"
        self._status_text = "Готово"
        self._file_progress = 0.0
        self._total_progress = 0.0
        self._file_progress_text = "Файл: --"
        self._total_progress_text = "Всього: --"
        self._is_running = False
        self._is_paused = False
        self._active_task_path = ""
        self._run_started_monotonic = 0.0
        self._last_analytics_emit = 0.0
        self._last_resource_emit = 0.0
        self._speed_history: List[Dict[str, float]] = []
        self._file_timings: List[Dict[str, Any]] = []
        self._codec_distribution: Dict[str, int] = {}
        self._resource_history: List[Dict[str, float]] = []
        self._cpu_load_text = "CPU --"
        self._gpu_load_text = "GPU --"
        self._ram_load_text = "RAM --"
        self._task_started_at: Dict[Path, float] = {}
        self._session_elapsed_text = "00:00"
        self._session_eta_text = "--:--"
        self._session_avg_speed_text = "--"
        self._session_input_text = "0 B"
        self._session_output_text = "0 B"
        self._session_saved_text = "0 B"

        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self._info_analysis = "—"
        self._info_warnings = "—"

        self._refresh_presets()
        self._refresh_recent_folders()
        self.history_model.set_entries(self.history_store.entries)
        self._refresh_output_preview(dict(self._last_settings_map))

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(EVENT_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll_events)
        self._timer.start()

        self._watch_timer = QtCore.QTimer(self)
        self._watch_timer.setInterval(WATCH_SCAN_INTERVAL_MS)
        self._watch_timer.timeout.connect(self._scan_watch_folder)

    @property
    def converter(self):
        if self._converter_service is None:
            from services.converter_service import ConverterService

            self._converter_service = ConverterService(self.ffmpeg_service, self.event_queue)
        return self._converter_service

    @property
    def runner(self):
        if self._runner is None:
            from services.conversion_runner import ConversionRunner

            self._runner = ConversionRunner(self.converter)
        return self._runner

    @property
    def media_analysis(self):
        if self._media_analysis is None:
            from services.media_analysis_service import MediaAnalysisService

            self._media_analysis = MediaAnalysisService(self.ffmpeg_service)
        return self._media_analysis

    @property
    def preview_builder(self):
        if self._preview_builder is None:
            from services.preview_builder import PreviewBuilder

            self._preview_builder = PreviewBuilder(self.ffmpeg_service)
        return self._preview_builder

    @property
    def validation(self):
        if self._validation is None:
            from services.validation_service import ValidationService

            self._validation = ValidationService(self.ffmpeg_service)
        return self._validation

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
        value = str(value or "").strip()
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
        value = str(value or "").strip()
        if self._output_dir == value:
            return
        self._output_dir = value
        self.outputDirChanged.emit()
        self._remember_folder(value)
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Property(str, notify=watchFolderChanged)
    def watchFolder(self) -> str:
        return self._watch_folder

    @watchFolder.setter
    def watchFolder(self, value: str) -> None:
        value = str(value or "").strip()
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

    @QtCore.Property(bool, constant=True)
    def isWhisperAvailable(self) -> bool:
        from services.transcription_service import is_whisper_available

        return is_whisper_available()

    @QtCore.Property(str, notify=uiLanguageChanged)
    def uiLanguage(self) -> str:
        return self._ui_language

    @uiLanguage.setter
    def uiLanguage(self, value: str) -> None:
        self.setLanguage(value)

    @QtCore.Property(str, notify=languageChanged)
    def currentLanguage(self) -> str:
        return self._ui_language

    @QtCore.Property("QVariantList", notify=languageChanged)
    def availableLanguages(self) -> List[Dict[str, str]]:
        return [
            {"code": "uk", "label": translate("ukrainian", "uk")},
            {"code": "en", "label": translate("english", "en")},
            {"code": "pl", "label": translate("polish", "pl")},
            {"code": "de", "label": translate("german", "de")},
        ]

    @QtCore.Slot(str)
    def setLanguage(self, value: str) -> None:
        normalized = normalize_language(str(value or "uk"))
        if self._ui_language == normalized:
            return
        self._ui_language = normalized
        self.uiLanguageChanged.emit()
        self.languageChanged.emit()
        self._save_state()

    @QtCore.Slot(str, result=str)
    def tr(self, key: str) -> str:
        return self._tr(key)

    def _tr(self, key: str, **kwargs: Any) -> str:
        return translate(key, self._ui_language, **kwargs)

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
        if not self.history_store.entries:
            return "Історія запусків порожня."
        lines: List[str] = []
        for entry in self.history_store.entries[:8]:
            started_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("started_at", 0) or 0))
            results = entry.get("results", [])
            failed = sum(1 for item in results if item.get("status") == TaskStatus.FAILED)
            skipped = sum(1 for item in results if item.get("status") == TaskStatus.SKIPPED)
            cancelled = sum(1 for item in results if item.get("status") == TaskStatus.CANCELLED)
            lines.append(
                f"{started_at} | {entry.get('operation', '—')} | файлів {entry.get('total_files', 0)} | "
                f"failed {failed} | skipped {skipped} | cancelled {cancelled} | {entry.get('output_dir', '—')}"
            )
        return "\n".join(lines)

    @QtCore.Property(int, notify=queueStatsChanged)
    def queueCount(self) -> int:
        return len(self.queue_model.items())

    @QtCore.Property(int, notify=queueStatsChanged)
    def completedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {TaskStatus.SUCCESS, TaskStatus.SKIPPED})

    @QtCore.Property(int, notify=queueStatsChanged)
    def failedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.FAILED)

    @QtCore.Property(int, notify=queueStatsChanged)
    def skippedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.SKIPPED)

    @QtCore.Property(int, notify=queueStatsChanged)
    def runningCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {TaskStatus.RUNNING, TaskStatus.PAUSED})

    @QtCore.Property(int, notify=queueStatsChanged)
    def cancelledCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.CANCELLED)

    @QtCore.Property("QVariantList", notify=speedHistoryChanged)
    def speedHistory(self) -> List[Dict[str, float]]:
        return list(self._speed_history)

    @QtCore.Property("QVariantList", notify=fileTimingsChanged)
    def fileTimings(self) -> List[Dict[str, Any]]:
        return list(self._file_timings)

    @QtCore.Property("QVariantMap", notify=codecDistributionChanged)
    def codecDistribution(self) -> Dict[str, int]:
        return dict(self._codec_distribution)

    @QtCore.Property("QVariantList", notify=resourceHistoryChanged)
    def resourceHistory(self) -> List[Dict[str, float]]:
        return list(self._resource_history)

    @QtCore.Property(str, notify=resourceHistoryChanged)
    def cpuLoadText(self) -> str:
        return self._cpu_load_text

    @QtCore.Property(str, notify=resourceHistoryChanged)
    def gpuLoadText(self) -> str:
        return self._gpu_load_text

    @QtCore.Property(str, notify=resourceHistoryChanged)
    def ramLoadText(self) -> str:
        return self._ram_load_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionElapsedText(self) -> str:
        return self._session_elapsed_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionEtaText(self) -> str:
        return self._session_eta_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionAvgSpeedText(self) -> str:
        return self._session_avg_speed_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionInputText(self) -> str:
        return self._session_input_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionOutputText(self) -> str:
        return self._session_output_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionSavedText(self) -> str:
        return self._session_saved_text

    def _save_state(self, *, pending_recovery: Optional[bool] = None) -> None:
        self.settings_manager.save(
            recent_folders=self._recent_folders[:RECENT_FOLDERS_LIMIT],
            watch_folder=self._watch_folder,
            output_dir=self._output_dir,
            ffmpeg_path=self._ffmpeg_path,
            ui_language=self._ui_language,
            last_settings=self._last_settings_map,
            queue_items=[self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
            pending_recovery=self._is_running if pending_recovery is None else pending_recovery,
            onboarding_completed=True,
        )

    def _append_log(self, level: str, msg: str) -> None:
        self._log_lines.append(f"{level}: {msg}")
        self.log_model.append(level, msg)
        self.logAdded.emit(level, msg)

    def _set_status(self, text: str) -> None:
        if self._status_text == text:
            return
        self._status_text = text
        self.statusChanged.emit()

    def _set_progress(self, file_pct: float, total_pct: float) -> None:
        if self._file_progress != file_pct:
            self._file_progress = file_pct
            self.fileProgressChanged.emit()
        if self._total_progress != total_pct:
            self._total_progress = total_pct
            self.totalProgressChanged.emit()

    def _refresh_presets(self) -> None:
        self.presets_model.setStringList(self.preset_manager.names())

    def _refresh_recent_folders(self) -> None:
        self.recent_folders_model.setStringList(self._recent_folders)
        self.recentFoldersChanged.emit()

    def _remember_folder(self, folder: str) -> None:
        self._recent_folders = self.settings_manager.remember_folder(self._recent_folders, folder)
        self._refresh_recent_folders()

    def _set_output_preview(self, text: str) -> None:
        if self._output_preview_text == text:
            return
        self._output_preview_text = text
        self.outputPreviewChanged.emit()

    def _set_selected_preview(self, source: str, output: str, command: str = "—") -> None:
        source_value = source or "—"
        output_value = output or "—"
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
        self._refresh_session_stats()

    def _refresh_session_stats(self, *, total_eta: Optional[float] = None) -> None:
        elapsed = time.monotonic() - self._run_started_monotonic if self._run_started_monotonic else 0.0
        input_bytes = 0
        output_bytes = 0
        for item in self.queue_model.items():
            try:
                if item.path.exists():
                    input_bytes += item.path.stat().st_size
            except Exception:
                pass
            output_text = (item.last_output or "").split(";", 1)[0].strip()
            if not output_text:
                continue
            try:
                output_path = Path(output_text).expanduser()
                if output_path.exists():
                    output_bytes += output_path.stat().st_size
            except Exception:
                pass
        saved = max(input_bytes - output_bytes, 0)
        speeds = [point.get("speed", 0.0) for point in self._speed_history if point.get("speed", 0.0) > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        self._session_elapsed_text = format_time(elapsed)
        self._session_eta_text = format_time(total_eta) if total_eta is not None else self._session_eta_text
        self._session_avg_speed_text = f"{avg_speed:.1f}x" if avg_speed else "--"
        self._session_input_text = format_bytes(input_bytes)
        self._session_output_text = format_bytes(output_bytes)
        self._session_saved_text = format_bytes(saved)
        self.sessionStatsChanged.emit()

    def _refresh_codec_distribution(self) -> None:
        distribution: Dict[str, int] = {}
        for item in self.queue_model.items():
            info = self.media_info_cache.get(item.path) or item.probe_data
            codec = (info.vcodec if info else None) or "Unknown"
            codec = self._display_codec(codec)
            distribution[codec] = distribution.get(codec, 0) + 1
        self._codec_distribution = distribution
        self.codecDistributionChanged.emit(dict(self._codec_distribution))

    def _display_codec(self, codec: str) -> str:
        normalized = str(codec or "").lower()
        if normalized in {"h264", "libx264"}:
            return "H.264"
        if normalized in {"hevc", "h265", "libx265"}:
            return "H.265"
        if "av1" in normalized:
            return "AV1"
        if "vp9" in normalized:
            return "VP9"
        return codec or "Unknown"

    def _sample_resources(self) -> Dict[str, float]:
        cpu = 0.0
        ram = 0.0
        gpu = 0.0
        try:
            import psutil  # type: ignore

            cpu = float(psutil.cpu_percent(interval=None))
            ram = float(psutil.virtual_memory().percent)
        except Exception:
            pass
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=0.4,
            )
            if result.returncode == 0:
                values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
                if values:
                    gpu = max(values)
        except Exception:
            pass
        return {"cpu": cpu, "gpu": gpu, "ram": ram}

    def _append_resource_sample(self, now: float) -> None:
        if not self._run_started_monotonic:
            return
        sample = self._sample_resources()
        sample["time"] = now - self._run_started_monotonic
        self._resource_history.append(sample)
        self._resource_history = self._resource_history[-120:]
        self._cpu_load_text = f"CPU {sample['cpu']:.0f}%"
        self._gpu_load_text = f"GPU {sample['gpu']:.0f}%"
        self._ram_load_text = f"RAM {sample['ram']:.0f}%"
        self.resourceHistoryChanged.emit(list(self._resource_history))

    def _record_file_timing(self, path: Path, status: str) -> None:
        started = self._task_started_at.pop(path, None)
        if started is None:
            return
        duration = max(time.monotonic() - started, 0.0)
        name = path.name
        item = self.queue_model.item_by_path(path)
        self._file_timings = [item for item in self._file_timings if item.get("name") != name]
        self._file_timings.append(
            {
                "name": name,
                "duration": duration,
                "status": status,
                "compression": item.compression_ratio if item else 0.0,
                "predictedSize": item.predicted_output_bytes if item else 0,
            }
        )
        self._file_timings.sort(key=lambda item: float(item.get("duration") or 0), reverse=True)
        self._file_timings = self._file_timings[:10]
        self.fileTimingsChanged.emit(list(self._file_timings))

    @QtCore.Slot()
    def refreshEncoders(self) -> None:
        if self.ffmpegPath:
            self.ffmpeg_service.ffmpeg_path = self.ffmpegPath
        if not self.ffmpeg_service.ffmpeg_path:
            self._append_log("ERROR", self._tr("backend.ffmpeg_missing"))
            return
        self._append_log("INFO", "Перевіряю FFmpeg encoder-и...")
        threading.Thread(
            target=self._detect_encoders_async,
            args=(self.ffmpeg_service.ffmpeg_path,),
            daemon=True,
        ).start()

    def _detect_encoders_async(self, ffmpeg_path: str) -> None:
        ffprobe_path = find_ffprobe(ffmpeg_path)
        service = FfmpegService(ffmpeg_path, ffprobe_path)
        caps = service.detect_encoders()
        self.event_queue.put(("encoder_detection", ffmpeg_path, ffprobe_path, caps))

    def _apply_encoder_detection(self, ffmpeg_path: str, ffprobe_path: Optional[str], caps: set[str]) -> None:
        if self.ffmpegPath and str(ffmpeg_path) != self.ffmpegPath:
            return
        self.ffmpeg_service.ffmpeg_path = ffmpeg_path
        self.ffmpeg_service.ffprobe_path = ffprobe_path
        self.ffmpeg_service.encoder_caps = set(caps)
        summary = []
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
        self._encoder_info = f"Доступні: {', '.join(summary) if summary else 'немає даних'}"
        self.encoderInfoChanged.emit()
        self._append_log("OK", f"FFmpeg: {self.ffmpeg_service.ffmpeg_path}")
        self._append_log("OK" if self.ffmpeg_service.ffprobe_path else "WARN", f"FFprobe: {self.ffmpeg_service.ffprobe_path or 'не знайдено'}")
        self._save_state()

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
        self._show_onboarding = False
        self.onboardingChanged.emit()

    @QtCore.Slot(int, str)
    def useRecentFolder(self, index: int, target: str) -> None:
        if 0 <= index < len(self._recent_folders):
            if target == "watch":
                self.watchFolder = self._recent_folders[index]
            else:
                self.outputDir = self._recent_folders[index]

    @QtCore.Slot()
    def openOutputDir(self) -> None:
        folder = Path(self.outputDir).expanduser()
        if not folder.exists():
            QtWidgets.QMessageBox.warning(None, "Папка", "Папка виводу не існує.")
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
        elif output.parent.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(output.parent)))

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
            "*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.heic *.heif "
            "*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.wma *.aiff *.mka "
            "*.srt *.ass *.ssa *.vtt *.webvtt);;All Files (*)"
        )
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Додати файли", "", filt)
        paths = [Path(path) for path in files]
        if paths:
            self._remember_folder(str(paths[0].parent))
        self._add_paths(paths)

    @QtCore.Slot("QVariantList")
    def addDroppedUrls(self, urls: List[Any]) -> None:
        paths: List[Path] = []
        folders: List[Path] = []
        for value in urls:
            local_path = value.toLocalFile() if isinstance(value, QtCore.QUrl) else QtCore.QUrl(str(value)).toLocalFile()
            if not local_path:
                continue
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
            items = [path for path in folder.rglob("*") if path.is_file()]
        except Exception as exc:
            self.event_queue.put(("log", "ERROR", f"Не вдалося просканувати папку {folder}: {exc}"))
            return
        self.event_queue.put(("add_paths", items, str(folder)))

    def _add_paths(self, paths: List[Path]) -> None:
        added, duplicates, unsupported = self.queue_manager.build_items(paths, self.queue_model.paths_set())
        if added:
            self.queue_model.add_items(added)
            for item in added:
                self.queue_model.set_file_size(item.path)
                self._prefetch_probe_async(item.path, item.media_type)
                self._ensure_thumbnail_async(item.path, item.media_type)
            self._notify_queue_stats()
            self._refresh_codec_distribution()
            self._append_log("OK", self._tr("backend.added_files", count=len(added)))
            self._refresh_output_preview(dict(self._last_settings_map))
            self._save_state()
        if duplicates:
            self._append_log("INFO", self._tr("backend.duplicates_skipped", count=duplicates))
        if unsupported:
            self._append_log("WARN", self._tr("backend.unsupported_skipped", count=unsupported))
        if not added and not duplicates and not unsupported:
            self._append_log("WARN", self._tr("backend.no_tasks"))

    @QtCore.Slot()
    def deduplicateQueue(self) -> None:
        unique, removed = self.queue_manager.deduplicate_by_path(self.queue_model.items())
        self.queue_model.set_items(unique)
        self._notify_queue_stats()
        self._refresh_codec_distribution()
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
        unique, removed, log_lines = self.queue_manager.deduplicate_by_hash(items)
        self.event_queue.put(("dedupe_hash_done", unique, removed, log_lines))

    def _move_selected(self, indices: List[int], direction: str) -> None:
        items = self.queue_manager.reorder(self.queue_model.items(), indices, direction)
        self.queue_model.set_items(items)
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    def _move_selected_paths(self, paths: List[Any], direction: str) -> None:
        selected_paths = self.queue_manager.paths_from_payload(paths)
        indices = self.queue_manager.selected_indices_for_paths(self.queue_model.items(), selected_paths)
        self._move_selected(indices, direction)

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
        items = self.queue_manager.move_path_to_index(
            self.queue_model.items(),
            Path(str(path_text or "").strip()).expanduser(),
            target_index,
        )
        self.queue_model.set_items(items)
        self._notify_queue_stats()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Slot("QVariantList")
    def removeSelected(self, indices: List[int]) -> None:
        items, removed = self.queue_manager.remove_indices(self.queue_model.items(), indices)
        self.queue_model.set_items(items)
        self._after_queue_removed(removed)

    @QtCore.Slot("QVariantList")
    def removeSelectedPaths(self, paths: List[Any]) -> None:
        selected = self.queue_manager.paths_from_payload(paths)
        items, removed = self.queue_manager.remove_paths(self.queue_model.items(), selected)
        self.queue_model.set_items(items)
        self._after_queue_removed(removed)

    @QtCore.Slot(str)
    def removeTaskPath(self, path_text: str) -> None:
        self.removeSelectedPaths([path_text])

    def _after_queue_removed(self, removed: int) -> None:
        if removed <= 0:
            return
        self._selected_index = -1
        self._selected_path = ""
        self._notify_queue_stats()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено: {removed}")

    @QtCore.Slot()
    def clearQueue(self) -> None:
        self.queue_model.set_items([])
        self._selected_index = -1
        self._selected_path = ""
        self._clear_info()
        self._set_output_preview("Черга порожня.")
        self._set_selected_preview("—", "—")
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._save_state()
        self._append_log("INFO", "Чергу очищено")

    @QtCore.Slot()
    def exportLog(self) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-log.txt"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати лог", str(default_path), "Text (*.txt)")
        if path:
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
            QtWidgets.QMessageBox.warning(None, "Watch folder", "Обери існуючу папку для моніторингу.")
            return
        try:
            self.watch_service.start(folder)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(None, "Watch folder", str(exc))
            return
        self._watch_seen = set()
        self._watch_running = True
        self.watchRunningChanged.emit()
        self._append_log("OK", f"Watch folder активовано: {folder}")

    @QtCore.Slot()
    def stopWatching(self) -> None:
        self.watch_service.stop()
        self._watch_running = False
        self.watchRunningChanged.emit()
        self._watch_timer.stop()
        self._append_log("INFO", "Watch folder зупинено")

    def _on_watch_files(self, paths: List[Path]) -> None:
        folder = self.watch_service.folder
        self.event_queue.put(("add_paths", list(paths), str(folder) if folder else ""))
        self.event_queue.put(("log", "INFO", f"Watch folder додав файлів: {len(paths)}"))

    def _scan_watch_folder(self) -> None:
        if not self._watch_running or not self.watchFolder:
            return
        base = Path(self.watchFolder).expanduser()
        if not base.exists():
            self.stopWatching()
            return
        new_paths = self.watch_service.scan_once()
        if new_paths:
            self._add_paths(new_paths)
            self._append_log("INFO", f"Watch folder додав файлів: {len(new_paths)}")

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
        self._info_name = task.path.name
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = task.size_text or "—"
        self._info_container = "—"
        self._info_analysis = f"Тип: {task.media_type}"
        self._info_warnings = task.last_error or "—"
        self.infoChanged.emit()
        self.taskOverrideLoaded.emit(dict(task.overrides))
        self._refresh_output_preview(dict(self._last_settings_map))
        info = self.media_info_cache.get(task.path)
        if info:
            self._update_info(info)
            return
        if self.ffmpeg_service.ffprobe_path and task.media_type in {"video", "audio"}:
            self.queue_model.update_task_state(task.path, TaskStatus.ANALYZING)
            self._notify_queue_stats()
            threading.Thread(target=self._probe_media_async, args=(task.path,), daemon=True).start()
        self._ensure_thumbnail_async(task.path, task.media_type)

    @QtCore.Slot(str)
    def selectQueuePath(self, path_text: str) -> None:
        self.selectQueueIndex(self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser()))

    @QtCore.Slot(int, result=str)
    def queuePathAt(self, index: int) -> str:
        task = self.queue_model.item_at(index)
        return str(task.path) if task else ""

    def _probe_media_async(self, path: Path) -> None:
        info = self.media_analysis.probe(path)
        self.event_queue.put(("media_info", path, info))

    def _prefetch_probe_async(self, path: Path, media_kind: str) -> None:
        if media_kind not in {"video", "audio"}:
            return
        if not self.ffmpeg_service.ffprobe_path or path in self.media_info_cache or path in self._probe_pending:
            return
        self._probe_pending.add(path)

        def run_probe() -> None:
            info = self.media_analysis.probe(path)
            self.event_queue.put(("media_info", path, info))

        self._probe_executor.submit(run_probe)

    def _ensure_thumbnail_async(self, path: Path, media_kind: str) -> None:
        if media_kind == "image":
            self.queue_model.set_thumbnail(path, str(path))
            return
        if media_kind != "video":
            return
        current = self.queue_model.item_by_path(path)
        if current and current.thumbnail_path:
            return
        threading.Thread(target=self._create_thumbnail_async, args=(path, media_kind), daemon=True).start()

    def _create_thumbnail_async(self, path: Path, media_kind: str) -> None:
        thumbnail = self.media_analysis.thumbnail_for(path, media_kind)
        if thumbnail:
            self.event_queue.put(("thumbnail", path, thumbnail))

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
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати водяний знак", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)")
        if path:
            self.watermarkPicked.emit(path)

    @QtCore.Slot()
    def pickCoverArt(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати cover art", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)")
        if path:
            self.coverArtPicked.emit(path)

    @QtCore.Slot()
    def pickAudioReplace(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати аудіо для заміни", "", "Audio (*.mp3 *.m4a *.aac *.wav *.flac *.opus *.ogg *.mp4 *.mov *.mkv);;All Files (*)")
        if path:
            self.audioReplacePicked.emit(path)

    @QtCore.Slot()
    def pickFont(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати шрифт", "", "Fonts (*.ttf *.otf);;All Files (*)")
        if path:
            self.fontPicked.emit(path)

    @QtCore.Slot()
    def pickSubtitle(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Вибрати субтитри", "", "Subtitles (*.srt *.ass *.ssa *.vtt *.webvtt);;All Files (*)")
        if path:
            self.subtitlePicked.emit(path)

    @QtCore.Slot("QVariantMap", result="QVariantMap")
    def validateSettings(self, settings_map: Dict[str, Any]) -> Dict[str, Any]:
        return self.validation.validate(
            dict(settings_map),
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            ffmpeg_path=self.ffmpegPath,
            include_queue=True,
        )

    def _refresh_output_preview(self, settings_map: Dict[str, Any]) -> None:
        summary = self.preview_builder.build(
            settings_map,
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            selected_path=self._selected_path,
            media_info=self.media_info_cache,
        )
        for item in summary.items:
            self.queue_model.set_preview_output(item.source_path, str(item.output_path))
        self._refresh_size_predictions(settings_map)
        self._set_output_preview(summary.text)
        self._set_selected_preview(summary.selected_source, summary.selected_output, summary.selected_command)

    def _refresh_size_predictions(self, settings_map: Dict[str, Any]) -> None:
        for task in self.queue_model.items():
            merged_map = merge_settings_maps(settings_map, task.overrides)
            settings = settings_map_to_model(merged_map, defaults=ConversionSettings())
            info = self.media_info_cache.get(task.path) or task.probe_data
            input_bytes = int((info.size_bytes if info else None) or task.input_bytes or 0)
            if not input_bytes:
                try:
                    input_bytes = task.path.stat().st_size
                except Exception:
                    input_bytes = 0
            if settings.target_size_mb:
                predicted = int(float(settings.target_size_mb) * 1024 * 1024)
            else:
                predicted = int(input_bytes * prediction_factor(settings.performance_profile)) if input_bytes else 0
            self.queue_model.set_prediction(task.path, predicted)

    @QtCore.Slot("QVariantMap")
    def refreshOutputPreview(self, settings_map: Dict[str, Any]) -> None:
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        self._save_state()

    @QtCore.Slot()
    def restoreSession(self) -> None:
        if self.queue_model.rowCount() > 0:
            self._append_log("INFO", f"Відновлено чергу: {self.queue_model.rowCount()} елементів.")
        if self.settings_manager.state.get("pending_recovery"):
            self._append_log("WARN", "Попередній запуск завершився аварійно; активні задачі повернено у чергу.")
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
            "version": 2,
            "exported_at": time.time(),
            "output_dir": self.outputDir,
            "ffmpeg_path": self.ffmpegPath,
            "settings": dict(settings_map),
            "queue_items": [self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
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
        queue_items = self.queue_manager.deserialize_tasks(payload.get("queue_items", []), pending_recovery=False)
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
        content = f"@echo off\r\n{command}\r\n" if os.name == "nt" else f"#!/usr/bin/env sh\n{command}\n"
        Path(path).write_text(content, encoding="utf-8")
        self._append_log("OK", f"Команду експортовано: {path}")

    @QtCore.Slot("QVariantMap")
    def copyDryRunCommand(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        if self._selected_preview_command and self._selected_preview_command != "—":
            QtWidgets.QApplication.clipboard().setText(self._selected_preview_command)
            self._append_log("OK", "Dry-run команду скопійовано.")

    @QtCore.Slot()
    def clearHistory(self) -> None:
        self.history_store.clear()
        self.history_model.set_entries(self.history_store.entries)
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
        paths = [Path(str(result.get("path"))) for result in entry.get("results", []) if result.get("path")]
        if paths:
            self._add_paths(paths)
        self._start_conversion(settings, only_paths={path.expanduser() for path in paths})

    def _build_run_tasks(
        self,
        settings_map: Dict[str, Any],
        *,
        failed_only: bool = False,
        only_paths: Optional[set[Path]] = None,
    ) -> List[TaskItem]:
        tasks: List[TaskItem] = []
        for item in self.queue_model.items():
            if failed_only and item.status not in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
                continue
            if only_paths is not None and item.path not in only_paths:
                continue
            merged_map = merge_settings_maps(settings_map, item.overrides)
            resolved = settings_map_to_model(merged_map, defaults=ConversionSettings())
            tasks.append(
                TaskItem(
                    path=item.path,
                    media_type=item.media_type,
                    status=TaskStatus.QUEUED,
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
        if self.runner.is_running:
            return
        if self.ffmpegPath:
            self.ffmpeg_service.ffmpeg_path = self.ffmpegPath
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        preflight = self.validation.validate(
            settings_map,
            tasks=self.queue_model.items(),
            output_dir=self.outputDir,
            ffmpeg_path=self.ffmpegPath,
            include_queue=True,
            only_paths=only_paths,
        )
        if not preflight.get("ok"):
            details = "\n".join(str(msg) for msg in dict(preflight.get("errors") or {}).values())
            QtWidgets.QMessageBox.critical(None, "Preflight", details or self._tr("backend.preflight_blocked", summary=""))
            self._append_log("ERROR", self._tr("backend.preflight_blocked", summary=preflight.get("summary")))
            return
        for warning in preflight.get("warnings") or []:
            self._append_log("WARN", f"Preflight: {warning}")

        run_tasks = self._build_run_tasks(settings_map, failed_only=failed_only, only_paths=only_paths)
        if not run_tasks:
            QtWidgets.QMessageBox.information(None, self._tr("queue"), self._tr("backend.no_tasks"))
            return
        out_dir = Path(self.outputDir).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, self._tr("status.failed"), self._tr("backend.output_dir_error", error=exc))
            return

        paths = {task.path for task in run_tasks}
        self.queue_model.clear_statuses(paths=paths)
        self._notify_queue_stats()
        base_settings = settings_map_to_model(settings_map, defaults=ConversionSettings())
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        self._set_progress(0.0, 0.0)
        self._active_task_path = ""
        self._run_started_monotonic = time.monotonic()
        self._last_analytics_emit = 0.0
        self._last_resource_emit = 0.0
        self._speed_history = []
        self._file_timings = []
        self._resource_history = []
        self.speedHistoryChanged.emit([])
        self.fileTimingsChanged.emit([])
        self.resourceHistoryChanged.emit([])
        self.converter.prefetched_media_info = dict(self.media_info_cache)
        self._session_elapsed_text = "00:00"
        self._session_eta_text = "--:--"
        self._session_avg_speed_text = "--"
        self._refresh_session_stats(total_eta=None)
        self._file_progress_text = "Файл: --"
        self.fileProgressTextChanged.emit()
        self._total_progress_text = "Всього: --"
        self.totalProgressTextChanged.emit()
        self._is_running = True
        self.isRunningChanged.emit()
        self._is_paused = False
        self.isPausedChanged.emit()
        self._set_status(self._tr("backend.conversion_started"))
        self._save_state(pending_recovery=True)
        self.runner.start(run_tasks, base_settings, out_dir)

    @QtCore.Slot("QVariantMap")
    def startConversion(self, settings_map: Dict[str, Any]) -> None:
        self._start_conversion(dict(settings_map), failed_only=False)

    @QtCore.Slot(str, "QVariantMap")
    def startConversionForPath(self, path_text: str, settings_map: Dict[str, Any]) -> None:
        task_path = Path(str(path_text or "").strip()).expanduser()
        if self.queue_model.item_by_path(task_path) is None:
            return
        self._start_conversion(dict(settings_map), only_paths={task_path})

    @QtCore.Slot()
    def retryFailed(self) -> None:
        if self._is_running:
            return
        if not self._last_settings_map:
            self._append_log("WARN", "Немає попередніх налаштувань для retry.")
            return
        self._start_conversion(dict(self._last_settings_map), failed_only=True)

    @QtCore.Slot(str)
    def retryTaskPath(self, path_text: str) -> None:
        if self._is_running or not self._last_settings_map:
            return
        task_path = Path(str(path_text or "").strip()).expanduser()
        if self.queue_model.item_by_path(task_path) is None:
            return
        self._start_conversion(dict(self._last_settings_map), only_paths={task_path})

    @QtCore.Slot()
    def stopConversion(self) -> None:
        if not self._is_running:
            return
        self._set_status("Зупинка після поточного файлу...")
        self.runner.stop()

    @QtCore.Slot()
    def pauseConversion(self) -> None:
        if not self._is_running:
            return
        self.runner.pause()
        if not self._is_paused:
            self._is_paused = True
            self.isPausedChanged.emit()
        for item in self.queue_model.items():
            if item.status == TaskStatus.RUNNING:
                self.queue_model.update_task_state(item.path, TaskStatus.PAUSED)
        self._notify_queue_stats()
        self._set_status("Пауза")

    @QtCore.Slot()
    def resumeConversion(self) -> None:
        self.runner.resume()
        if self._is_paused:
            self._is_paused = False
            self.isPausedChanged.emit()
        for item in self.queue_model.items():
            if item.status == TaskStatus.PAUSED:
                self.queue_model.update_task_state(item.path, TaskStatus.RUNNING)
        self._notify_queue_stats()
        if self._is_running:
            self._set_status("Конвертація продовжується...")

    @QtCore.Slot()
    def skipCurrentFile(self) -> None:
        if self._is_running:
            self.runner.skip_current()
            self._set_status("Пропускаю поточний файл...")

    @QtCore.Slot(str)
    def loadPreset(self, name: str) -> None:
        data = self.preset_manager.get(name)
        if data:
            self.presetLoaded.emit(data)
            self._append_log("OK", f"Пресет завантажено: {name}")

    @QtCore.Slot(str, "QVariantMap")
    def savePreset(self, name: str, settings_map: Dict[str, Any]) -> None:
        if not name:
            QtWidgets.QMessageBox.warning(None, "Пресети", "Введи назву пресету.")
            return
        if self.preset_manager.get(name):
            answer = QtWidgets.QMessageBox.question(None, "Пресети", "Пресет уже існує. Перезаписати?")
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self.preset_manager.save(name, dict(settings_map))
        self._refresh_presets()
        self._append_log("OK", f"Пресет збережено: {name}")

    @QtCore.Slot(str)
    def deletePreset(self, name: str) -> None:
        if not name:
            return
        answer = QtWidgets.QMessageBox.question(None, "Пресети", f"Видалити пресет '{name}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        if self.preset_manager.delete(name):
            self._refresh_presets()
            self._append_log("OK", f"Пресет видалено: {name}")

    @QtCore.Slot(int, "QVariantMap")
    def saveTaskOverride(self, index: int, override_map: Dict[str, Any]) -> None:
        task = self.queue_model.item_at(index)
        if task is None:
            return
        task.overrides = dict(override_map)
        self.queue_model.update_item(index, task)
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("OK", f"Override збережено для: {task.path.name}")
        self.taskOverrideLoaded.emit(dict(task.overrides))

    @QtCore.Slot(str, "QVariantMap")
    def saveTaskOverrideByPath(self, path_text: str, override_map: Dict[str, Any]) -> None:
        index = self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser())
        self.saveTaskOverride(index, override_map)

    @QtCore.Slot(str, "QVariantMap")
    def updateTaskOverrideByPath(self, path_text: str, override_map: Dict[str, Any]) -> None:
        index = self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser())
        task = self.queue_model.item_at(index)
        if task is None:
            return
        merged = dict(task.overrides)
        for key, value in dict(override_map or {}).items():
            if value not in (None, ""):
                merged[str(key)] = value
        task.overrides = merged
        self.queue_model.update_item(index, task)
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("OK", f"Override оновлено для: {task.path.name}")
        self.taskOverrideLoaded.emit(dict(task.overrides))

    @QtCore.Slot("QVariantList", "QVariantMap")
    def saveBulkOverride(self, paths: List[Any], override_map: Dict[str, Any]) -> None:
        selected_paths = self.queue_manager.paths_from_payload(paths)
        changed = 0
        for idx, task in enumerate(self.queue_model.items()):
            if task.path not in selected_paths:
                continue
            task.overrides = dict(override_map)
            self.queue_model.update_item(idx, task)
            changed += 1
        if changed:
            self._refresh_output_preview(dict(self._last_settings_map))
            self._save_state()
            self._append_log("OK", f"Bulk override застосовано: {changed}")

    @QtCore.Slot(int)
    def clearTaskOverride(self, index: int) -> None:
        task = self.queue_model.item_at(index)
        if task is None:
            return
        task.overrides = {}
        self.queue_model.update_item(index, task)
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self.taskOverrideLoaded.emit({})

    @QtCore.Slot(str)
    def clearTaskOverrideByPath(self, path_text: str) -> None:
        index = self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser())
        self.clearTaskOverride(index)

    def _record_history(self, entry: Dict[str, Any]) -> None:
        self.history_store.add(entry)
        self.history_model.set_entries(self.history_store.entries)
        self.historyChanged.emit()

    def _cancel_active_items(self) -> None:
        for item in self.queue_model.items():
            if item.status in {TaskStatus.ANALYZING, TaskStatus.RUNNING, TaskStatus.PAUSED}:
                self.queue_model.update_task_state(item.path, TaskStatus.CANCELLED, "Скасовано користувачем")
        self._notify_queue_stats()

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                etype = event[0]
                if etype == "log":
                    _, level, msg = event
                    self._append_log(level, msg)
                elif etype == "encoder_detection":
                    _, ffmpeg_path, ffprobe_path, caps = event
                    self._apply_encoder_detection(ffmpeg_path, ffprobe_path, caps)
                elif etype == "status":
                    _, msg = event
                    self._set_status(msg)
                elif etype == "progress":
                    if len(event) >= 8:
                        _, file_pct, out_time, duration, file_eta, total_pct, total_eta, speed = event
                    else:
                        _, file_pct, out_time, duration, file_eta, total_pct, total_eta = event
                        speed = None
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
                    if self._active_task_path and file_pct is not None:
                        self.queue_model.set_task_progress(
                            Path(self._active_task_path),
                            file_pct,
                            format_time(file_eta),
                            f"{float(speed):.1f}x" if speed else "",
                        )
                    now = time.monotonic()
                    if speed and self._run_started_monotonic and now - self._last_analytics_emit >= ANALYTICS_EMIT_INTERVAL_SEC:
                        self._last_analytics_emit = now
                        self._speed_history.append(
                            {
                                "time": now - self._run_started_monotonic,
                                "speed": float(speed),
                            }
                        )
                        self._speed_history = self._speed_history[-120:]
                        self.speedHistoryChanged.emit(list(self._speed_history))
                    if self._run_started_monotonic and now - self._last_resource_emit >= RESOURCE_SAMPLE_INTERVAL_SEC:
                        self._last_resource_emit = now
                        self._append_resource_sample(now)
                    self._refresh_session_stats(total_eta=total_eta)
                elif etype == "task_progress":
                    _, path, file_pct, file_eta, speed, total_pct, total_eta = event
                    self.queue_model.set_task_progress(
                        path,
                        file_pct or 0.0,
                        format_time(file_eta),
                        f"{float(speed):.1f}x" if speed else "",
                    )
                    self._file_progress_text = (
                        f"{Path(path).name}: {int((file_pct or 0.0) * 100):02d}% • ETA {format_time(file_eta)}"
                    )
                    self.fileProgressTextChanged.emit()
                    self._total_progress_text = f"Всього: {int(total_pct * 100):02d}% • ETA {format_time(total_eta)}"
                    self.totalProgressTextChanged.emit()
                    self._set_progress(file_pct or 0.0, total_pct)
                    now = time.monotonic()
                    if speed and self._run_started_monotonic and now - self._last_analytics_emit >= ANALYTICS_EMIT_INTERVAL_SEC:
                        self._last_analytics_emit = now
                        self._speed_history.append(
                            {
                                "time": now - self._run_started_monotonic,
                                "speed": float(speed),
                            }
                        )
                        self._speed_history = self._speed_history[-120:]
                        self.speedHistoryChanged.emit(list(self._speed_history))
                    if self._run_started_monotonic and now - self._last_resource_emit >= RESOURCE_SAMPLE_INTERVAL_SEC:
                        self._last_resource_emit = now
                        self._append_resource_sample(now)
                    self._refresh_session_stats(total_eta=total_eta)
                elif etype == "set_total":
                    self._set_progress(0.0, 0.0)
                elif etype == "done":
                    _, stopped = event
                    self._active_task_path = ""
                    self._is_running = False
                    self.isRunningChanged.emit()
                    if self._is_paused:
                        self._is_paused = False
                        self.isPausedChanged.emit()
                    if stopped:
                        self._cancel_active_items()
                    self._set_status(self._tr("backend.stopped") if stopped else self._tr("backend.ready"))
                    self._refresh_session_stats(total_eta=0.0)
                    self._save_state(pending_recovery=False)
                elif etype == "media_info":
                    _, path, info = event
                    self._probe_pending.discard(path)
                    if info:
                        self.media_info_cache[path] = info
                        self.converter.prefetched_media_info[path] = info
                        self.queue_model.set_media_summary(path, info)
                        self._refresh_codec_distribution()
                    current = self.queue_model.item_by_path(path)
                    if current and current.status == TaskStatus.ANALYZING:
                        self.queue_model.update_task_state(path, TaskStatus.READY)
                        self._notify_queue_stats()
                    selected = self.queue_model.item_at(self._selected_index)
                    if info and selected and selected.path == path:
                        self._update_info(info)
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
                    self._refresh_output_preview(dict(self._last_settings_map))
                    self._save_state()
                    for line in log_lines:
                        self._append_log("INFO", line)
                    self._append_log("INFO", f"Видалено hash-дублікатів: {removed}")
                elif etype == "task_state":
                    _, path, status, message, output_path = event
                    if status in {TaskStatus.RUNNING, TaskStatus.PAUSED}:
                        self._active_task_path = str(path)
                        self._task_started_at.setdefault(path, time.monotonic())
                    self.queue_model.update_task_state(path, status, message, output_path)
                    if status == TaskStatus.SUCCESS and output_path:
                        self.queue_model.set_output_stats(path, output_path)
                    if status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}:
                        self._record_file_timing(path, status)
                        if str(path) == self._active_task_path:
                            self._active_task_path = ""
                    self._notify_queue_stats()
                    self._save_state()
                elif etype == "run_summary":
                    _, summary = event
                    if isinstance(summary, dict):
                        self._record_history(summary)
        except queue.Empty:
            return
