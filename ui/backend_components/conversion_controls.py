from __future__ import annotations

from .common import (
    Any,
    ConversionSettings,
    Dict,
    List,
    Optional,
    Path,
    QtCore,
    QtWidgets,
    TaskItem,
    TaskStatus,
    find_ffprobe,
    merge_settings_maps,
    settings_map_to_model,
    time,
)


class ConversionControlsMixin:
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
                    task_id=item.task_id,
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
        if failed_only:
            only_paths = {item.path for item in self.queue_model.items() if item.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}}
            if not only_paths:
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

    @QtCore.Slot("QVariantList", "QVariantMap")
    def startConversionForPaths(self, paths: List[Any], settings_map: Dict[str, Any]) -> None:
        """Start only the selected queue items without altering queue state."""
        selected_paths = {Path(str(path or "").strip()).expanduser() for path in paths if str(path or "").strip()}
        selected_paths = {path for path in selected_paths if self.queue_model.item_by_path(path) is not None}
        if selected_paths:
            self._start_conversion(dict(settings_map), only_paths=selected_paths)

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
            self.converter.skip_current(Path(self._active_task_path) if self._active_task_path else None)
            self._set_status("Пропускаю поточний файл...")

    @QtCore.Slot(str)
    def skipTaskPath(self, path_text: str) -> None:
        if self._is_running and path_text:
            self.converter.skip_current(Path(path_text).expanduser())

    @QtCore.Slot(str)
    def loadPreset(self, name: str) -> None:
        data = self.preset_manager.get(name)
        if data:
            self.presetLoaded.emit(data)
            self._append_log("OK", f"Пресет завантажено: {name}")

    @QtCore.Slot(str, "QVariantMap")
    def savePreset(self, name: str, settings_map: Dict[str, Any]) -> None:
        name = name.strip()
        if not name:
            QtWidgets.QMessageBox.warning(None, "Пресети", "Введи назву пресету.")
            return
        if self.preset_manager.get(name):
            answer = QtWidgets.QMessageBox.question(None, "Пресети", "Пресет уже існує. Перезаписати?")
            if answer != QtWidgets.QMessageBox.Yes:
                return
        try:
            self.preset_manager.save(name, dict(settings_map))
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(None, "Пресети", str(exc))
            return
        self._refresh_presets()
        self._append_log("OK", f"Пресет збережено: {name}")

    @QtCore.Slot()
    def importPresets(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Імпорт пресетів", "", "JSON (*.json)")
        if not path:
            return
        try:
            imported = self.preset_manager.read_import(Path(path))
            conflicts = sorted(set(imported) & set(self.preset_manager.names()))
            policy = "error"
            if conflicts:
                prompt = self._tr("presets_conflicts", names=", ".join(conflicts))
                answer = QtWidgets.QMessageBox.question(
                    None,
                    self._tr("presets"),
                    prompt,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                )
                if answer == QtWidgets.QMessageBox.Cancel:
                    return
                policy = "replace" if answer == QtWidgets.QMessageBox.Yes else "keep"
            self.preset_manager.import_json(Path(path), conflict_policy=policy)
            self._refresh_presets()
            self._append_log("OK", "Пресети імпортовано.")
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(None, "Пресети", str(exc))

    @QtCore.Slot()
    def exportPresets(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експорт користувацьких пресетів", "presets.json", "JSON (*.json)")
        if not path:
            return
        try:
            self.preset_manager.export_json(Path(path))
            self._append_log("OK", "Пресети експортовано.")
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(None, "Пресети", str(exc))

    @QtCore.Slot(str)
    def deletePreset(self, name: str) -> None:
        if not name:
            return
        answer = QtWidgets.QMessageBox.question(None, "Пресети", f"Видалити пресет '{name}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        try:
            if self.preset_manager.delete(name):
                self._refresh_presets()
                self._append_log("OK", f"Пресет видалено: {name}")
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(None, self._tr("presets"), str(exc))

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
            if key in {"trim_start", "trim_end"} or value not in (None, ""):
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
