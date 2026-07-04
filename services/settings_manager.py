from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.constants import DEFAULT_OUTPUT_DIR, RECENT_FOLDERS_LIMIT, STATE_STORE
from app.localization import normalize_language
from utils.state import load_json_state, save_json_state


class SettingsManager:
    def __init__(self, path: Path = STATE_STORE) -> None:
        self.path = path
        self.state: Dict[str, Any] = load_json_state(path)

    def reload(self) -> Dict[str, Any]:
        self.state = load_json_state(self.path)
        return dict(self.state)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def recent_folders(self) -> List[str]:
        folders = self.state.get("recent_folders", [])
        if not isinstance(folders, list):
            return []
        return [folder for folder in folders if isinstance(folder, str) and folder][:RECENT_FOLDERS_LIMIT]

    def output_dir(self) -> str:
        return str(self.state.get("output_dir") or "")

    def output_dir_configured(self) -> bool:
        return bool(self.state.get("output_dir_configured")) and bool(str(self.state.get("output_dir") or "").strip())

    def ffmpeg_path(self, fallback: Optional[str]) -> str:
        return str(self.state.get("ffmpeg_path") or fallback or "")

    def watch_folder(self) -> str:
        return str(self.state.get("watch_folder") or "")

    def ui_language(self) -> str:
        return normalize_language(str(self.state.get("ui_language") or self.state.get("language") or "uk"))

    def last_settings(self) -> Dict[str, Any]:
        value = self.state.get("last_settings")
        return dict(value) if isinstance(value, dict) else {}

    def youtube_history(self) -> List[str]:
        value = self.state.get("youtube_history", [])
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item or "").strip()][:20]

    def youtube_cookies_path(self) -> str:
        return str(self.state.get("youtube_cookies_path") or "")

    def tray_enabled(self) -> bool:
        return bool(self.state.get("tray_enabled", False))

    def push_notifications_enabled(self) -> bool:
        return bool(self.state.get("push_notifications_enabled", True))

    def save(
        self,
        *,
        recent_folders: List[str],
        watch_folder: str,
        output_dir: str,
        output_dir_configured: bool,
        ffmpeg_path: str,
        ui_language: str,
        last_settings: Dict[str, Any],
        queue_items: List[Dict[str, Any]],
        pending_recovery: bool,
        onboarding_completed: bool = True,
        youtube_history: Optional[List[str]] = None,
        youtube_cookies_path: str = "",
        tray_enabled: bool = False,
        push_notifications_enabled: bool = True,
    ) -> None:
        self.state = {
            "recent_folders": recent_folders[:RECENT_FOLDERS_LIMIT],
            "watch_folder": watch_folder,
            "output_dir": output_dir,
            "output_dir_configured": bool(output_dir_configured) and bool(str(output_dir or "").strip()),
            "ffmpeg_path": ffmpeg_path,
            "ui_language": normalize_language(ui_language),
            "language": normalize_language(ui_language),
            "last_settings": dict(last_settings),
            "queue_items": list(queue_items),
            "pending_recovery": bool(pending_recovery),
            "onboarding_completed": bool(onboarding_completed),
            "youtube_history": list(youtube_history or [])[:20],
            "youtube_cookies_path": str(youtube_cookies_path or ""),
            "tray_enabled": bool(tray_enabled),
            "push_notifications_enabled": bool(push_notifications_enabled),
        }
        save_json_state(self.path, self.state)

    def remember_folder(self, folders: List[str], folder: str) -> List[str]:
        value = str(folder or "").strip()
        if not value:
            return folders[:RECENT_FOLDERS_LIMIT]
        path = str(Path(value).expanduser())
        result = [item for item in folders if item != path]
        result.insert(0, path)
        return result[:RECENT_FOLDERS_LIMIT]
