from __future__ import annotations

BODY = r'''    autoTuneChanged = QtCore.Signal()
    autoProfileReady = QtCore.Signal(dict)

    @QtCore.Property(QtCore.QObject, constant=True)
    def systemProfile(self):
        return self._system_profile

    @QtCore.Property(bool, notify=autoTuneChanged)
    def autoTuneEnabled(self):
        return bool(self.settings_manager.state.get("auto_tune_enabled", True))

    @autoTuneEnabled.setter
    def autoTuneEnabled(self, value):
        self.settings_manager.state["auto_tune_enabled"] = bool(value)
        self._save_state()
        self.autoTuneChanged.emit()
        if value and self._system_profile.result:
            self._apply_system_profile(self._system_profile.result)

    @QtCore.Slot()
    def startSystemScan(self):
        if not self._is_running:
            self._system_profile.scan(self.ffmpegPath or "")

    @QtCore.Slot(dict)
    def _apply_system_profile(self, report):
        if self.autoTuneEnabled and self._is_running:
            self._pending_system_profile = report
            self.autoTuneChanged.emit()
        elif self.autoTuneEnabled:
            recommendation = dict(report.get("recommendation", {}))
            self.settings_manager.state["concurrency_limit"] = recommendation.get("concurrency_limit", 1)
            self._last_settings_map.update({key: recommendation[key] for key in ("concurrency_limit", "cpu_load_limit", "gpu_load_limit") if key in recommendation})
            self._pending_system_profile = None
            self.concurrencyLimitChanged.emit()
            self.autoProfileReady.emit(recommendation)
            self.autoTuneChanged.emit()
            self._save_state()

    @QtCore.Property(bool, notify=autoTuneChanged)
    def autoTunePending(self):
        return self.autoTuneEnabled and bool(self._pending_system_profile)

    @QtCore.Slot()
    def _apply_pending_profile(self):
        if not self._is_running and self._pending_system_profile:
            self._apply_system_profile(self._pending_system_profile)

    @QtCore.Property(QtCore.QObject, constant=True)
    def whisperSetup(self):
        return self._whisper_setup

    @QtCore.Slot(result=str)
    def pickWhisperTestMedia(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Whisper — audio / video", "", "Media (*.wav *.mp3 *.m4a *.mp4 *.mov *.mkv *.flac *.ogg);;All files (*)")
        return path
'''
