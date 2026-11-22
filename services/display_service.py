"""Display Service — detects display parameters and provides adaptive UI recommendations.

Capabilities:
  - Resolution and usable desktop work-area detection (excluding taskbars/docks).
  - High-DPI, device pixel ratio, and DPI density monitoring.
  - Multi-monitor topology and active screen geometry awareness.
  - Screen classification: compact, standard, large, ultrawide, portrait.
  - Recommended UI adjustments: layout density, font scaling factor, sidebar collapsing.
  - Safe window geometry calculation and off-screen bounds recovery.
  - Live event monitoring for resolution/scaling changes.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass
class ScreenMetrics:
    screen_width: int = 1920
    screen_height: int = 1080
    available_width: int = 1920
    available_height: int = 1040
    available_x: int = 0
    available_y: int = 0
    device_pixel_ratio: float = 1.0
    logical_dpi: float = 96.0
    physical_dpi: float = 96.0
    is_portrait: bool = False
    is_ultrawide: bool = False
    category: str = "standard"  # "compact", "standard", "large", "ultrawide"
    recommended_layout_mode: str = "comfortable"  # "compact", "comfortable", "spacious"
    recommended_font_scale: float = 1.0
    recommended_sidebar_collapsed: bool = False
    recommended_window_width: int = 1240
    recommended_window_height: int = 840
    recommended_window_x: int = 100
    recommended_window_y: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "screenWidth": self.screen_width,
            "screenHeight": self.screen_height,
            "availableWidth": self.available_width,
            "availableHeight": self.available_height,
            "availableX": self.available_x,
            "availableY": self.available_y,
            "devicePixelRatio": round(self.device_pixel_ratio, 2),
            "logicalDpi": round(self.logical_dpi, 1),
            "physicalDpi": round(self.physical_dpi, 1),
            "isPortrait": self.is_portrait,
            "isUltraWide": self.is_ultrawide,
            "category": self.category,
            "recommendedLayoutMode": self.recommended_layout_mode,
            "recommendedFontScale": round(self.recommended_font_scale, 2),
            "recommendedSidebarCollapsed": self.recommended_sidebar_collapsed,
            "recommendedWindowWidth": self.recommended_window_width,
            "recommendedWindowHeight": self.recommended_window_height,
            "recommendedWindowX": self.recommended_window_x,
            "recommendedWindowY": self.recommended_window_y,
        }


def classify_display(
    available_width: int,
    available_height: int,
    dpr: float = 1.0,
    logical_dpi: float = 96.0,
) -> tuple[str, bool, bool]:
    """Classify display into category and return (category, is_portrait, is_ultrawide)."""
    is_portrait = available_height > available_width
    aspect_ratio = available_width / max(1, available_height)
    is_ultrawide = aspect_ratio >= 2.05 and available_width >= 2400

    if available_width < 1200 or available_height < 740:
        category = "compact"
    elif is_ultrawide:
        category = "ultrawide"
    elif available_width >= 2200 and available_height >= 1300:
        category = "large"
    else:
        category = "standard"

    return category, is_portrait, is_ultrawide


def calculate_screen_metrics(
    screen_width: int,
    screen_height: int,
    available_width: int,
    available_height: int,
    available_x: int = 0,
    available_y: int = 0,
    dpr: float = 1.0,
    logical_dpi: float = 96.0,
    physical_dpi: float = 96.0,
) -> ScreenMetrics:
    """Calculate complete ScreenMetrics and recommendations for given dimensions."""
    category, is_portrait, is_ultrawide = classify_display(
        available_width, available_height, dpr, logical_dpi
    )

    # Calculate optimal window width & height
    if category == "compact" or is_portrait:
        rec_layout = "compact"
        rec_sidebar_collapsed = available_width < 1120 or is_portrait
        rec_font_scale = 0.90 if available_width < 1000 else 0.95
        win_w = max(760, min(available_width - 20, int(available_width * 0.94)))
        win_h = max(680, min(available_height - 30, int(available_height * 0.92)))
    elif category == "large":
        rec_layout = "spacious"
        rec_sidebar_collapsed = False
        rec_font_scale = 1.05 if dpr <= 1.25 else 1.0
        win_w = max(1100, min(1680, int(available_width * 0.80)))
        win_h = max(780, min(1080, int(available_height * 0.82)))
    elif category == "ultrawide":
        rec_layout = "comfortable"
        rec_sidebar_collapsed = False
        rec_font_scale = 1.0
        win_w = max(1240, min(1800, int(available_width * 0.65)))
        win_h = max(800, min(1000, int(available_height * 0.82)))
    else:  # standard
        rec_layout = "comfortable"
        rec_sidebar_collapsed = False
        rec_font_scale = 1.0
        win_w = max(800, min(1360, int(available_width * 0.85)))
        win_h = max(680, min(900, int(available_height * 0.85)))

    win_w = min(win_w, max(760, available_width))
    win_h = min(win_h, max(680, available_height))

    win_x = available_x + max(0, (available_width - win_w) // 2)
    win_y = available_y + max(0, (available_height - win_h) // 2)

    return ScreenMetrics(
        screen_width=screen_width,
        screen_height=screen_height,
        available_width=available_width,
        available_height=available_height,
        available_x=available_x,
        available_y=available_y,
        device_pixel_ratio=dpr,
        logical_dpi=logical_dpi,
        physical_dpi=physical_dpi,
        is_portrait=is_portrait,
        is_ultrawide=is_ultrawide,
        category=category,
        recommended_layout_mode=rec_layout,
        recommended_font_scale=rec_font_scale,
        recommended_sidebar_collapsed=rec_sidebar_collapsed,
        recommended_window_width=win_w,
        recommended_window_height=win_h,
        recommended_window_x=win_x,
        recommended_window_y=win_y,
    )


class DisplayService(QtCore.QObject):
    """Monitors screens and provides adaptive display recommendations."""

    metricsChanged = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._connected_screens: list[QtGui.QScreen] = []
        self._current_metrics = self.detect_metrics()
        self._setup_screen_listeners()

    def detect_metrics(self, screen: QtGui.QScreen | None = None) -> ScreenMetrics:
        """Detect current screen metrics from Qt runtime or fallback defaults."""
        app = QtWidgets.QApplication.instance()
        if not app or not isinstance(app, QtGui.QGuiApplication):
            return calculate_screen_metrics(1920, 1080, 1920, 1040, 0, 0, 1.0, 96.0, 96.0)

        target_screen = screen or QtGui.QGuiApplication.primaryScreen()
        if not target_screen:
            return calculate_screen_metrics(1920, 1080, 1920, 1040, 0, 0, 1.0, 96.0, 96.0)

        geom = target_screen.geometry()
        avail = target_screen.availableGeometry()
        dpr = target_screen.devicePixelRatio()
        logical_dpi = target_screen.logicalDotsPerInch()
        physical_dpi = target_screen.physicalDotsPerInch()

        return calculate_screen_metrics(
            screen_width=geom.width(),
            screen_height=geom.height(),
            available_width=avail.width(),
            available_height=avail.height(),
            available_x=avail.x(),
            available_y=avail.y(),
            dpr=float(dpr) if dpr else 1.0,
            logical_dpi=float(logical_dpi) if logical_dpi else 96.0,
            physical_dpi=float(physical_dpi) if physical_dpi else 96.0,
        )

    def current_metrics(self) -> ScreenMetrics:
        return self._current_metrics

    def refresh(self, screen: QtGui.QScreen | None = None) -> None:
        """Recalculate metrics and emit metricsChanged if updated."""
        new_metrics = self.detect_metrics(screen)
        if new_metrics != self._current_metrics:
            self._current_metrics = new_metrics
            self.metricsChanged.emit()

    def ensure_window_in_bounds(
        self, x: int, y: int, width: int, height: int
    ) -> tuple[int, int, int, int]:
        """Validate window coordinates against connected screens.

        If coordinates fall outside visible screen area (e.g. after disconnecting
        an external monitor), recover by centering on primary screen.
        """
        metrics = self._current_metrics
        win_rect = QtCore.QRect(x, y, max(400, width), max(300, height))
        app = QtWidgets.QApplication.instance()
        if not app or not isinstance(app, QtGui.QGuiApplication):
            return x, y, width, height
        screens = QtGui.QGuiApplication.screens() if (app and isinstance(app, QtGui.QGuiApplication)) else []

        screens = QtGui.QGuiApplication.screens()
        if not screens:
            return x, y, width, height
            avail_rect = QtCore.QRect(
                metrics.available_x, metrics.available_y, metrics.available_width, metrics.available_height
            )
            intersect = avail_rect.intersected(win_rect)
            visible_on_any = intersect.width() >= 150 and intersect.height() >= 100
        else:
            visible_on_any = False
            for scr in screens:
                avail = scr.availableGeometry()
                intersect = avail.intersected(win_rect)
                if intersect.width() >= 150 and intersect.height() >= 100:
                    visible_on_any = True
                    break

        win_rect = QtCore.QRect(x, y, max(400, width), max(300, height))
        visible_on_any = False
        for scr in screens:
            avail = scr.availableGeometry()
            intersect = avail.intersected(win_rect)
            # Window must have at least 150x100px visible on some screen
            if intersect.width() >= 150 and intersect.height() >= 100:
                visible_on_any = True
                break

        metrics = self._current_metrics
        if not visible_on_any:
            # Offscreen: center on current primary screen
            width = min(max(760, width), metrics.available_width)
            height = min(max(680, height), metrics.available_height)
            x = metrics.available_x + max(0, (metrics.available_width - width) // 2)
            y = metrics.available_y + max(0, (metrics.available_height - height) // 2)
        else:
            # Clamp sizes if larger than available area
            width = min(width, metrics.available_width)
            height = min(height, metrics.available_height)

        return x, y, width, height

    def _setup_screen_listeners(self) -> None:
        app = QtWidgets.QApplication.instance()
        if not app or not isinstance(app, QtGui.QGuiApplication):
            return

        with contextlib.suppress(Exception):
            app.screenAdded.connect(self._on_screens_changed)
        with contextlib.suppress(Exception):
            app.screenRemoved.connect(self._on_screens_changed)
        try:
            if hasattr(app, "primaryScreenChanged"):
                app.primaryScreenChanged.connect(self._on_screens_changed)
        except Exception:
            pass
        self._connect_screens()

    def _connect_screens(self) -> None:
        app = QtWidgets.QApplication.instance()
        if not app or not isinstance(app, QtGui.QGuiApplication):
            return
        try:
            screens = QtGui.QGuiApplication.screens() if hasattr(QtGui.QGuiApplication, "screens") else []
        except Exception:
            screens = []
        for scr in screens:
            if scr not in self._connected_screens:
                with contextlib.suppress(Exception):
                    scr.geometryChanged.connect(self._on_screen_geometry_changed)
                with contextlib.suppress(Exception):
                    scr.availableGeometryChanged.connect(self._on_screen_geometry_changed)
                with contextlib.suppress(Exception):
                    scr.logicalDotsPerInchChanged.connect(self._on_screen_geometry_changed)
                self._connected_screens.append(scr)

    def _on_screen_geometry_changed(self, *args) -> None:
        self.refresh()

    def _on_screens_changed(self, *args) -> None:
        self._connect_screens()
        self.refresh()

