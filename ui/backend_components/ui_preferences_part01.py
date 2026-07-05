from __future__ import annotations

BODY = r'''    # --- Theme properties ---

    @QtCore.Property(str, notify=themeChanged)
    def accentColor(self) -> str:
        return self.theme_manager.accent_color()

    @accentColor.setter
    def accentColor(self, value: str) -> None:
        self.theme_manager.set_accent_color(value)
        self.themeChanged.emit()

    @QtCore.Property(str, notify=themeChanged)
    def themeMode(self) -> str:
        return self.theme_manager.theme_mode()

    @themeMode.setter
    def themeMode(self, value: str) -> None:
        self.theme_manager.set_theme_mode(value)
        self.themeChanged.emit()

    @QtCore.Property(str, notify=themeChanged)
    def effectiveThemeMode(self) -> str:
        mode = self.theme_manager.theme_mode()
        if mode == "high_contrast":
            return "high_contrast"
        if mode == "auto":
            return "dark" if ThemeManager.detect_os_dark_mode() else "light"
        return mode if mode in {"dark", "light"} else "dark"

    @QtCore.Property(str, notify=themeChanged)
    def layoutMode(self) -> str:
        return self.theme_manager.layout_mode()

    @layoutMode.setter
    def layoutMode(self, value: str) -> None:
        self.theme_manager.set_layout_mode(value)
        self.themeChanged.emit()

    @QtCore.Property(float, notify=themeChanged)
    def fontScale(self) -> float:
        return self.theme_manager.font_scale()

    @fontScale.setter
    def fontScale(self, value: float) -> None:
        self.theme_manager.set_font_scale(value)
        self.themeChanged.emit()

    @QtCore.Property(bool, notify=themeChanged)
    def beginnerMode(self) -> bool:
        return self.theme_manager.beginner_mode()

    @beginnerMode.setter
    def beginnerMode(self, value: bool) -> None:
        self.theme_manager.set_beginner_mode(value)
        self.themeChanged.emit()

    @QtCore.Property("QVariantList", notify=themeChanged)
    def accentPresets(self) -> List[Dict[str, str]]:
        return self.theme_manager.accent_presets()

    @QtCore.Property("QVariantMap", notify=themeChanged)
    def layoutConfig(self) -> Dict[str, Any]:
        return self.theme_manager.layout_config()

    @QtCore.Slot(result=bool)
    def detectOsDarkMode(self) -> bool:
        return ThemeManager.detect_os_dark_mode()

    @QtCore.Slot()
    def autoDetectTheme(self) -> None:
        is_dark = ThemeManager.detect_os_dark_mode()
        self.themeMode = "dark" if is_dark else "light"

    @QtCore.Slot("QVariantMap")
    def importTheme(self, data: Dict[str, Any]) -> None:
        self.theme_manager.import_theme(dict(data or {}))
        self.themeChanged.emit()
        self._append_log("OK", "Тему імпортовано.")

    @QtCore.Slot(result="QVariantMap")
    def exportTheme(self) -> Dict[str, Any]:
        return self.theme_manager.export_theme()

    @QtCore.Property(bool, notify=errorStateChanged)
    def hasLastError(self) -> bool:
        return bool(self._last_error_details)

    @QtCore.Property(str, notify=errorStateChanged)
    def lastErrorTitle(self) -> str:
        return self._last_error_title

    @QtCore.Property(str, notify=errorStateChanged)
    def lastErrorDetails(self) -> str:
        return self._last_error_details

    @QtCore.Slot()
    def clearLastError(self) -> None:
        self._last_error_title = ""
        self._last_error_details = ""
        self._last_error_log = ""
        self.errorStateChanged.emit()

    @QtCore.Slot()
    def copyLastErrorLog(self) -> None:
        text = self._last_error_log or self._last_error_details or "\n".join(self._log_lines[-80:])
        if text:
            QtWidgets.QApplication.clipboard().setText(text)

    @QtCore.Slot(int, int, int, int)
    def saveWindowState(self, x: int, y: int, width: int, height: int) -> None:
        self.theme_manager.set_window_state(x, y, width, height)

    @QtCore.Slot(result="QVariantMap")
    def loadWindowState(self) -> Dict[str, int]:
        return self.theme_manager.window_state()

    # --- Shortcut properties ---

    @QtCore.Property("QVariantList", notify=shortcutsChanged)
    def allShortcuts(self) -> List[Dict[str, str]]:
'''
