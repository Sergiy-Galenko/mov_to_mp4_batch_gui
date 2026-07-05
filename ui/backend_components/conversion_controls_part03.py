from __future__ import annotations

BODY = r'''        selected_paths = self.queue_manager.paths_from_payload(paths)
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
'''
