from __future__ import annotations

BODY = r'''    def _build_run_tasks(
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
                    smart_recommendation=item.smart_recommendation,
                    pinned=item.pinned,
                    priority=item.priority,
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
        if not self._ensure_output_dir_selected(prompt=True):
            return
        if self.ffmpegPath:
            self.ffmpeg_service.ffmpeg_path = self.ffmpegPath
            self.ffmpeg_service.ffprobe_path = find_ffprobe(self.ffmpeg_service.ffmpeg_path)
        preflight = self._run_preflight(settings_map, only_paths=only_paths)
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
'''
