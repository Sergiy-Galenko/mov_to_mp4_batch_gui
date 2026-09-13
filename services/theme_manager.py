"""Theme manager — handles accent colors, layout modes, and window state.

Supports:
  - Accent color presets and custom hex colors
  - Auto-detect OS dark/light mode preference
  - Layout modes: compact / comfortable / spacious
  - Window position/size persistence
  - Theme import/export as JSON
"""

from __future__ import annotations

import contextlib
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.paths import APP_DATA_DIR
from app.theme_palette import COLOR_GROUPS, COLOR_KEYS, THEME_MODES, normalize_color, resolve_palette
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
        self._palette_cache: dict[str, dict[str, str]] = {}

    def effective_mode(self) -> str:
        mode = self.theme_mode()
        return ("dark" if self.detect_os_dark_mode() else "light") if mode == "auto" else mode

    def palette(self, mode: str | None = None) -> dict[str, str]:
        mode = mode or self.effective_mode()
        if mode not in self._palette_cache:
            colors = self.color_overrides(mode)
            legacy_accent = self._state.get("accent_color")
            if legacy_accent and "accent" not in colors:
                with contextlib.suppress(ValueError):
                    colors["accent"] = normalize_color(legacy_accent)
            self._palette_cache[mode] = resolve_palette(mode, colors)
        return dict(self._palette_cache[mode])

    def color_overrides(self, mode: str | None = None) -> dict[str, str]:
        all_colors = self._state.get("custom_colors", {})
        raw = all_colors.get(mode or self.effective_mode(), {}) if isinstance(all_colors, dict) else {}
        colors = {}
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in COLOR_KEYS:
                    with contextlib.suppress(ValueError):
                        colors[key] = normalize_color(value)
        return colors

    def set_color(self, key: str, color: str, mode: str | None = None) -> None:
        if key not in COLOR_KEYS:
            raise ValueError(f"Unknown theme color: {key}")
        value = normalize_color(color)
        mode = mode or self.effective_mode()
        colors = self.color_overrides(mode)
        colors[key] = value
        if not isinstance(self._state.get("custom_colors"), dict):
            self._state["custom_colors"] = {}
        self._state["custom_colors"][mode] = colors
        if key == "accent":
            self._state.pop("accent_color", None)
        self._save()

    def reset_color(self, key: str, mode: str | None = None) -> None:
        if key not in COLOR_KEYS:
            raise ValueError(f"Unknown theme color: {key}")
        mode = mode or self.effective_mode()
        colors = self.color_overrides(mode)
        colors.pop(key, None)
        if not isinstance(self._state.get("custom_colors"), dict):
            self._state["custom_colors"] = {}
        self._state["custom_colors"][mode] = colors
        if key == "accent":
            self._state.pop("accent_color", None)
        self._save()

    def reset_colors(self, mode: str | None = None) -> None:
        colors = self._state.get("custom_colors", {})
        if isinstance(colors, dict):
            colors.pop(mode or self.effective_mode(), None)
        self._state.pop("accent_color", None)
        self._save()

    @staticmethod
    def color_definitions() -> list[dict[str, str]]:
        return [{"key": key, "group": group} for group, keys in COLOR_GROUPS.items() for key in keys]

    def accent_color(self) -> str:
        return self.palette()["accent"]

    def set_accent_color(self, color: str) -> None:
        self.set_color("accent", color)

    def theme_mode(self) -> str:
        mode = self._state.get("theme_mode", "dark")
        return mode if isinstance(mode, str) and mode in THEME_MODES else "dark"

    def set_theme_mode(self, mode: str) -> None:
        normalized = "auto" if mode == "system" else str(mode or "dark")
        self._state["theme_mode"] = normalized if normalized in THEME_MODES else "dark"
        self._save()

    def queue_view_mode(self) -> str:
        """Return 'list' or 'grid'."""
        return str(self._state.get("queue_view_mode") or "list")

    def set_queue_view_mode(self, mode: str) -> None:
        self._state["queue_view_mode"] = "grid" if mode == "grid" else "list"
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
        try:
            return self._normalize_scale(self._state.get("font_scale", self.layout_config().get("font_scale", 1.0)))
        except (ValueError, TypeError):
            return 1.0

    @staticmethod
    def _normalize_scale(scale: float) -> float:
        value = float(scale)
        if not math.isfinite(value):
            raise ValueError("Font scale must be finite")
        return max(0.7, min(value, 1.5))

    def set_font_scale(self, scale: float) -> None:
        self._state["font_scale"] = self._normalize_scale(scale)
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

    def export_theme(self, mode: str | None = None) -> dict[str, Any]:
        """Export a complete palette so a shared theme has the same appearance."""
        return {
            "schema_version": 2,
            "theme_mode": mode or self.effective_mode(),
            "colors": self.palette(mode),
            "accent_color": self.palette(mode)["accent"],
            "layout_mode": self.layout_mode(),
            "font_scale": self.font_scale(),
            "sidebar_collapsed": self.sidebar_collapsed(),
            "beginner_mode": self.beginner_mode(),
        }

    def import_theme(self, data: dict[str, Any]) -> None:
        """Validate first, then persist once; a bad file cannot partially apply."""
        if not isinstance(data, dict) or not any(key in data for key in ("colors", "theme_mode", "accent_color")):
            raise ValueError("Not a theme configuration")
        if data.get("schema_version", 1) not in (1, 2):
            raise ValueError("Unsupported theme version")
        mode = data.get("theme_mode", self.theme_mode())
        mode = "auto" if mode == "system" else mode
        if not isinstance(mode, str) or mode not in THEME_MODES:
            raise ValueError("Unknown theme mode")
        colors = data.get("colors", {})
        if not isinstance(colors, dict) or any(key not in COLOR_KEYS for key in colors):
            raise ValueError("Invalid theme color names")
        colors = {key: normalize_color(value) for key, value in colors.items()}
        if "accent_color" in data and "accent" not in colors:
            colors["accent"] = normalize_color(data["accent_color"])
        layout = data.get("layout_mode", self.layout_mode())
        if not isinstance(layout, str) or layout not in LAYOUT_MODES:
            raise ValueError("Unknown layout mode")
        scale = self._normalize_scale(data.get("font_scale", self.font_scale()))
        state = deepcopy(self._state)
        state.update(theme_mode=mode, layout_mode=layout, font_scale=scale)
        state.pop("accent_color", None)
        if not isinstance(state.get("custom_colors"), dict):
            state["custom_colors"] = {}
        target = ("dark" if self.detect_os_dark_mode() else "light") if mode == "auto" else mode
        state["custom_colors"][target] = colors
        for key in ("beginner_mode", "sidebar_collapsed"):
            if key in data:
                if not isinstance(data[key], bool):
                    raise ValueError(f"{key} must be a boolean")
                state[key] = data[key]
        save_json_state(self.path, state)
        self._state = state
        self._palette_cache.clear()

    def saved_themes(self) -> list[str]:
        themes = self._state.get("saved_themes", {})
        return sorted(themes) if isinstance(themes, dict) else []

    def save_theme(self, name: str, mode: str | None = None) -> None:
        name = str(name or "").strip()
        if not name or len(name) > 64:
            raise ValueError("Theme names must contain 1–64 characters")
        if not isinstance(self._state.get("saved_themes"), dict):
            self._state["saved_themes"] = {}
        self._state["saved_themes"][name] = self.export_theme(mode)
        self._save()

    def load_theme(self, name: str) -> None:
        themes = self._state.get("saved_themes", {})
        if not isinstance(themes, dict) or name not in themes:
            raise ValueError("Theme not found")
        self.import_theme(themes[name])

    def delete_theme(self, name: str) -> None:
        themes = self._state.get("saved_themes", {})
        if isinstance(themes, dict):
            themes.pop(name, None)
            self._save()

    def _save(self) -> None:
        self._palette_cache.clear()
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
