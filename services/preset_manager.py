from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from config.constants import PRESET_STORE
from core.presets import load_presets, save_presets


class PresetManager:
    def __init__(self, path: Path = PRESET_STORE) -> None:
        self.path = path
        self.presets: Dict[str, Dict[str, Any]] = load_presets(path)

    def names(self) -> List[str]:
        return sorted(self.presets.keys())

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        data = self.presets.get(name)
        return dict(data) if isinstance(data, dict) else None

    def save(self, name: str, settings_map: Dict[str, Any]) -> None:
        self.presets[name] = dict(settings_map)
        save_presets(self.path, self.presets)

    def delete(self, name: str) -> bool:
        if name not in self.presets:
            return False
        del self.presets[name]
        save_presets(self.path, self.presets)
        return True
