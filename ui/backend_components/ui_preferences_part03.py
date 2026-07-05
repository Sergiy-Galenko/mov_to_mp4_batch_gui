from __future__ import annotations

BODY = r'''    def setupSystemTray(self) -> None:
        """Initialize system tray (must be called after window is created)."""
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        window = app.activeWindow()
        if window is None:
            visible_windows = [item for item in QtGui.QGuiApplication.topLevelWindows() if item.isVisible()]
            window = visible_windows[0] if visible_windows else None
        if window is not None:
            self.system_tray.setup(window)
            self.system_tray.set_notifications_enabled(self._push_notifications_enabled)
            self.system_tray.set_visible(self._tray_enabled)
        if window is not None and not self._system_tray_signals_connected:
            self.system_tray.showRequested.connect(self._on_tray_show)
            self.system_tray.quitRequested.connect(self._on_tray_quit)
            self.system_tray.startRequested.connect(lambda: self.startConversion(dict(self._last_settings_map)))
            self.system_tray.stopRequested.connect(self.stopConversion)
            self.system_tray.pauseRequested.connect(self.pauseConversion)
            self._system_tray_signals_connected = True

    def _on_tray_show(self) -> None:
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        window = app.activeWindow()
        if window is None:
            visible_windows = [item for item in QtGui.QGuiApplication.topLevelWindows() if item.isVisible()]
            window = visible_windows[0] if visible_windows else None
        if window is None:
            return
        window.show()
        if hasattr(window, "raise_"):
            window.raise_()
        if hasattr(window, "activateWindow"):
            window.activateWindow()
        elif hasattr(window, "requestActivate"):
            window.requestActivate()

    def _on_tray_quit(self) -> None:
        QtWidgets.QApplication.quit()

    def _send_push_notification(self, title: str, message: str, level: str = "info") -> None:
        if not self._push_notifications_enabled:
            return
        if not self.system_tray.is_available:
            self.setupSystemTray()
        icon = QtWidgets.QSystemTrayIcon.Information
        if level == "error":
            icon = QtWidgets.QSystemTrayIcon.Critical
        elif level == "warning":
            icon = QtWidgets.QSystemTrayIcon.Warning
        self.system_tray.notify(title, message, icon)
'''
