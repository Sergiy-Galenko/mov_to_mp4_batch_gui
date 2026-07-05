from __future__ import annotations

BODY = r'''    @QtCore.Property(str, notify=queueStatsChanged)
    def folderTypeFilter(self) -> str:
        return self._folder_type_filter

    @folderTypeFilter.setter
    def folderTypeFilter(self, value: str) -> None:
        self._folder_type_filter = str(value or "").strip()
        self.folder_scanner.type_filter = self._folder_type_filter if self._folder_type_filter else None

    @QtCore.Property(str, notify=queueStatsChanged)
    def folderExcludePatterns(self) -> str:
        return self._folder_exclude_patterns

    @folderExcludePatterns.setter
    def folderExcludePatterns(self, value: str) -> None:
        self._folder_exclude_patterns = str(value or "").strip()
        if self._folder_exclude_patterns:
            patterns = {p.strip() for p in self._folder_exclude_patterns.split(",") if p.strip()}
            self.folder_scanner.exclude_patterns = patterns
        else:
            from services.folder_scanner import _DEFAULT_EXCLUDES
            self.folder_scanner.exclude_patterns = set(_DEFAULT_EXCLUDES)

    @QtCore.Slot()
    def addFolderFiltered(self) -> None:
        """Add folder with current type filter and exclude patterns."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Додати папку (з фільтрами)")
        if not folder:
            return
        base = Path(folder)
        self._append_log("INFO", f"Сканую папку з фільтрами: {base}")
        threading.Thread(
            target=self._collect_folder_filtered_async,
            args=(base,),
            daemon=True,
        ).start()

    def _collect_folder_filtered_async(self, folder: Path) -> None:
        try:
            stats = self.folder_scanner.scan_with_stats(folder)
            files = stats["files"]
            excluded = stats["excluded"]
            type_filtered = stats["type_filtered"]
        except Exception as exc:
            self.event_queue.put(("log", "ERROR", f"Не вдалося просканувати папку {folder}: {exc}"))
            return
        self.event_queue.put(("add_paths", files, str(folder)))
        if excluded or type_filtered:
            self.event_queue.put(("log", "INFO", f"Скановано: {stats['total_scanned']} файлів, виключено: {excluded}, по типу: {type_filtered}"))

    # --- Clipboard paste ---

    @QtCore.Slot()
    def pasteFromClipboard(self) -> None:
        """Add files/URLs from clipboard text."""
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text() or ""
        if not text.strip():
            self._append_log("INFO", "Буфер обміну порожній.")
            return

        paths: List[Path] = []
        urls: List[str] = []
        for line in text.strip().splitlines():
            line = line.strip().strip('"').strip("'")
            if not line:
                continue
            if line.startswith(("http://", "https://")):
                urls.append(line)
            else:
                path = Path(line)
                if path.exists():
                    paths.append(path)

        if paths:
            self._add_paths(paths)
            self._append_log("OK", f"Додано з буферу: {len(paths)} файлів")
        if urls:
            self._append_log("INFO", f"URL з буферу: {len(urls)} (використай YouTube для завантаження)")
        if not paths and not urls:
            self._append_log("WARN", "Не знайдено дійсних шляхів або URL у буфері обміну.")

    # --- Queue save / load ---

    @QtCore.Slot()
    def saveQueueToFile(self) -> None:
        """Save current queue to a JSON file."""
        default_path = Path(self.outputDir).expanduser() / "queue-export.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Зберегти чергу", str(default_path), "JSON (*.json)"
        )
        if not path:
            return
        payload = {
            "version": 1,
            "type": "queue",
            "items": [self.queue_manager.serialize_task(item) for item in self.queue_model.items()],
        }
        save_json_file(Path(path), payload)
        self._append_log("OK", f"Чергу збережено: {path}")

    @QtCore.Slot()
    def loadQueueFromFile(self) -> None:
        """Load queue from a JSON file (appends to existing queue)."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Завантажити чергу", "", "JSON (*.json)"
        )
        if not path:
            return
        payload = load_json_file(Path(path))
        if not isinstance(payload, dict) or payload.get("type") != "queue":
            QtWidgets.QMessageBox.warning(None, "Черга", "Некоректний файл черги.")
            return
        items = self.queue_manager.deserialize_tasks(
            payload.get("items", []), pending_recovery=False
        )
        if items:
            self.queue_model.add_items(items)
            self._notify_queue_stats()
            self._refresh_output_preview(dict(self._last_settings_map))
'''
