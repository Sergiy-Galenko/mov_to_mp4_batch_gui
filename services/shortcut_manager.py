"""Keyboard shortcut manager — configurable hotkeys for all major actions.

Provides a centralized registry of keyboard shortcuts with:
  - Default key bindings for all major actions
  - User-customizable overrides saved in JSON
  - Import/export shortcut configurations
"""

from __future__ import annotations

from pathlib import Path

from app.paths import APP_DATA_DIR
from utils.state import load_json_state, save_json_state

SHORTCUTS_PATH = APP_DATA_DIR / "shortcuts.json"

# Default keyboard shortcuts
DEFAULT_SHORTCUTS: dict[str, dict[str, str]] = {
    # Conversion actions
    "start_conversion": {"key": "F5", "label": "Start conversion", "category": "conversion"},
    "stop_conversion": {"key": "Escape", "label": "Stop conversion", "category": "conversion"},
    "pause_resume": {"key": "F6", "label": "Pause / Resume", "category": "conversion"},
    "skip_file": {"key": "F7", "label": "Skip current file", "category": "conversion"},
    "retry_failed": {"key": "F8", "label": "Retry failed files", "category": "conversion"},

    # Queue actions
    "add_files": {"key": "Ctrl+O", "label": "Add files", "category": "queue"},
    "add_folder": {"key": "Ctrl+Shift+O", "label": "Add folder", "category": "queue"},
    "remove_selected": {"key": "Delete", "label": "Remove selected", "category": "queue"},
    "select_all": {"key": "Ctrl+A", "label": "Select all", "category": "queue"},
    "clear_queue": {"key": "Ctrl+Shift+Delete", "label": "Clear queue", "category": "queue"},
    "deduplicate": {"key": "Ctrl+D", "label": "Deduplicate queue", "category": "queue"},
    "move_up": {"key": "Alt+Up", "label": "Move selection up", "category": "queue"},
    "move_down": {"key": "Alt+Down", "label": "Move selection down", "category": "queue"},
    "queue_search": {"key": "Ctrl+F", "label": "Focus queue search", "category": "queue"},

    # Navigation
    "nav_queue": {"key": "Ctrl+1", "label": "Go to Queue", "category": "navigation"},
    "nav_analytics": {"key": "Ctrl+2", "label": "Go to Analytics", "category": "navigation"},
    "nav_presets": {"key": "Ctrl+3", "label": "Go to Presets", "category": "navigation"},
    "nav_ffmpeg": {"key": "Ctrl+4", "label": "Go to FFmpeg", "category": "navigation"},
    "nav_youtube": {"key": "Ctrl+5", "label": "Go to YouTube", "category": "navigation"},
    "nav_settings": {"key": "Ctrl+6", "label": "Go to Settings", "category": "navigation"},
    "toggle_sidebar": {"key": "Ctrl+B", "label": "Toggle sidebar", "category": "navigation"},

    # General
    "save_preset": {"key": "Ctrl+S", "label": "Save current preset", "category": "general"},
    "export_project": {"key": "Ctrl+E", "label": "Export project", "category": "general"},
    "import_project": {"key": "Ctrl+I", "label": "Import project", "category": "general"},
    "export_log": {"key": "Ctrl+L", "label": "Export log", "category": "general"},
    "open_output_dir": {"key": "Ctrl+Shift+E", "label": "Open output folder", "category": "general"},
    "toggle_beginner_mode": {"key": "Ctrl+Shift+B", "label": "Toggle beginner mode", "category": "general"},
    "paste_paths": {"key": "Ctrl+V", "label": "Paste file paths / URLs", "category": "general"},
}


class ShortcutManager:
    """Manages keyboard shortcut configuration."""

    def __init__(self, path: Path = SHORTCUTS_PATH) -> None:
        self.path = path
        self._overrides: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        state = load_json_state(self.path)
        self._overrides = {}
        for action_id, key_str in state.items():
            if isinstance(key_str, str) and key_str.strip():
                self._overrides[str(action_id)] = key_str.strip()

    def get_key(self, action_id: str) -> str:
        """Get the key binding for an action (user override or default)."""
        if action_id in self._overrides:
            return self._overrides[action_id]
        default = DEFAULT_SHORTCUTS.get(action_id)
        return default["key"] if default else ""

    def get_label(self, action_id: str) -> str:
        """Get the human-readable label for an action."""
        default = DEFAULT_SHORTCUTS.get(action_id)
        return default["label"] if default else action_id

    def get_category(self, action_id: str) -> str:
        """Get the category of an action."""
        default = DEFAULT_SHORTCUTS.get(action_id)
        return default["category"] if default else "general"

    def set_key(self, action_id: str, key: str) -> None:
        """Set a custom key binding for an action."""
        if action_id not in DEFAULT_SHORTCUTS:
            return
        self._overrides[action_id] = str(key or "").strip()
        self._save()

    def reset_key(self, action_id: str) -> None:
        """Reset an action to its default key binding."""
        self._overrides.pop(action_id, None)
        self._save()

    def reset_all(self) -> None:
        """Reset all shortcuts to defaults."""
        self._overrides.clear()
        self._save()

    def all_shortcuts(self) -> list[dict[str, str]]:
        """Return all shortcuts as a list of dicts."""
        result: list[dict[str, str]] = []
        for action_id, default in DEFAULT_SHORTCUTS.items():
            result.append({
                "action": action_id,
                "key": self.get_key(action_id),
                "default_key": default["key"],
                "label": default["label"],
                "category": default["category"],
                "customized": action_id in self._overrides,
            })
        return result

    def shortcuts_by_category(self) -> dict[str, list[dict[str, str]]]:
        """Return shortcuts grouped by category."""
        all_items = self.all_shortcuts()
        grouped: dict[str, list[dict[str, str]]] = {}
        for item in all_items:
            cat = item["category"]
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(item)
        return grouped

    def export_config(self) -> dict[str, str]:
        """Export current shortcut configuration."""
        config: dict[str, str] = {}
        for action_id in DEFAULT_SHORTCUTS:
            config[action_id] = self.get_key(action_id)
        return config

    def import_config(self, data: dict[str, str]) -> int:
        """Import shortcut configuration. Returns count of imported bindings."""
        if not isinstance(data, dict):
            return 0
        count = 0
        for action_id, key in data.items():
            if action_id in DEFAULT_SHORTCUTS and isinstance(key, str):
                self._overrides[action_id] = key.strip()
                count += 1
        self._save()
        return count

    def find_conflict(self, key: str, exclude_action: str = "") -> str | None:
        """Check if a key binding conflicts with another action.

        Returns the conflicting action_id, or None if no conflict.
        """
        key_lower = key.lower()
        for action_id in DEFAULT_SHORTCUTS:
            if action_id == exclude_action:
                continue
            if self.get_key(action_id).lower() == key_lower:
                return action_id
        return None

    def _save(self) -> None:
        save_json_state(self.path, dict(self._overrides))
