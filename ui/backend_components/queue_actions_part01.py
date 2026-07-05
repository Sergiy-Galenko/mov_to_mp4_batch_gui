from __future__ import annotations

BODY = r'''    @QtCore.Slot()
    def deduplicateQueue(self) -> None:
        unique, removed = self.queue_manager.deduplicate_by_path(self.queue_model.items())
        self.queue_model.set_items(unique)
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено дублікатів: {removed}")

    @QtCore.Slot()
    def deduplicateQueueByHash(self) -> None:
        items = self.queue_model.items()
        if not items:
            return
        self._append_log("INFO", "Hash-дедуплікація запущена у фоні.")
        threading.Thread(target=self._deduplicate_hash_async, args=(items,), daemon=True).start()

    def _deduplicate_hash_async(self, items: List[TaskItem]) -> None:
        unique, removed, log_lines = self.queue_manager.deduplicate_by_hash(items)
        self.event_queue.put(("dedupe_hash_done", unique, removed, log_lines))

    def _move_selected(self, indices: List[int], direction: str) -> None:
        items = self.queue_manager.reorder(self.queue_model.items(), indices, direction)
        self.queue_model.set_items(items)
        self._selected_index = self.queue_model.index_for_path(Path(self._selected_path)) if self._selected_path else -1
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    def _move_selected_paths(self, paths: List[Any], direction: str) -> None:
        selected_paths = self.queue_manager.paths_from_payload(paths)
        indices = self.queue_manager.selected_indices_for_paths(self.queue_model.items(), selected_paths)
        self._move_selected(indices, direction)

    @QtCore.Slot("QVariantList")
    def moveSelectedUp(self, indices: List[int]) -> None:
        self._move_selected(indices, "up")

    @QtCore.Slot("QVariantList")
    def moveSelectedDown(self, indices: List[int]) -> None:
        self._move_selected(indices, "down")

    @QtCore.Slot("QVariantList")
    def moveSelectedTop(self, indices: List[int]) -> None:
        self._move_selected(indices, "top")

    @QtCore.Slot("QVariantList")
    def moveSelectedBottom(self, indices: List[int]) -> None:
        self._move_selected(indices, "bottom")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsUp(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "up")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsDown(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "down")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsTop(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "top")

    @QtCore.Slot("QVariantList")
    def moveSelectedPathsBottom(self, paths: List[Any]) -> None:
        self._move_selected_paths(paths, "bottom")

    @QtCore.Slot(str, int)
    def movePathToIndex(self, path_text: str, target_index: int) -> None:
        items = self.queue_manager.move_path_to_index(
            self.queue_model.items(),
            Path(str(path_text or "").strip()).expanduser(),
            target_index,
        )
        self.queue_model.set_items(items)
        self._notify_queue_stats()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()

    @QtCore.Slot("QVariantList")
    def removeSelected(self, indices: List[int]) -> None:
        items, removed = self.queue_manager.remove_indices(self.queue_model.items(), indices)
        self.queue_model.set_items(items)
        self._after_queue_removed(removed)

    @QtCore.Slot("QVariantList")
    def removeSelectedPaths(self, paths: List[Any]) -> None:
        selected = self.queue_manager.paths_from_payload(paths)
        items, removed = self.queue_manager.remove_paths(self.queue_model.items(), selected)
        self.queue_model.set_items(items)
        self._after_queue_removed(removed)

    @QtCore.Slot(str)
    def removeTaskPath(self, path_text: str) -> None:
        self.removeSelectedPaths([path_text])

    def _after_queue_removed(self, removed: int) -> None:
        if removed <= 0:
            return
        self._selected_index = -1
        self._selected_path = ""
        self._notify_queue_stats()
        self._refresh_output_preview(dict(self._last_settings_map))
        self._save_state()
        self._append_log("INFO", f"Видалено: {removed}")

    @QtCore.Slot()
    def clearQueue(self) -> None:
        self.queue_model.set_items([])
        self._selected_index = -1
        self._selected_path = ""
        self._clear_info()
        self._set_output_preview("Черга порожня.")
        self._set_selected_preview("—", "—")
        self._notify_queue_stats()
        self._refresh_codec_distribution()
        self._save_state()
        self._append_log("INFO", "Чергу очищено")

'''
