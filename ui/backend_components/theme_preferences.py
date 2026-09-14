from __future__ import annotations

BODY = r'''    @QtCore.Property("QVariantMap", notify=themeChanged)
    def themePalette(self) -> Dict[str, str]:
        return self.theme_manager.palette(self.effectiveThemeMode)

    @QtCore.Property("QVariantMap", notify=themeChanged)
    def themeColorOverrides(self) -> Dict[str, str]:
        return self.theme_manager.color_overrides(self.effectiveThemeMode)

    @QtCore.Property("QVariantList", constant=True)
    def themeColorDefinitions(self) -> List[Dict[str, str]]:
        return self.theme_manager.color_definitions()

    @QtCore.Property("QVariantList", notify=themeChanged)
    def savedThemeNames(self) -> List[str]:
        return self.theme_manager.saved_themes()

    @QtCore.Slot(str, str, result=bool)
    def setThemeColor(self, key: str, color: str) -> bool:
        try:
            self.theme_manager.set_color(key, color, self.effectiveThemeMode)
        except (ValueError, OSError):
            return False
        self.themeChanged.emit()
        return True

    @QtCore.Slot(str)
    def resetThemeColor(self, key: str) -> None:
        self.theme_manager.reset_color(key, self.effectiveThemeMode)
        self.themeChanged.emit()

    @QtCore.Slot()
    def resetThemeColors(self) -> None:
        self.theme_manager.reset_colors(self.effectiveThemeMode)
        self.themeChanged.emit()

    @QtCore.Slot(str, result=bool)
    def saveNamedTheme(self, name: str) -> bool:
        try:
            self.theme_manager.save_theme(name, self.effectiveThemeMode)
        except (ValueError, OSError):
            return False
        self.themeChanged.emit()
        self.toastRequested.emit(self._tr("appearance.saved"))
        return True

    @QtCore.Slot(str, result=bool)
    def loadNamedTheme(self, name: str) -> bool:
        try:
            self.theme_manager.load_theme(name)
        except (ValueError, TypeError, OSError):
            return False
        self.themeChanged.emit()
        return True

    @QtCore.Slot(str)
    def deleteNamedTheme(self, name: str) -> None:
        self.theme_manager.delete_theme(name)
        self.themeChanged.emit()

    @QtCore.Slot()
    def importThemeFile(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, self._tr("import_theme"), "", "JSON (*.json)")
        if not path:
            return
        try:
            if Path(path).stat().st_size > 1024 * 1024:
                raise ValueError("Theme file exceeds 1 MB")
            data = load_json_file(Path(path))
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON theme")
        except (ValueError, OSError) as exc:
            self.toastRequested.emit(self._tr("appearance.invalid_file") + ": " + str(exc))
            return
        if self.importTheme(data):
            self.toastRequested.emit(self._tr("appearance.imported"))

    @QtCore.Slot()
    def exportThemeFile(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, self._tr("export_theme"), "my-theme.json", "JSON (*.json)")
        if not path:
            return
        try:
            save_json_file(Path(path), self.exportTheme())
        except OSError as exc:
            self.toastRequested.emit(str(exc))
            return
        self.toastRequested.emit(self._tr("appearance.exported"))

    def _apply_widget_theme(self) -> None:
        application = QtWidgets.QApplication.instance()
        if application is None:
            return
        colors = self.themePalette
        palette = QtGui.QPalette()
        roles = {
            "Window": "panelBackground", "WindowText": "textPrimary", "Base": "input",
            "AlternateBase": "panelSecondary", "ToolTipBase": "panelSecondary", "ToolTipText": "textPrimary",
            "Text": "textPrimary", "Button": "panelSecondary", "ButtonText": "textPrimary",
            "BrightText": "textOnAccent", "Highlight": "accent", "HighlightedText": "textOnAccent",
            "Link": "accent", "LinkVisited": "accentHover", "PlaceholderText": "textDisabled",
            "Light": "borderDefault", "Midlight": "panelHover", "Mid": "borderMuted",
            "Dark": "input", "Shadow": "windowBackground", "Accent": "accent",
        }
        for role, key in roles.items():
            palette.setColor(getattr(QtGui.QPalette.ColorRole, role), QtGui.QColor(colors[key]))
        for role in ("WindowText", "Text", "ButtonText", "PlaceholderText"):
            palette.setColor(QtGui.QPalette.ColorGroup.Disabled, getattr(QtGui.QPalette.ColorRole, role), QtGui.QColor(colors["textDisabled"]))
        application.setPalette(palette)

    def _on_system_theme_changed(self, *_args) -> None:
        if self.themeMode == "auto":
            self.themeChanged.emit()
'''
