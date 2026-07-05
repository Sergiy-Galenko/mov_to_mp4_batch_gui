from __future__ import annotations

BODY = r'''    logAdded = QtCore.Signal(str, str)
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
        self._preflight_result: Dict[str, Any] = {"ok": True, "summary": "Preflight ще не запускався.", "errors": {}, "warnings": []}
        self.queue_manager = QueueManager()
        self.settings_manager = SettingsManager()
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
        self.system_tray = SystemTrayService(parent=self, app_title=APP_TITLE)
        self._tray_enabled = self.settings_manager.tray_enabled()
        self._push_notifications_enabled = self.settings_manager.push_notifications_enabled()
        self._system_tray_signals_connected = False
        self._folder_type_filter = ""
        self._folder_exclude_patterns = ""

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
        self._output_dir_configured = self.settings_manager.output_dir_configured()
        self._output_dir = self.settings_manager.output_dir() if self._output_dir_configured else ""
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
        self._youtube_download_running = False
        self._youtube_download_progress = 0.0
        self._youtube_download_status = "Готово"
'''
