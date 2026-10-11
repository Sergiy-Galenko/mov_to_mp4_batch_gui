from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.constants import PRESET_STORE
from app.presets import DEFAULT_PRESETS, load_presets, save_presets, validate_presets


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
        name = name.strip()
        if not name:
            raise ValueError("Введи назву пресету.")
        self.presets[name] = dict(settings_map)
        save_presets(self.path, self._custom_presets())

    def delete(self, name: str) -> bool:
        if name not in self.presets:
            return False
        if name in DEFAULT_PRESETS:
            if self.presets[name] == DEFAULT_PRESETS[name]:
                return False
            self.presets[name] = dict(DEFAULT_PRESETS[name])
        else:
            del self.presets[name]
        save_presets(self.path, self._custom_presets())
        return True

    def import_json(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as fh:
            imported = validate_presets(json.load(fh))
        updated = {**self.presets, **imported}
        save_presets(
            self.path, {name: value for name, value in updated.items() if name not in DEFAULT_PRESETS or value != DEFAULT_PRESETS[name]}
        )
        self.presets = updated

    def export_json(self, path: Path) -> None:
        save_presets(
            path, {name: value for name, value in self.presets.items() if name not in DEFAULT_PRESETS or value != DEFAULT_PRESETS[name]}
        )

    def _custom_presets(self) -> dict[str, dict[str, Any]]:
        return {name: value for name, value in self.presets.items() if name not in DEFAULT_PRESETS or value != DEFAULT_PRESETS[name]}
