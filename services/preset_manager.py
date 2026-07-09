from __future__ import annotations

from pathlib import Path
from typing import Any

from app.constants import PRESET_STORE
from app.presets import load_presets, save_presets


class PresetManager:
    def __init__(self, path: Path = PRESET_STORE) -> None:
        self.path = path
        self.presets: dict[str, dict[str, Any]] = load_presets(path)

    def names(self) -> list[str]:
        return sorted(self.presets.keys())

    def get(self, name: str) -> dict[str, Any] | None:
        data = self.presets.get(name)
        return dict(data) if isinstance(data, dict) else None

    def save(self, name: str, settings_map: dict[str, Any]) -> None:
        self.presets[name] = dict(settings_map)
        save_presets(self.path, self.presets)

    def delete(self, name: str) -> bool:
        if name not in self.presets:
            return False
        del self.presets[name]
        save_presets(self.path, self.presets)
        return True
