"""Theme manager — handles accent colors, layout modes, and window state.

Supports:
  - Accent color presets and custom hex colors
  - Auto-detect OS dark/light mode preference
  - Layout modes: compact / comfortable / spacious
  - Window position/size persistence
  - Theme import/export as JSON
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.paths import APP_DATA_DIR
from utils.state import load_json_state, save_json_state

THEME_STATE_PATH = APP_DATA_DIR / "theme_config.json"

# Pre-defined accent color palettes
ACCENT_PRESETS: list[dict[str, str]] = [
    {"name": "Blue", "color": "#2563EB"},
    {"name": "Purple", "color": "#7C3AED"},
    {"name": "Teal", "color": "#0F766E"},
    {"name": "Rose", "color": "#E11D48"},
    {"name": "Amber", "color": "#D97706"},
    {"name": "Emerald", "color": "#15803D"},
    {"name": "Cyan", "color": "#0891B2"},
    {"name": "Indigo", "color": "#4F46E5"},
    {"name": "Pink", "color": "#DB2777"},
    {"name": "Orange", "color": "#EA580C"},
]

# Layout mode definitions
LAYOUT_MODES = {
    "compact": {
        "font_scale": 0.85,
        "spacing_scale": 0.75,
        "sidebar_width": 180,
        "card_padding": 8,
    },
    "comfortable": {
        "font_scale": 1.0,
        "spacing_scale": 1.0,
        "sidebar_width": 220,
        "card_padding": 12,
    },
    "spacious": {
        "font_scale": 1.1,
        "spacing_scale": 1.25,
        "sidebar_width": 260,
        "card_padding": 16,
    },
}


class ThemeManager:
    """Manages UI theming, layout, and window state persistence."""

    def __init__(self, path: Path = THEME_STATE_PATH) -> None:
        self.path = path
        self._state = load_json_state(path)

    def accent_color(self) -> str:
        return str(self._state.get("accent_color") or "#2563EB")

    def set_accent_color(self, color: str) -> None:
        self._state["accent_color"] = str(color or "#2563EB")
        self._save()

    def theme_mode(self) -> str:
        """Return 'dark', 'light', 'auto', or 'high_contrast'."""
        return str(self._state.get("theme_mode") or "light")

    def set_theme_mode(self, mode: str) -> None:
        normalized = "auto" if mode == "system" else str(mode or "light")
        self._state["theme_mode"] = normalized if normalized in ("dark", "light", "auto", "high_contrast") else "light"
        self._save()

    def layout_mode(self) -> str:
        """Return 'compact', 'comfortable', or 'spacious'."""
        return str(self._state.get("layout_mode") or "comfortable")

    def set_layout_mode(self, mode: str) -> None:
        self._state["layout_mode"] = mode if mode in LAYOUT_MODES else "comfortable"
        self._save()

    def layout_config(self) -> dict[str, Any]:
        """Return the current layout configuration dict."""
        mode = self.layout_mode()
        return dict(LAYOUT_MODES.get(mode, LAYOUT_MODES["comfortable"]))

    def font_scale(self) -> float:
        """Return custom font scaling factor."""
        scale = self._state.get("font_scale")
        if scale is not None:
            return max(0.7, min(float(scale), 1.5))
        return self.layout_config().get("font_scale", 1.0)

    def set_font_scale(self, scale: float) -> None:
        self._state["font_scale"] = max(0.7, min(float(scale), 1.5))
        self._save()

    def window_state(self) -> dict[str, int]:
        """Return saved window geometry: {x, y, width, height}."""
        return dict(self._state.get("window_state") or {})

    def set_window_state(self, x: int, y: int, width: int, height: int) -> None:
        self._state["window_state"] = {
            "x": int(x),
            "y": int(y),
            "width": max(800, int(width)),
            "height": max(600, int(height)),
        }
        self._save()

    def sidebar_collapsed(self) -> bool:
        return bool(self._state.get("sidebar_collapsed", False))

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        self._state["sidebar_collapsed"] = bool(collapsed)
        self._save()

    def beginner_mode(self) -> bool:
        """Return whether beginner mode (simplified UI) is active."""
        return bool(self._state.get("beginner_mode", False))

    def set_beginner_mode(self, enabled: bool) -> None:
        self._state["beginner_mode"] = bool(enabled)
        self._save()

    def accent_presets(self) -> list[dict[str, str]]:
        """Return list of accent color presets."""
        return list(ACCENT_PRESETS)

    def export_theme(self) -> dict[str, Any]:
        """Export current theme configuration."""
        return {
            "accent_color": self.accent_color(),
            "theme_mode": self.theme_mode(),
            "layout_mode": self.layout_mode(),
            "font_scale": self.font_scale(),
            "sidebar_collapsed": self.sidebar_collapsed(),
            "beginner_mode": self.beginner_mode(),
        }

    def import_theme(self, data: dict[str, Any]) -> None:
        """Import theme configuration from a dict."""
        if not isinstance(data, dict):
            return
        if "accent_color" in data:
            self.set_accent_color(str(data["accent_color"]))
        if "theme_mode" in data:
            self.set_theme_mode(str(data["theme_mode"]))
        if "layout_mode" in data:
            self.set_layout_mode(str(data["layout_mode"]))
        if "font_scale" in data:
            self.set_font_scale(float(data["font_scale"]))
        if "beginner_mode" in data:
            self.set_beginner_mode(bool(data["beginner_mode"]))

    def _save(self) -> None:
        save_json_state(self.path, self._state)

    @staticmethod
    def detect_os_dark_mode() -> bool:
        """Detect if the OS is in dark mode. Returns True for dark, False for light."""
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return value == 0  # 0 means dark mode
            except Exception:
                return True
        elif sys.platform == "darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True, text=True, timeout=2,
                )
                return "Dark" in result.stdout
            except Exception:
                return True
        # Default to dark mode on Linux/other
        return True
