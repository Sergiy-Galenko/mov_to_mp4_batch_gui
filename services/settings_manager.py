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

    def watch_auto_convert_enabled(self) -> bool:
        return bool(self.state.get("watch_auto_convert_enabled", False))

    def watch_rules_text(self) -> str:
        return str(self.state.get("watch_rules_text") or "")

    def scheduler_enabled(self) -> bool:
        return bool(self.state.get("scheduler_enabled", False))

    def scheduler_mode(self) -> str:
        value = str(self.state.get("scheduler_mode") or "time").strip().lower()
        return value if value in {"time", "idle", "time_or_idle", "time_and_idle"} else "time"

    def scheduler_time(self) -> str:
        return str(self.state.get("scheduler_time") or "23:00")

    def scheduler_cpu_limit(self) -> int:
        try:
            return max(1, min(100, int(self.state.get("scheduler_cpu_limit") or 40)))
        except (TypeError, ValueError):
            return 40

    def scheduler_gpu_limit(self) -> int:
        try:
            return max(1, min(100, int(self.state.get("scheduler_gpu_limit") or 30)))
        except (TypeError, ValueError):
            return 30

    def completion_action(self) -> str:
        value = str(self.state.get("completion_action") or "none").strip().lower()
        return value if value in {"none", "open_output", "sleep", "shutdown"} else "none"

    def webhook_enabled(self) -> bool:
        return bool(self.state.get("webhook_enabled", False))

    def webhook_url(self) -> str:
        return str(self.state.get("webhook_url") or "")

    def discord_webhook_url(self) -> str:
        return str(self.state.get("discord_webhook_url") or "")

    def telegram_bot_token(self) -> str:
        return str(self.state.get("telegram_bot_token") or "")

    def telegram_chat_id(self) -> str:
        return str(self.state.get("telegram_chat_id") or "")

    def license_payload(self) -> Dict[str, Any]:
        value = self.state.get("license_payload")
        return dict(value) if isinstance(value, dict) else {}

    def trial_started_at(self) -> float:
        try:
            return float(self.state.get("trial_started_at") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def paid_auto_update_enabled(self) -> bool:
        return bool(self.state.get("paid_auto_update_enabled", False))

    def paid_update_manifest_url(self) -> str:
        return str(self.state.get("paid_update_manifest_url") or "")

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
        watch_auto_convert_enabled: bool = False,
        watch_rules_text: str = "",
        scheduler_enabled: bool = False,
        scheduler_mode: str = "time",
        scheduler_time: str = "23:00",
        scheduler_cpu_limit: int = 40,
        scheduler_gpu_limit: int = 30,
        completion_action: str = "none",
        webhook_enabled: bool = False,
        webhook_url: str = "",
        discord_webhook_url: str = "",
        telegram_bot_token: str = "",
        telegram_chat_id: str = "",
        license_payload: Optional[Dict[str, Any]] = None,
        trial_started_at: float = 0.0,
        paid_auto_update_enabled: bool = False,
        paid_update_manifest_url: str = "",
    ) -> None:
        scheduler_mode_value = str(scheduler_mode or "time").strip().lower()
        if scheduler_mode_value not in {"time", "idle", "time_or_idle", "time_and_idle"}:
            scheduler_mode_value = "time"
        completion_action_value = str(completion_action or "none").strip().lower()
        if completion_action_value not in {"none", "open_output", "sleep", "shutdown"}:
            completion_action_value = "none"
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
            "watch_auto_convert_enabled": bool(watch_auto_convert_enabled),
            "watch_rules_text": str(watch_rules_text or ""),
            "scheduler_enabled": bool(scheduler_enabled),
            "scheduler_mode": scheduler_mode_value,
            "scheduler_time": str(scheduler_time or "23:00").strip() or "23:00",
            "scheduler_cpu_limit": max(1, min(100, int(scheduler_cpu_limit or 40))),
            "scheduler_gpu_limit": max(1, min(100, int(scheduler_gpu_limit or 30))),
            "completion_action": completion_action_value,
            "webhook_enabled": bool(webhook_enabled),
            "webhook_url": str(webhook_url or ""),
            "discord_webhook_url": str(discord_webhook_url or ""),
            "telegram_bot_token": str(telegram_bot_token or ""),
            "telegram_chat_id": str(telegram_chat_id or ""),
            "license_payload": dict(license_payload or {}),
            "trial_started_at": float(trial_started_at or 0.0),
            "paid_auto_update_enabled": bool(paid_auto_update_enabled),
            "paid_update_manifest_url": str(paid_update_manifest_url or ""),
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
