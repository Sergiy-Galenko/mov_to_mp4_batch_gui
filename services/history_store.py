from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.constants import HISTORY_STORE
from utils.state import load_json_file, save_json_file


class HistoryStore:
    def __init__(self, path: Path = HISTORY_STORE, limit: int = 30) -> None:
        self.path = path
        self.limit = limit
        self.entries: List[Dict[str, Any]] = self.load()

    def load(self) -> List[Dict[str, Any]]:
        data = load_json_file(self.path)
        if not isinstance(data, list):
            return []
        return [entry for entry in data if isinstance(entry, dict)]

    def add(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.entries.insert(0, entry)
        self.entries = self.entries[: self.limit]
        save_json_file(self.path, self.entries)
        return list(self.entries)

    def clear(self) -> List[Dict[str, Any]]:
        self.entries = []
        save_json_file(self.path, self.entries)
        return []
