from __future__ import annotations

import queue

from .common import (
    APP_TITLE,
    DEFAULT_FOLDER_RULES,
    EVENT_POLL_INTERVAL_MS,
    RESOURCE_SAMPLE_INTERVAL_SEC,
    WATCH_SCAN_INTERVAL_MS,
    Any,
    ArchiveBackend,
    BatchWorkflowService,
    Dict,
    DisplayService,
    FfmpegAutoInstaller,
    FfmpegService,
    FolderScanner,
    HistoryModel,
    HistoryStore,
    LicenseService,
    List,
    LogModel,
    MediaInfo,
    MediaPreviewService,
    MontageEditing,
    MontageService,
    NotificationService,
    Optional,
    PaidUpdateService,
    Path,
    PresetManager,
    QtCore,
    QtGui,
    QueueFilterModel,
    QueueManager,
    QueueModel,
    ResourceMonitor,
    SettingsManager,
    ShortcutManager,
    SourceUpdateService,
    SystemProfile,
    SystemTrayService,
    TaskbarService,
    TelegramNoteService,
    ThemeManager,
    ThreadPoolExecutor,
    UiEventQueue,
    WatchService,
    WhisperModelManager,
    WhisperSetup,
    find_ffmpeg,
    find_ffprobe,
    threading,
)


class CoreMixin:
    logAdded = QtCore.Signal(str, str)
    statusChanged = QtCore.Signal()
    fileProgressChanged = QtCore.Signal()
    totalProgressChanged = QtCore.Signal()
    fileProgressTextChanged = QtCore.Signal()
    totalProgressTextChanged = QtCore.Signal()
    encoderInfoChanged = QtCore.Signal()
    ffmpegPathChanged = QtCore.Signal()
    outputDirChanged = QtCore.Signal()
    outputDirConfiguredChanged = QtCore.Signal()
    infoChanged = QtCore.Signal()
    isRunningChanged = QtCore.Signal()
    isPausedChanged = QtCore.Signal()
    presetsChanged = QtCore.Signal()
    presetLoaded = QtCore.Signal(dict)
    recentFoldersChanged = QtCore.Signal()
    watchFolderChanged = QtCore.Signal()
    watchRunningChanged = QtCore.Signal()
    outputPreviewChanged = QtCore.Signal()
    historyChanged = QtCore.Signal()
    queueStatsChanged = QtCore.Signal()
    queueFilterChanged = QtCore.Signal()
    selectedDetailsChanged = QtCore.Signal()
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
    youtubeDownloadChanged = QtCore.Signal()
    youtubeHistoryChanged = QtCore.Signal()
    toastRequested = QtCore.Signal(str)
    themeChanged = QtCore.Signal()
    shortcutsChanged = QtCore.Signal()
    previewGenerated = QtCore.Signal(str, dict)  # path, preview_data
    trayVisibilityChanged = QtCore.Signal()
    errorStateChanged = QtCore.Signal()
    pushNotificationsChanged = QtCore.Signal()
    preflightChanged = QtCore.Signal()
    batchWorkflowChanged = QtCore.Signal()
    schedulerChanged = QtCore.Signal()
    completionActionChanged = QtCore.Signal()
    notificationChannelsChanged = QtCore.Signal()
    licenseChanged = QtCore.Signal()
    paidUpdateChanged = QtCore.Signal()
    sourceUpdateChanged = QtCore.Signal()
    queueViewModeChanged = QtCore.Signal()
    concurrencyLimitChanged = QtCore.Signal()
    outputTemplateChanged = QtCore.Signal()
    displayMetricsChanged = QtCore.Signal()
    autoDisplayAdaptationChanged = QtCore.Signal()
    whisperModelsChanged = QtCore.Signal()
    whisperDownloadProgress = QtCore.Signal(str, float, str)
    montageWaveformReady = QtCore.Signal(str, str)
    montageSessionUpdated = QtCore.Signal(str)
    montageProxyReady = QtCore.Signal(str, str)
    montageTimelineRendered = QtCore.Signal(str, bool)

    def __init__(self) -> None:
        super().__init__()
        self.whisper_model_manager = WhisperModelManager()
        self.event_queue: queue.Queue[tuple] = UiEventQueue()
        self.ffmpeg_service = FfmpegService(find_ffmpeg(), None)
        self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        self.montage_service = MontageService(self.ffmpeg_service.ffmpeg_path, self.ffmpeg_service.ffprobe_path)
        self._montage_editing = MontageEditing(self)
        from services.editor_project import EditorProject
        from services.editor_render_service import EditorRenderService

        self._editor_project = EditorProject(self)
        self._editor_render = EditorRenderService(self)
        self._telegram_note_service = TelegramNoteService(self)
        self._archive_backend = ArchiveBackend(self)
        self._converter_service = None
        self._runner = None
        self._media_analysis = None
        self._preview_builder = None
        self._validation = None
        self._preflight_result: Dict[str, Any] = {"ok": True, "summary": "Preflight ще не запускався.", "errors": {}, "warnings": []}
        self._resource_monitor = ResourceMonitor()
        self.queue_manager = QueueManager()
        self.settings_manager = SettingsManager()
        self._pending_system_profile = None
        self.isRunningChanged.connect(self._apply_pending_profile)
        from services.background_job import BackgroundJob
        self._diagnostic_job = BackgroundJob(self)
        self._diagnostic_job.completed.connect(lambda result: self._append_log(
            "OK", self._tr("system.cache_cleared", count=result["cache_removed"]) if "cache_removed" in result
            else self._tr("system.report_saved")
        ))
        self._system_profile = SystemProfile(self)
        self._system_profile.completed.connect(self._apply_system_profile)
        self._whisper_setup = WhisperSetup(self)
        self._whisper_setup.completed.connect(lambda _: self.whisperModelsChanged.emit())
        self.ffmpeg_auto_installer = FfmpegAutoInstaller()
        self.preset_manager = PresetManager()
        self.history_store = HistoryStore()
        self.watch_service = WatchService(
            on_new_files=self._on_watch_files,
            poll_interval_sec=max(WATCH_SCAN_INTERVAL_MS / 1000.0, 0.5),
        )
        self.theme_manager = ThemeManager()
        self.shortcut_manager = ShortcutManager()
        self.media_preview = MediaPreviewService(
            ffmpeg_path=self.ffmpeg_service.ffmpeg_path or "",
            ffprobe_path=self.ffmpeg_service.ffprobe_path or "",
        )
        self.folder_scanner = FolderScanner()
        self.batch_workflow = BatchWorkflowService()
        self.notification_service = NotificationService()
        self.license_service = LicenseService()
        self.paid_update_service = PaidUpdateService()
        self.source_update_service = SourceUpdateService()
        self.system_tray = SystemTrayService(parent=self, app_title=APP_TITLE)
        self.taskbar = TaskbarService()
        self.display_service = DisplayService(parent=self)
        self.display_service.metricsChanged.connect(self._on_display_metrics_changed)
        self._license_payload = self.settings_manager.license_payload()
        self._trial_started_at = self.settings_manager.trial_started_at()
        self._trial_signature = self.settings_manager.trial_signature()
        self._license_info = self.license_service.info_from_state(
            {
                "license_payload": self._license_payload,
                "trial_started_at": self._trial_started_at,
                "trial_signature": self._trial_signature,
            }
        )
        self._paid_auto_update_enabled = self.settings_manager.paid_auto_update_enabled()
        self._paid_update_manifest_url = self.settings_manager.paid_update_manifest_url()
        self._paid_update_status = "Paid update check has not run."
        self._paid_update_download_url = ""
        self._paid_update_available = False
        self._source_update_checking = False
        self._source_update_available = False
        self._source_update_restart_required = False
        self._source_update_status = "Оновлення ще не перевірялися."
        self._source_update_local_commit = ""
        self._source_update_remote_commit = ""
        self._tray_enabled = self.settings_manager.tray_enabled()
        self._push_notifications_enabled = self.settings_manager.push_notifications_enabled()
        self._watch_auto_convert_enabled = self.settings_manager.watch_auto_convert_enabled()
        self._watch_rules_text = self.settings_manager.watch_rules_text() or DEFAULT_FOLDER_RULES
        self._scheduler_enabled = self.settings_manager.scheduler_enabled()
        self._scheduler_mode = self.settings_manager.scheduler_mode()
        self._scheduler_time = self.settings_manager.scheduler_time()
        self._scheduler_cpu_limit = self.settings_manager.scheduler_cpu_limit()
        self._scheduler_gpu_limit = self.settings_manager.scheduler_gpu_limit()
        self._scheduler_last_start_key = ""
        self._completion_action = self.settings_manager.completion_action()
        self._webhook_enabled = self.settings_manager.webhook_enabled()
        self._webhook_url = self.settings_manager.webhook_url()
        self._discord_webhook_url = self.settings_manager.discord_webhook_url()
        self._telegram_bot_token = self.settings_manager.telegram_bot_token()
        self._telegram_chat_id = self.settings_manager.telegram_chat_id()
        self._system_tray_signals_connected = False
        self._folder_type_filter = ""
        self._folder_exclude_patterns = ""

        self.queue_model = QueueModel()
        self.queue_filter_model = QueueFilterModel(self)
        self.queue_filter_model.setSourceModel(self.queue_model)
        for signal in (
            self.queue_filter_model.rowsInserted,
            self.queue_filter_model.rowsRemoved,
            self.queue_filter_model.modelReset,
            self.queue_filter_model.layoutChanged,
        ):
            signal.connect(lambda *_args: self.queueFilterChanged.emit())
        self.log_model = LogModel()
        self.history_model = HistoryModel()
        self.presets_model = QtCore.QStringListModel()
        self.recent_folders_model = QtCore.QStringListModel()

        state = self.settings_manager.state
        self._recent_folders = self.settings_manager.recent_folders()
        self._watch_folder = self.settings_manager.watch_folder()
        self._ui_language = self.settings_manager.ui_language()
        self._watch_running = False
        self._watch_pending_paths: set[Path] = set()
        self._watch_seen: set[Path] = set()
        self._ffmpeg_path = self.settings_manager.ffmpeg_path(self.ffmpeg_service.ffmpeg_path)
        self._output_dir_configured = self.settings_manager.output_dir_configured()
        self._output_dir = self.settings_manager.output_dir() if self._output_dir_configured else ""
        self._last_settings_map = self.settings_manager.last_settings()
        self._show_onboarding = False

        restored_items = self.queue_manager.deserialize_tasks(
            state.get("queue_items", []),
            pending_recovery=bool(state.get("pending_recovery")),
        )
        from services.task_journal import TaskJournal
        restored_items = TaskJournal().recover_items(restored_items)
        self.queue_model.set_items(restored_items)

        self.media_info_cache: Dict[Path, MediaInfo] = {}
        self._probe_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ffprobe-prefetch")
        self._probe_pending: set[Path] = set()
        self._thumbnail_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="thumbnail")
        self._thumbnail_pending: set[Path] = set()
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
        self._youtube_download_running = False
        self._youtube_download_progress = 0.0
        self._youtube_download_status = "Готово"
        self._youtube_history = self.settings_manager.youtube_history()
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
        self._resource_timer.timeout.connect(lambda: self._sample_resources() if self._scheduler_enabled or self._is_running else None)
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
        self._archive_backend.shutdown()
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
        self._montage_editing.shutdown()
        self._editor_project.shutdown()
        self._editor_render.shutdown()
        self._diagnostic_job.shutdown()
        self.montage_service.proxy_service.close()
        self._system_profile.shutdown()
        self._whisper_setup.shutdown()
        self._probe_executor.shutdown(wait=False, cancel_futures=True)
        self._thumbnail_executor.shutdown(wait=False, cancel_futures=True)

    @property
    def converter(self):
        if self._converter_service is None:
            from services.converter_service import ConverterService

            self._converter_service = ConverterService(self.ffmpeg_service, self.event_queue)
            self._converter_service.resource_monitor = self._resource_monitor
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
        from services.whisper_runtime import engine_for

        try:
            selected = engine_for(engine=engine)
        except ValueError:
            return ["auto", "cpu"]
        report = self._whisper_setup.diagnostics.get("engines", {}).get(selected, {})
        return ["auto", *dict.fromkeys(["cpu", *report.get("devices", [])])]

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
