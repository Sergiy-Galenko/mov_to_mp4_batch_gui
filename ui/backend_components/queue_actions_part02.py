from __future__ import annotations

BODY = r'''    @QtCore.Slot()
    def exportLog(self) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-log.txt"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати лог", str(default_path), "Text (*.txt)")
        if path:
            Path(path).write_text("\n".join(self._log_lines), encoding="utf-8")
            self._append_log("OK", f"Лог збережено: {path}")

    @QtCore.Slot()
    def pickWatchFolder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Watch folder", self.watchFolder or "")
        if folder:
            self.watchFolder = folder

    @QtCore.Slot()
    def startWatching(self) -> None:
        folder = Path(self.watchFolder).expanduser()
        if not self.watchFolder or not folder.exists():
            QtWidgets.QMessageBox.warning(None, "Watch folder", "Обери існуючу папку для моніторингу.")
            return
        try:
            self.watch_service.start(folder)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(None, "Watch folder", str(exc))
            return
        self._watch_seen = set()
        self._watch_running = True
        self.watchRunningChanged.emit()
        self._append_log("OK", f"Watch folder активовано: {folder}")

    @QtCore.Slot()
    def stopWatching(self) -> None:
        self.watch_service.stop()
        self._watch_running = False
        self.watchRunningChanged.emit()
        self._watch_timer.stop()
        self._append_log("INFO", "Watch folder зупинено")

    def _on_watch_files(self, paths: List[Path]) -> None:
        folder = self.watch_service.folder
        self.event_queue.put(("add_paths", list(paths), str(folder) if folder else ""))
        self.event_queue.put(("log", "INFO", f"Watch folder додав файлів: {len(paths)}"))

    def _scan_watch_folder(self) -> None:
        if not self._watch_running or not self.watchFolder:
            return
        base = Path(self.watchFolder).expanduser()
        if not base.exists():
            self.stopWatching()
            return
        new_paths = self.watch_service.scan_once()
        if new_paths:
            self._add_paths(new_paths)
            self._append_log("INFO", f"Watch folder додав файлів: {len(new_paths)}")

    @QtCore.Slot(int)
    def selectQueueIndex(self, index: int) -> None:
        self._selected_index = index
        task = self.queue_model.item_at(index)
        if task is None:
            self._selected_path = ""
            self._clear_info()
            self._set_selected_preview("—", "—")
            self.taskOverrideLoaded.emit({})
            return
        self._selected_path = str(task.path)
        self._info_name = task.path.name
        self._info_duration = "--:--"
        self._info_codec = "—"
        self._info_res = "—"
        self._info_size = task.size_text or "—"
        self._info_container = "—"
        self._info_analysis = f"Тип: {task.media_type}"
        self._info_warnings = task.last_error or "—"
        self.infoChanged.emit()
        self.taskOverrideLoaded.emit(dict(task.overrides))
        self._refresh_output_preview(dict(self._last_settings_map))
        info = self.media_info_cache.get(task.path)
        if info:
            self._update_info(info)
            return
        if self.ffmpeg_service.ffprobe_path and task.media_type in {"video", "audio"}:
            self.queue_model.update_task_state(task.path, TaskStatus.ANALYZING)
            self._notify_queue_stats()
            threading.Thread(target=self._probe_media_async, args=(task.path,), daemon=True).start()
        self._ensure_thumbnail_async(task.path, task.media_type)

    @QtCore.Slot(str)
    def selectQueuePath(self, path_text: str) -> None:
        self.selectQueueIndex(self.queue_model.index_for_path(Path(str(path_text or "").strip()).expanduser()))

    @QtCore.Slot(int, result=str)
    def queuePathAt(self, index: int) -> str:
        task = self.queue_model.item_at(index)
        return str(task.path) if task else ""
'''
