from __future__ import annotations

BODY = r'''        return self.shortcut_manager.all_shortcuts()

    @QtCore.Property("QVariantMap", notify=shortcutsChanged)
    def shortcutsByCategory(self) -> Dict[str, List[Dict[str, str]]]:
        return self.shortcut_manager.shortcuts_by_category()

    @QtCore.Slot(str, result=str)
    def shortcutKey(self, action_id: str) -> str:
        return self.shortcut_manager.get_key(action_id)

    @QtCore.Slot(str, result="QVariantList")
    def globalSearch(self, query: str) -> List[Dict[str, Any]]:
        needle = str(query or "").strip().lower()
        if len(needle) < 2:
            return []
        results: List[Dict[str, Any]] = []

        def add(kind: str, title: str, detail: str, page: int, target: str = "", action: str = "") -> None:
            if len(results) >= 24:
                return
            results.append(
                {
                    "kind": kind,
                    "title": title,
                    "detail": detail,
                    "page": page,
                    "target": target,
                    "action": action,
                }
            )

        for item in self.queue_model.items():
            haystack = " ".join([item.path.name, str(item.path), item.media_type, item.status, item.last_error]).lower()
            if needle in haystack:
                add("Файл", item.path.name, f"{item.media_type} | {item.status} | {item.path}", 0)

        for name in self.preset_manager.names():
            if needle in str(name).lower():
                add("Пресет", str(name), "Відкрити пресети", 2)

        for url in self._youtube_history:
            if needle in str(url).lower():
                add("YouTube", str(url), "Відкрити Downloads", 4)

        for entry in self.history_store.entries[:30]:
            started = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("started_at", 0) or 0))
            detail = f"{started} | files {entry.get('total_files', 0)} | {entry.get('output_dir', '')}"
            if needle in detail.lower() or needle in str(entry.get("operation", "")).lower():
                add("Історія", str(entry.get("operation", "Run")), detail, 1)

        for line in self._log_lines[-120:]:
            if needle in line.lower():
                add("Лог", line[:80], "Відкрити чергу і лог", 0)

        quick_targets = [
            ("Конвертація", "Черга файлів", 0, ""),
            ("Монтаж", "Відео-редактор", 5, "video_editor"),
            ("Downloads", "YouTube завантаження", 4, ""),
            ("Аналітика", "Графіки та історія", 1, ""),
            ("FFmpeg", "Шлях, кодеки, watch folder", 3, ""),
            ("Налаштування", "Параметри конвертації", 5, "run"),
        ]
        for title, detail, page, target in quick_targets:
            if needle in title.lower() or needle in detail.lower():
                add("Розділ", title, detail, page, target)

        return results

    @QtCore.Slot(str, str)
    def setShortcutKey(self, action_id: str, key: str) -> None:
        conflict = self.shortcut_manager.find_conflict(key, exclude_action=action_id)
        if conflict:
            self._append_log("WARN", f"Shortcut conflict: {key} already used by {self.shortcut_manager.get_label(conflict)}")
            return
        self.shortcut_manager.set_key(action_id, key)
        self.shortcutsChanged.emit()
        self._append_log("OK", f"Shortcut set: {action_id} → {key}")

    @QtCore.Slot(str)
    def resetShortcut(self, action_id: str) -> None:
        self.shortcut_manager.reset_key(action_id)
        self.shortcutsChanged.emit()

    @QtCore.Slot()
    def resetAllShortcuts(self) -> None:
        self.shortcut_manager.reset_all()
        self.shortcutsChanged.emit()
        self._append_log("OK", "All shortcuts reset to defaults.")

    # --- System tray properties ---

    @QtCore.Property(bool, notify=trayVisibilityChanged)
    def trayEnabled(self) -> bool:
        return self._tray_enabled

    @trayEnabled.setter
    def trayEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if self._tray_enabled == next_value:
            return
        self._tray_enabled = next_value
        self.system_tray.set_visible(self._tray_enabled)
        self.trayVisibilityChanged.emit()
        self._save_state()

    @QtCore.Property(bool, notify=pushNotificationsChanged)
    def pushNotificationsEnabled(self) -> bool:
        return self._push_notifications_enabled

    @pushNotificationsEnabled.setter
    def pushNotificationsEnabled(self, value: bool) -> None:
        next_value = bool(value)
        if self._push_notifications_enabled == next_value:
            return
        self._push_notifications_enabled = next_value
        self.system_tray.set_notifications_enabled(self._push_notifications_enabled)
        self.pushNotificationsChanged.emit()
        self._save_state()

    @QtCore.Slot()
'''
