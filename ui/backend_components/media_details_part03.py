from __future__ import annotations

BODY = r'''            return
        settings = dict(entry.get("settings") or {})
        if not settings:
            self._append_log("WARN", "У цьому запуску немає збережених налаштувань.")
            return
        self._last_settings_map = settings
        self.presetLoaded.emit(settings)
        self._refresh_output_preview(settings)
        self._append_log("OK", "Налаштування запуску завантажено з історії.")

    @QtCore.Slot(int)
    def rerunHistory(self, index: int) -> None:
        entry = self.history_model.entry_at(index)
        if not entry:
            return
        settings = dict(entry.get("settings") or {})
        paths = [Path(str(result.get("path"))) for result in entry.get("results", []) if result.get("path")]
        if paths:
            self._add_paths(paths)
        self._start_conversion(settings, only_paths={path.expanduser() for path in paths})
'''
