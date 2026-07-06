from __future__ import annotations

BODY = r'''    @QtCore.Property(str, constant=True)
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

    @QtCore.Property(bool, notify=outputDirConfiguredChanged)
    def outputDirConfigured(self) -> bool:
        return self._output_dir_configured

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
'''
