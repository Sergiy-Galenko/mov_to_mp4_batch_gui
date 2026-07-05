from __future__ import annotations

BODY = r'''        self.uiLanguageChanged.emit()
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

    @QtCore.Property(bool, notify=youtubeDownloadChanged)
    def youtubeDownloadRunning(self) -> bool:
        return self._youtube_download_running

    @QtCore.Property(float, notify=youtubeDownloadChanged)
    def youtubeDownloadProgress(self) -> float:
        return self._youtube_download_progress

    @QtCore.Property(str, notify=youtubeDownloadChanged)
    def youtubeDownloadStatus(self) -> str:
        return self._youtube_download_status

    @QtCore.Property("QVariantList", notify=youtubeHistoryChanged)
    def youtubeDownloadHistory(self) -> List[str]:
        return list(self._youtube_history)

    @QtCore.Property(str, notify=youtubeHistoryChanged)
    def youtubeCookiesPath(self) -> str:
        return self._youtube_cookies_path

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
'''
