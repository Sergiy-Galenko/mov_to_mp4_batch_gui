"""System tray integration: tray menu, progress icon, and desktop notifications."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets


class SystemTrayService(QtCore.QObject):
    """Manages system tray icon, menu, and desktop notifications."""

    showRequested = QtCore.Signal()
    quitRequested = QtCore.Signal()
    startRequested = QtCore.Signal()
    stopRequested = QtCore.Signal()
    pauseRequested = QtCore.Signal()

    def __init__(
        self,
        parent: Optional[QtCore.QObject] = None,
        app_title: str = "Media Converter",
    ) -> None:
        super().__init__(parent)
        self._app_title = app_title
        self._tray: Optional[QtWidgets.QSystemTrayIcon] = None
        self._default_icon = QtGui.QIcon()
        self._progress = 0.0
        self._is_running = False
        self._enabled = False
        self._tray_visible = False
        self._notifications_enabled = True

    def setup(self, window: QtWidgets.QWidget) -> None:
        """Initialize the system tray icon and menu."""
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        if self._tray:
            self._apply_visibility()
            return

        self._window = window
        self._tray = QtWidgets.QSystemTrayIcon(self)
        self._tray.setToolTip(self._app_title)

        self._default_icon = self._create_default_icon()
        self._tray.setIcon(self._default_icon)

        menu = QtWidgets.QMenu()
        show_action = menu.addAction("Показати вікно")
        show_action.triggered.connect(self._on_show)
        menu.addSeparator()
        self._start_action = menu.addAction("Старт конвертації")
        self._start_action.triggered.connect(self.startRequested.emit)
        self._pause_action = menu.addAction("Пауза")
        self._pause_action.triggered.connect(self.pauseRequested.emit)
        self._stop_action = menu.addAction("Стоп")
        self._stop_action.triggered.connect(self.stopRequested.emit)
        menu.addSeparator()
        quit_action = menu.addAction("Вийти")
        quit_action.triggered.connect(self.quitRequested.emit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._enabled = True
        self._apply_visibility()

    def show(self) -> None:
        """Show the tray icon."""
        if self._tray:
            self._tray.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        if self._tray:
            self._tray.hide()

    def set_visible(self, visible: bool) -> None:
        self._tray_visible = bool(visible)
        self._apply_visibility()

    def update_progress(self, progress: float, is_running: bool = True) -> None:
        """Update the tray icon to show conversion progress."""
        self._progress = max(0.0, min(1.0, progress))
        self._is_running = is_running

        if not self._tray:
            return

        if is_running:
            icon = self._create_progress_icon(self._progress)
            self._tray.setIcon(icon)
            self._tray.setToolTip(f"{self._app_title} - {int(self._progress * 100)}%")
        else:
            self._tray.setIcon(self._default_icon)
            self._tray.setToolTip(self._app_title)

        self._update_menu_state(is_running)

    def notify(
        self,
        title: str,
        message: str,
        icon: QtWidgets.QSystemTrayIcon.MessageIcon = QtWidgets.QSystemTrayIcon.Information,
        duration_ms: int = 5000,
    ) -> None:
        """Show a desktop notification balloon."""
        if not self._tray or not self._notifications_enabled:
            return
        self._apply_visibility()
        self._tray.showMessage(title, message, icon, duration_ms)

    def notify_success(self, message: str) -> None:
        """Show a success notification."""
        self.notify("Конвертація завершена", message, QtWidgets.QSystemTrayIcon.Information)

    def notify_error(self, message: str) -> None:
        """Show an error notification."""
        self.notify("Помилка", message, QtWidgets.QSystemTrayIcon.Critical)

    def notify_warning(self, message: str) -> None:
        """Show a warning notification."""
        self.notify("Увага", message, QtWidgets.QSystemTrayIcon.Warning)

    def set_notifications_enabled(self, enabled: bool) -> None:
        self._notifications_enabled = bool(enabled)
        self._apply_visibility()

    @property
    def is_available(self) -> bool:
        return self._enabled and self._tray is not None

    def _apply_visibility(self) -> None:
        if not self._tray:
            return
        if self._tray_visible or self._notifications_enabled:
            self._tray.show()
        else:
            self._tray.hide()

    def _on_show(self) -> None:
        self.showRequested.emit()

    def _on_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.showRequested.emit()

    def _update_menu_state(self, is_running: bool) -> None:
        if hasattr(self, "_start_action"):
            self._start_action.setEnabled(not is_running)
        if hasattr(self, "_pause_action"):
            self._pause_action.setEnabled(is_running)
        if hasattr(self, "_stop_action"):
            self._stop_action.setEnabled(is_running)

    def _create_default_icon(self) -> QtGui.QIcon:
        """Create the default tray icon."""
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setBrush(QtGui.QColor("#3D8EFF"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)

        painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2.5))
        font = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(QtCore.QRect(2, 2, 28, 28), QtCore.Qt.AlignCenter, "M")
        painter.end()
        return QtGui.QIcon(pixmap)

    def _create_progress_icon(self, progress: float) -> QtGui.QIcon:
        """Create tray icon with progress arc overlay."""
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setBrush(QtGui.QColor("#1E2330"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)

        span_angle = int(progress * 360 * 16)
        painter.setPen(QtGui.QPen(QtGui.QColor("#3D8EFF"), 3))
        painter.drawArc(4, 4, 24, 24, 90 * 16, -span_angle)

        painter.setPen(QtGui.QColor("white"))
        font = QtGui.QFont("Arial", 8, QtGui.QFont.Bold)
        painter.setFont(font)
        text = f"{int(progress * 100)}"
        painter.drawText(QtCore.QRect(2, 2, 28, 28), QtCore.Qt.AlignCenter, text)
        painter.end()
        return QtGui.QIcon(pixmap)
