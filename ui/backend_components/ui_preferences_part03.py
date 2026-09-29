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

    @QtCore.Property(bool, notify=sourceUpdateChanged)
    def sourceUpdateChecking(self) -> bool:
        return self._source_update_checking

    @QtCore.Property(bool, notify=sourceUpdateChanged)
    def sourceUpdateAvailable(self) -> bool:
        return self._source_update_available

    @QtCore.Property(bool, notify=sourceUpdateChanged)
    def sourceUpdateRestartRequired(self) -> bool:
        return self._source_update_restart_required

    @QtCore.Property(str, notify=sourceUpdateChanged)
    def sourceUpdateStatus(self) -> str:
        return self._source_update_status

    @QtCore.Property(str, notify=sourceUpdateChanged)
    def sourceUpdateCurrentCommit(self) -> str:
        return self._source_update_local_commit

    @QtCore.Property(str, notify=sourceUpdateChanged)
    def sourceUpdateRemoteCommit(self) -> str:
        return self._source_update_remote_commit

    @QtCore.Slot()
    def checkSourceUpdate(self) -> None:
        if self._source_update_checking:
            return
        self._source_update_checking = True
        self._source_update_available = False
        self._source_update_restart_required = False
        self._source_update_status = "Перевіряємо оновлення у GitHub…"
        self.sourceUpdateChanged.emit()
        threading.Thread(target=lambda: self.event_queue.put(("source_update_done", self.source_update_service.check())), daemon=True).start()

    @QtCore.Slot()
    def applySourceUpdate(self) -> None:
        if self._source_update_checking or not self._source_update_available:
            return
        self._source_update_checking = True
        self._source_update_status = "Завантажуємо оновлення…"
        self.sourceUpdateChanged.emit()
        threading.Thread(target=lambda: self.event_queue.put(("source_update_done", self.source_update_service.apply())), daemon=True).start()

    def _apply_source_update_result(self, info: SourceUpdateInfo) -> None:
        self._source_update_checking = False
        self._source_update_available = bool(info.available)
        self._source_update_restart_required = bool(info.restart_required)
        self._source_update_status = info.message
        self._source_update_local_commit = info.local_commit
        self._source_update_remote_commit = info.remote_commit
        if info.downloaded_path:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(info.downloaded_path))
        self.sourceUpdateChanged.emit()
        self._append_log("OK" if info.available or info.restart_required else "INFO", f"Source update: {info.message}")
        self.toastRequested.emit(info.message)

    @QtCore.Slot()
    def restartAfterSourceUpdate(self) -> None:
        if not self._source_update_restart_required:
            return
        if QtCore.QProcess.startDetached(sys.executable, list(sys.argv)):
            QtWidgets.QApplication.quit()
        else:
            self._source_update_status = "Оновлення завантажено. Закрийте й запустіть застосунок вручну."
            self.sourceUpdateChanged.emit()

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
