from __future__ import annotations

from pathlib import Path
from typing import Any

from app.constants import HISTORY_STORE
from utils.state import load_json_file, save_json_file


class HistoryStore:
    def __init__(self, path: Path = HISTORY_STORE, limit: int = 30) -> None:
        self.path = path
        self.limit = limit
        self.entries: list[dict[str, Any]] = self.load()

    def load(self) -> list[dict[str, Any]]:
        data = load_json_file(self.path)
        if not isinstance(data, list):
            return []
        return [entry for entry in data if isinstance(entry, dict)]

    def add(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        self.entries.insert(0, entry)
        self.entries = self.entries[: self.limit]
        save_json_file(self.path, self.entries)
        return list(self.entries)

    def clear(self) -> list[dict[str, Any]]:
        self.entries = []
        save_json_file(self.path, self.entries)
        return []
