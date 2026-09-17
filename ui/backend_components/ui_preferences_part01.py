from __future__ import annotations

BODY = r"""    # --- Theme properties ---

    @QtCore.Property(str, notify=themeChanged)
    def accentColor(self) -> str:
        return self.themePalette["accent"]

    @accentColor.setter
    def accentColor(self, value: str) -> None:
        self.setThemeColor("accent", value)

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
            scheme = QtGui.QGuiApplication.styleHints().colorScheme()
            return "light" if scheme == QtCore.Qt.ColorScheme.Light else "dark"
        valid_modes = {"dark", "light", "obsidian", "oled", "midnight", "high_contrast"}
        return mode if mode in valid_modes else "dark"

    @QtCore.Property(str, notify=queueViewModeChanged)
    def queueViewMode(self) -> str:
        return self.theme_manager.queue_view_mode()

    @queueViewMode.setter
    def queueViewMode(self, value: str) -> None:
        self.theme_manager.set_queue_view_mode(value)
        self.queueViewModeChanged.emit()

    @QtCore.Property(int, notify=concurrencyLimitChanged)
    def concurrencyLimit(self) -> int:
        return int(self.settings_manager.state.get("concurrency_limit", 0))

    @concurrencyLimit.setter
    def concurrencyLimit(self, value: int) -> None:
        val = max(0, min(16, int(value)))
        self.settings_manager.state["concurrency_limit"] = val
        self.settings_manager.save()
        self.concurrencyLimitChanged.emit()

    @QtCore.Property(str, notify=outputTemplateChanged)
    def outputTemplate(self) -> str:
        return str(self.settings_manager.state.get("output_template", "{stem}"))

    @outputTemplate.setter
    def outputTemplate(self, value: str) -> None:
        val = str(value or "{stem}").strip()
        self.settings_manager.state["output_template"] = val
        self.settings_manager.save()
        self.outputTemplateChanged.emit()

    @QtCore.Slot(float, result=str)
    def formatTrimSeconds(self, seconds: float) -> str:
        if seconds < 0:
            return "00:00"
        m = int(seconds) // 60
        s = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 10)
        return f"{m:02d}:{s:02d}.{ms}"

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

    @QtCore.Slot("QVariantMap", result=bool)
    def importTheme(self, data: Dict[str, Any]) -> bool:
        try:
            self.theme_manager.import_theme(data)
        except (ValueError, TypeError, OSError) as exc:
            self.toastRequested.emit(self._tr("appearance.invalid_file") + ": " + str(exc))
            return False
        self.themeChanged.emit()
        return True

    @QtCore.Slot(result="QVariantMap")
    def exportTheme(self) -> Dict[str, Any]:
        return self.theme_manager.export_theme(self.effectiveThemeMode)

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
"""
