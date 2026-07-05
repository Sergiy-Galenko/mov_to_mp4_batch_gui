from __future__ import annotations

BODY = r'''            self._append_log("WARN", "Немає попередніх налаштувань для retry.")
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
            self.runner.skip_current()
            self._set_status("Пропускаю поточний файл...")

    @QtCore.Slot(str)
    def loadPreset(self, name: str) -> None:
        data = self.preset_manager.get(name)
        if data:
            self.presetLoaded.emit(data)
            self._append_log("OK", f"Пресет завантажено: {name}")

    @QtCore.Slot(str, "QVariantMap")
    def savePreset(self, name: str, settings_map: Dict[str, Any]) -> None:
        if not name:
            QtWidgets.QMessageBox.warning(None, "Пресети", "Введи назву пресету.")
            return
        if self.preset_manager.get(name):
            answer = QtWidgets.QMessageBox.question(None, "Пресети", "Пресет уже існує. Перезаписати?")
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self.preset_manager.save(name, dict(settings_map))
        self._refresh_presets()
        self._append_log("OK", f"Пресет збережено: {name}")

    @QtCore.Slot(str)
    def deletePreset(self, name: str) -> None:
        if not name:
            return
        answer = QtWidgets.QMessageBox.question(None, "Пресети", f"Видалити пресет '{name}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        if self.preset_manager.delete(name):
            self._refresh_presets()
            self._append_log("OK", f"Пресет видалено: {name}")

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
            if value not in (None, ""):
                merged[str(key)] = value
        task.overrides = merged
        self.queue_model.update_item(index, task)
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("OK", f"Override оновлено для: {task.path.name}")
        self.taskOverrideLoaded.emit(dict(task.overrides))

    @QtCore.Slot("QVariantList", "QVariantMap")
    def saveBulkOverride(self, paths: List[Any], override_map: Dict[str, Any]) -> None:
'''
