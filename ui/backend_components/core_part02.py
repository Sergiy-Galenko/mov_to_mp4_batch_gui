from __future__ import annotations

BODY = r"""        self._youtube_history = self.settings_manager.youtube_history()
        self._youtube_cookies_path = self.settings_manager.youtube_cookies_path()
        self._youtube_cancel_event: Optional[threading.Event] = None
        self._youtube_download_queue: List[Dict[str, Any]] = []
        self._youtube_current_download_id = ""
        self._youtube_playlist_preview = ""
        self._youtube_preview_info: Dict[str, Any] = {}
        self._youtube_download_log: List[str] = []
        self._ytdlp_update_running = False
        self._ffmpeg_auto_install_running = False
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
        self._last_error_title = ""
        self._last_error_details = ""
        self._last_error_log = ""

        self._info_name = "—"
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = "—"
        self._info_container = "—"
        self._info_analysis = "—"
        self._info_warnings = "—"

        self._preview_refresh_timer = QtCore.QTimer(self)
        self._preview_refresh_timer.setSingleShot(True)
        self._preview_refresh_timer.setInterval(150)
        self._preview_refresh_timer.timeout.connect(lambda: self._refresh_output_preview(dict(self._last_settings_map)))
        self._state_save_timer = QtCore.QTimer(self)
        self._state_save_timer.setSingleShot(True)
        self._state_save_timer.setInterval(300)
        self._state_save_timer.timeout.connect(self._save_state)

        self._refresh_presets()
        self.themeChanged.connect(self._apply_widget_theme)
        QtGui.QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_theme_changed)
        self._apply_widget_theme()
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

        self._scheduler_timer = QtCore.QTimer(self)
        self._scheduler_timer.setInterval(30000)
        self._scheduler_timer.timeout.connect(self._check_scheduler)
        self._scheduler_timer.start()
        self._resource_timer = QtCore.QTimer(self)
        self._resource_timer.setInterval(int(RESOURCE_SAMPLE_INTERVAL_SEC * 1000))
        self._resource_timer.timeout.connect(
            lambda: self._sample_resources() if self._scheduler_enabled or self._is_running else None
        )
        self._resource_timer.start()
        QtCore.QTimer.singleShot(2000, self._maybe_check_paid_update_on_startup)

    def _schedule_output_preview(self) -> None:
        if not self._preview_refresh_timer.isActive():
            self._preview_refresh_timer.start()

    def _schedule_state_save(self) -> None:
        if not self._state_save_timer.isActive():
            self._state_save_timer.start()

    @QtCore.Slot()
    def shutdown(self) -> None:
        self._timer.stop()
        self._watch_timer.stop()
        self._scheduler_timer.stop()
        self._resource_timer.stop()
        self._preview_refresh_timer.stop()
        self._state_save_timer.stop()
        self._save_state()
        if self._converter_service is not None:
            self._converter_service.stop()
        if self._youtube_cancel_event is not None:
            self._youtube_cancel_event.set()
        self.watch_service.stop()
        self.whisper_model_manager.shutdown()
        self._probe_executor.shutdown(wait=False, cancel_futures=True)
        self._thumbnail_executor.shutdown(wait=False, cancel_futures=True)

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

    @QtCore.Slot(str, str, result=list)
    def getWhisperModels(self, device: str = "auto", engine: str = "auto") -> list:
        from services.whisper_runtime import engine_for
        try:
            return self.whisper_model_manager.list_models(engine_for(device, engine))
        except Exception as exc:
            self.toastRequested.emit(str(exc))
            return []

    @QtCore.Slot(str, result=list)
    def getWhisperDevices(self, engine: str = "auto") -> list:
        return self.whisper_model_manager.detect_available_devices(engine)

    @QtCore.Slot(str, result=bool)
    def whisperEngineInstalled(self, engine: str) -> bool:
        from services.whisper_runtime import package_available
        return package_available("faster_whisper" if engine == "faster-whisper" else "whisper")

    @QtCore.Slot(str, str, result=str)
    def getWhisperEngine(self, device: str, engine: str) -> str:
        from services.whisper_runtime import engine_for
        try:
            return engine_for(device, engine)
        except ValueError:
            return ""

    @QtCore.Slot(str, str, str, result=bool)
    def downloadWhisperModel(self, model_name: str, device: str, engine: str) -> bool:
        from services.whisper_runtime import engine_for
        def on_progress(pct: float, msg: str) -> None:
            self.whisperDownloadProgress.emit(model_name, pct, msg)
        try:
            future = self.whisper_model_manager.download_model(model_name, on_progress, engine_for(device, engine))
            def finished(_future):
                if not self.whisper_model_manager.closed:
                    self.whisperModelsChanged.emit()
            future.add_done_callback(finished)
            self.whisperModelsChanged.emit()
            return True
        except Exception as exc:
            self.toastRequested.emit(str(exc))
            return False

    @QtCore.Slot()
    def cancelWhisperDownload(self) -> None:
        self.whisper_model_manager.cancel_download()

    @QtCore.Slot(str, str, str, result=bool)
    def deleteWhisperModel(self, model_name: str, device: str, engine: str) -> bool:
        from services.whisper_runtime import engine_for
        if self.isRunning:
            self.toastRequested.emit(self._tr("whisper.busy"))
            return False
        try:
            result = self.whisper_model_manager.delete_model(model_name, engine_for(device, engine))
            self.whisperModelsChanged.emit()
            return result
        except Exception as exc:
            self.toastRequested.emit(str(exc))
            return False
"""
