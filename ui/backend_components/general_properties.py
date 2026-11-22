from __future__ import annotations

from .common import APP_TITLE, APP_VERSION, Any, Dict, List, Path, QtCore, TaskStatus, normalize_language, time, translate
from .core import CoreMixin


class GeneralPropertiesMixin:
    @QtCore.Property(str, constant=True)
    def appTitle(self) -> str:
        return APP_TITLE

    @QtCore.Property(str, constant=True)
    def appVersion(self) -> str:
        return APP_VERSION

    @QtCore.Property(QtCore.QObject, constant=True)
    def queueModel(self) -> QtCore.QObject:
        return self.queue_model

    @QtCore.Property(QtCore.QObject, constant=True)
    def logModel(self) -> QtCore.QObject:
        return self.log_model

    @QtCore.Property(QtCore.QObject, constant=True)
    def historyModel(self) -> QtCore.QObject:
        return self.history_model

    @QtCore.Property("QStringList", notify=CoreMixin.presetsChanged)
    def builtinPresetNames(self) -> list[str]:
        return self.preset_manager.builtin_names()

    @QtCore.Property("QStringList", notify=CoreMixin.presetsChanged)
    def customPresetNames(self) -> list[str]:
        return self.preset_manager.custom_names()

    @QtCore.Property(QtCore.QObject, constant=True)
    def presetsModel(self) -> QtCore.QObject:
        return self.presets_model

    @QtCore.Property(QtCore.QObject, notify=CoreMixin.recentFoldersChanged)
    def recentFoldersModel(self) -> QtCore.QObject:
        return self.recent_folders_model

    @QtCore.Property(str, notify=CoreMixin.ffmpegPathChanged)
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

    @QtCore.Property(str, notify=CoreMixin.outputDirChanged)
    def outputDir(self) -> str:
        return self._output_dir

    @outputDir.setter
    def outputDir(self, value: str) -> None:
        value = str(value or "").strip()
        was_configured = self._output_dir_configured
        self._output_dir_configured = bool(value)
        if self._output_dir == value:
            if was_configured != self._output_dir_configured:
                self.outputDirConfiguredChanged.emit()
                self._save_state()
            return
        self._output_dir = value
        self.outputDirChanged.emit()
        if was_configured != self._output_dir_configured:
            self.outputDirConfiguredChanged.emit()
        if value:
            self._remember_folder(value)
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Property(bool, notify=CoreMixin.outputDirConfiguredChanged)
    def outputDirConfigured(self) -> bool:
        return self._output_dir_configured

    @QtCore.Property(str, notify=CoreMixin.watchFolderChanged)
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

    @QtCore.Property(bool, notify=CoreMixin.watchRunningChanged)
    def watchRunning(self) -> bool:
        return self._watch_running

    @QtCore.Property(bool, notify=CoreMixin.onboardingChanged)
    def onboardingVisible(self) -> bool:
        return self._show_onboarding

    @QtCore.Property(bool, notify=CoreMixin.whisperModelsChanged)
    def isWhisperAvailable(self) -> bool:
        from services.transcription_service import is_whisper_available

        return is_whisper_available()

    @QtCore.Property(str, notify=CoreMixin.uiLanguageChanged)
    def uiLanguage(self) -> str:
        return self._ui_language

    @uiLanguage.setter
    def uiLanguage(self, value: str) -> None:
        self.setLanguage(value)

    @QtCore.Property(str, notify=CoreMixin.languageChanged)
    def currentLanguage(self) -> str:
        return self._ui_language

    @QtCore.Property("QVariantList", notify=CoreMixin.languageChanged)
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

    @QtCore.Property(str, notify=CoreMixin.encoderInfoChanged)
    def encoderInfo(self) -> str:
        return self._encoder_info

    @QtCore.Property(str, notify=CoreMixin.statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @QtCore.Property(float, notify=CoreMixin.fileProgressChanged)
    def fileProgress(self) -> float:
        return self._file_progress

    @QtCore.Property(float, notify=CoreMixin.totalProgressChanged)
    def totalProgress(self) -> float:
        return self._total_progress

    @QtCore.Property(str, notify=CoreMixin.fileProgressTextChanged)
    def fileProgressText(self) -> str:
        return self._file_progress_text

    @QtCore.Property(str, notify=CoreMixin.totalProgressTextChanged)
    def totalProgressText(self) -> str:
        return self._total_progress_text

    @QtCore.Property(bool, notify=CoreMixin.youtubeDownloadChanged)
    def youtubeDownloadRunning(self) -> bool:
        return self._youtube_download_running

    @QtCore.Property(float, notify=CoreMixin.youtubeDownloadChanged)
    def youtubeDownloadProgress(self) -> float:
        return self._youtube_download_progress

    @QtCore.Property(str, notify=CoreMixin.youtubeDownloadChanged)
    def youtubeDownloadStatus(self) -> str:
        return self._youtube_download_status

    @QtCore.Property("QVariantList", notify=CoreMixin.youtubeHistoryChanged)
    def youtubeDownloadHistory(self) -> List[str]:
        return list(self._youtube_history)

    @QtCore.Property(str, notify=CoreMixin.youtubeHistoryChanged)
    def youtubeCookiesPath(self) -> str:
        return self._youtube_cookies_path

    @QtCore.Property(bool, notify=CoreMixin.isRunningChanged)
    def isRunning(self) -> bool:
        return self._is_running

    @QtCore.Property(bool, notify=CoreMixin.isPausedChanged)
    def isPaused(self) -> bool:
        return self._is_paused

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoName(self) -> str:
        return self._info_name

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoDuration(self) -> str:
        return self._info_duration

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoCodec(self) -> str:
        return self._info_codec

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoRes(self) -> str:
        return self._info_res

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoSize(self) -> str:
        return self._info_size

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoContainer(self) -> str:
        return self._info_container

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoAnalysis(self) -> str:
        return self._info_analysis

    @QtCore.Property(str, notify=CoreMixin.infoChanged)
    def infoWarnings(self) -> str:
        return self._info_warnings

    @QtCore.Property(str, notify=CoreMixin.outputPreviewChanged)
    def outputPreviewText(self) -> str:
        return self._output_preview_text

    @QtCore.Property(str, notify=CoreMixin.outputPreviewChanged)
    def selectedPreviewSource(self) -> str:
        return self._selected_preview_source

    @QtCore.Property(str, notify=CoreMixin.outputPreviewChanged)
    def selectedPreviewOutput(self) -> str:
        return self._selected_preview_output

    @QtCore.Property(str, notify=CoreMixin.outputPreviewChanged)
    def selectedPreviewCommand(self) -> str:
        return self._selected_preview_command

    @QtCore.Property(str, notify=CoreMixin.historyChanged)
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

    @QtCore.Property(int, notify=CoreMixin.queueStatsChanged)
    def queueCount(self) -> int:
        return len(self.queue_model.items())

    @QtCore.Property(int, notify=CoreMixin.queueStatsChanged)
    def completedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {TaskStatus.SUCCESS, TaskStatus.SKIPPED})

    @QtCore.Property(int, notify=CoreMixin.queueStatsChanged)
    def failedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.FAILED)

    @QtCore.Property(int, notify=CoreMixin.queueStatsChanged)
    def skippedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.SKIPPED)

    @QtCore.Property(int, notify=CoreMixin.queueStatsChanged)
    def runningCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {TaskStatus.RUNNING, TaskStatus.PAUSED})

    @QtCore.Property(int, notify=CoreMixin.queueStatsChanged)
    def cancelledCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.CANCELLED)

    @QtCore.Property("QVariantList", notify=CoreMixin.speedHistoryChanged)
    def speedHistory(self) -> List[Dict[str, float]]:
        return list(self._speed_history)

    @QtCore.Property("QVariantList", notify=CoreMixin.fileTimingsChanged)
    def fileTimings(self) -> List[Dict[str, Any]]:
        return list(self._file_timings)

    @QtCore.Property("QVariantMap", notify=CoreMixin.codecDistributionChanged)
    def codecDistribution(self) -> Dict[str, int]:
        return dict(self._codec_distribution)

    @QtCore.Property("QVariantList", notify=CoreMixin.resourceHistoryChanged)
    def resourceHistory(self) -> List[Dict[str, float]]:
        return list(self._resource_history)

    @QtCore.Property(str, notify=CoreMixin.resourceHistoryChanged)
    def cpuLoadText(self) -> str:
        return self._cpu_load_text

    @QtCore.Property(str, notify=CoreMixin.resourceHistoryChanged)
    def gpuLoadText(self) -> str:
        return self._gpu_load_text

    @QtCore.Property(str, notify=CoreMixin.resourceHistoryChanged)
    def ramLoadText(self) -> str:
        return self._ram_load_text

    @QtCore.Property(str, notify=CoreMixin.sessionStatsChanged)
    def sessionElapsedText(self) -> str:
        return self._session_elapsed_text

    @QtCore.Property(str, notify=CoreMixin.sessionStatsChanged)
    def sessionEtaText(self) -> str:
        return self._session_eta_text

    @QtCore.Property(str, notify=CoreMixin.sessionStatsChanged)
    def sessionAvgSpeedText(self) -> str:
        return self._session_avg_speed_text

    @QtCore.Property(str, notify=CoreMixin.sessionStatsChanged)
    def sessionInputText(self) -> str:
        return self._session_input_text

    @QtCore.Property(str, notify=CoreMixin.sessionStatsChanged)
    def sessionOutputText(self) -> str:
        return self._session_output_text

    @QtCore.Property(str, notify=CoreMixin.sessionStatsChanged)
    def sessionSavedText(self) -> str:
        return self._session_saved_text

    @QtCore.Property("QVariantList", notify=CoreMixin.youtubeDownloadChanged)
    def youtubeDownloadQueue(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self._youtube_download_queue]

    @QtCore.Property(str, notify=CoreMixin.youtubeDownloadChanged)
    def youtubeCookiesStatus(self) -> str:
        path_text = str(self._youtube_cookies_path or "").strip()
        if not path_text:
            return "Cookies: не підключено"
        path = Path(path_text).expanduser()
        if path.is_file():
            return "Cookies: підключено"
        return "Cookies: файл не знайдено"

    @QtCore.Property(str, notify=CoreMixin.youtubeDownloadChanged)
    def youtubePlaylistPreview(self) -> str:
        return self._youtube_playlist_preview

    @QtCore.Property("QVariantMap", notify=CoreMixin.youtubeDownloadChanged)
    def youtubePreviewInfo(self) -> Dict[str, Any]:
        return dict(self._youtube_preview_info)

    @QtCore.Property("QVariantList", notify=CoreMixin.youtubeDownloadChanged)
    def youtubeDownloadLog(self) -> List[str]:
        return list(self._youtube_download_log)

    @QtCore.Property(bool, notify=CoreMixin.youtubeDownloadChanged)
    def ytdlpUpdateRunning(self) -> bool:
        return self._ytdlp_update_running

    @QtCore.Property(bool, notify=CoreMixin.preflightChanged)
    def preflightOk(self) -> bool:
        return bool(self._preflight_result.get("ok", True))

    @QtCore.Property(str, notify=CoreMixin.preflightChanged)
    def preflightSummary(self) -> str:
        return str(self._preflight_result.get("summary") or "")

    @QtCore.Property("QVariantList", notify=CoreMixin.preflightChanged)
    def preflightErrors(self) -> List[str]:
        errors = self._preflight_result.get("errors") or {}
        if isinstance(errors, dict):
            return [str(value) for value in errors.values()]
        return [str(value) for value in errors]

    @QtCore.Property("QVariantList", notify=CoreMixin.preflightChanged)
    def preflightWarnings(self) -> List[str]:
        return [str(value) for value in self._preflight_result.get("warnings") or []]
