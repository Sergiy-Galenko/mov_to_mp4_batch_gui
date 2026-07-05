from __future__ import annotations

BODY = r'''        self._youtube_history = self.settings_manager.youtube_history()
        self._youtube_cookies_path = self.settings_manager.youtube_cookies_path()
        self._youtube_cancel_event: Optional[threading.Event] = None
        self._youtube_download_queue: List[Dict[str, Any]] = []
        self._youtube_current_download_id = ""
        self._youtube_playlist_preview = ""
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
'''
