from __future__ import annotations

BODY = r'''        self._refresh_size_predictions(settings_map)
        self._refresh_smart_recommendations(settings_map)
        self._set_output_preview(summary.text)
        self._set_selected_preview(summary.selected_source, summary.selected_output, summary.selected_command)

    def _refresh_size_predictions(self, settings_map: Dict[str, Any]) -> None:
        for task in self.queue_model.items():
            merged_map = merge_settings_maps(settings_map, task.overrides)
            settings = settings_map_to_model(merged_map, defaults=ConversionSettings())
            info = self.media_info_cache.get(task.path) or task.probe_data
            input_bytes = int((info.size_bytes if info else None) or task.input_bytes or 0)
            if not input_bytes:
                try:
                    input_bytes = task.path.stat().st_size
                except Exception:
                    input_bytes = 0
            if settings.target_size_mb:
                predicted = int(float(settings.target_size_mb) * 1024 * 1024)
            else:
                predicted = int(input_bytes * prediction_factor(settings.performance_profile)) if input_bytes else 0
            self.queue_model.set_prediction(task.path, predicted)

    @QtCore.Slot("QVariantMap")
    def refreshOutputPreview(self, settings_map: Dict[str, Any]) -> None:
        self._last_settings_map = dict(settings_map)
        self._refresh_output_preview(dict(settings_map))
        self._save_state()

    @QtCore.Slot()
    def restoreSession(self) -> None:
        if self.queue_model.rowCount() > 0:
            self._append_log("INFO", f"Відновлено чергу: {self.queue_model.rowCount()} елементів.")
        if self.settings_manager.state.get("pending_recovery"):
            self._append_log("WARN", "Попередній запуск завершився аварійно; активні задачі повернено у чергу.")
        if self._last_settings_map:
            self.presetLoaded.emit(dict(self._last_settings_map))
            self._refresh_output_preview(dict(self._last_settings_map))

    @QtCore.Slot("QVariantMap")
    def exportProject(self, settings_map: Dict[str, Any]) -> None:
        default_path = Path(self.outputDir).expanduser() / "media-converter-project.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експортувати проєкт", str(default_path), "JSON (*.json)")
        if not path:
            return
        payload = {
            "version": 2,
            "exported_at": time.time(),
            "output_dir": self.outputDir,
            "ffmpeg_path": self.ffmpegPath,
            "settings": dict(settings_map),
            "queue_items": [self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
        }
        save_json_file(Path(path), payload)
        self._append_log("OK", f"Проєкт збережено: {path}")

    @QtCore.Slot()
    def importProject(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Імпортувати проєкт", "", "JSON (*.json)")
        if not path:
            return
        payload = load_json_file(Path(path))
        if not isinstance(payload, dict):
            QtWidgets.QMessageBox.warning(None, "Проєкт", "Некоректний JSON проєкту.")
            return
        queue_items = self.queue_manager.deserialize_tasks(payload.get("queue_items", []), pending_recovery=False)
        self.queue_model.set_items(queue_items)
        self._notify_queue_stats()
        self._last_settings_map = dict(payload.get("settings") or {})
        self.outputDir = str(payload.get("output_dir") or self.outputDir)
        imported_ffmpeg = str(payload.get("ffmpeg_path") or "").strip()
        if imported_ffmpeg:
            self.ffmpegPath = imported_ffmpeg
        self._save_state()
        if self._last_settings_map:
            self.presetLoaded.emit(dict(self._last_settings_map))
            self._refresh_output_preview(dict(self._last_settings_map))
        self._append_log("OK", f"Проєкт імпортовано: {path}")

    @QtCore.Slot("QVariantMap")
    def exportCommandScript(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        command = self._selected_preview_command
        if not command or command == "—":
            QtWidgets.QMessageBox.information(None, "FFmpeg command", "Немає команди для експорту.")
            return
        suffix = ".bat" if os.name == "nt" else ".sh"
        default_path = Path(self.outputDir).expanduser() / f"ffmpeg-command{suffix}"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експорт команди", str(default_path), f"Script (*{suffix});;All Files (*)")
        if not path:
            return
        content = f"@echo off\r\n{command}\r\n" if os.name == "nt" else f"#!/usr/bin/env sh\n{command}\n"
        Path(path).write_text(content, encoding="utf-8")
        self._append_log("OK", f"Команду експортовано: {path}")

    @QtCore.Slot("QVariantMap")
    def copyDryRunCommand(self, settings_map: Dict[str, Any]) -> None:
        self._refresh_output_preview(dict(settings_map))
        if self._selected_preview_command and self._selected_preview_command != "—":
            QtWidgets.QApplication.clipboard().setText(self._selected_preview_command)
            self._append_log("OK", "Dry-run команду скопійовано.")

    @QtCore.Slot()
    def clearHistory(self) -> None:
        self.history_store.clear()
        self.history_model.set_entries(self.history_store.entries)
        self.historyChanged.emit()
        self._append_log("INFO", "Історію запусків очищено.")

    @QtCore.Slot(str)
    def exportHistoryReport(self, fmt: str) -> None:
        clean_fmt = str(fmt or "csv").strip().lower()
        if clean_fmt not in {"csv", "json", "html"}:
            clean_fmt = "csv"
        if not self.history_store.entries:
            QtWidgets.QMessageBox.information(None, "Report", "Історія запусків порожня.")
            return
        latest = self.history_store.entries[0]
        default_path = Path(self.outputDir or str(Path.home())).expanduser() / f"conversion-report.{clean_fmt}"
        filter_map = {
            "csv": "CSV (*.csv)",
            "json": "JSON (*.json)",
            "html": "HTML (*.html)",
        }
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Експорт звіту", str(default_path), filter_map[clean_fmt])
        if not path:
            return
        ReportService.export_file(
            Path(path),
            list(latest.get("results") or []),
            fmt=clean_fmt,
            settings=dict(latest.get("settings") or {}),
            output_dir=str(latest.get("output_dir") or ""),
            started_at=latest.get("started_at"),
        )
        self._append_log("OK", f"Звіт експортовано: {path}")

    @QtCore.Slot(int)
    def openHistoryOutput(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        folder = Path(str(entry.get("output_dir") or "")).expanduser()
        if folder.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    @QtCore.Slot(int)
    def loadHistorySettings(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
'''
