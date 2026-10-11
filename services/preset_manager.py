from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.constants import PRESET_STORE
from app.presets import DEFAULT_PRESETS, load_presets, save_presets, validate_presets


class PresetManager:
    def __init__(self, path: Path = PRESET_STORE) -> None:
        self.path = path
        loaded = load_presets(path)
        self.presets = {name: dict(value) for name, value in DEFAULT_PRESETS.items()}
        for name, value in loaded.items():
            if name in DEFAULT_PRESETS:
                if value == DEFAULT_PRESETS[name]:
                    continue
                name = self._unique_name(name + " (Custom)", set(self.presets) | set(loaded))
            self.presets[name] = value

    def names(self) -> list[str]:
        return sorted(self.presets.keys())

    def get(self, name: str) -> dict[str, Any] | None:
        data = self.presets.get(name)
        return dict(data) if isinstance(data, dict) else None

    def builtin_names(self) -> list[str]:
        return sorted(DEFAULT_PRESETS)

    def custom_names(self) -> list[str]:
        return sorted(self._custom_presets())

    def is_builtin(self, name: str) -> bool:
        return name in DEFAULT_PRESETS

    def _commit(self, updated: dict[str, dict[str, Any]]) -> None:
        custom = {name: value for name, value in updated.items() if name not in DEFAULT_PRESETS or value != DEFAULT_PRESETS[name]}
        save_presets(self.path, custom)
        self.presets = updated

    def save(self, name: str, settings_map: dict[str, Any]) -> None:
        if name.strip() in DEFAULT_PRESETS:
            raise ValueError("Вбудований пресет захищено. Використай «Зберегти як» з новою назвою.")
        validated = validate_presets({name: settings_map})
        self._commit({**self.presets, **validated})

    def delete(self, name: str) -> bool:
        if name not in self.presets:
            return False
        updated = dict(self.presets)
        if name in DEFAULT_PRESETS:
            if self.presets[name] == DEFAULT_PRESETS[name]:
                return False
            updated[name] = dict(DEFAULT_PRESETS[name])
        else:
            del updated[name]
        self._commit(updated)
        return True

    def read_import(self, path: Path) -> dict[str, dict[str, Any]]:
        with path.open("r", encoding="utf-8") as fh:
            return validate_presets(json.load(fh))

    def import_json(self, path: Path, *, conflict_policy: str = "error") -> list[str]:
        imported = self.read_import(path)
        conflicts = sorted(set(imported) & set(self.presets))
        if conflicts and conflict_policy == "error":
            raise ValueError("Пресети з такими назвами вже існують: " + ", ".join(conflicts))
        if conflict_policy not in {"error", "replace", "keep"}:
            raise ValueError("Невідома політика конфліктів.")
        for name in list(imported):
            if name in DEFAULT_PRESETS and conflict_policy == "replace":
                renamed = self._unique_name(name + " (Custom)", set(self.presets) | set(imported))
                imported[renamed] = imported.pop(name)
        if conflict_policy == "keep":
            imported = {name: value for name, value in imported.items() if name not in self.presets}
        self._commit({**self.presets, **imported})
        return list(imported)

    def export_json(self, path: Path) -> None:
        save_presets(path, self._custom_presets())

    def _custom_presets(self) -> dict[str, dict[str, Any]]:
        return {name: value for name, value in self.presets.items() if name not in DEFAULT_PRESETS or value != DEFAULT_PRESETS[name]}

    @staticmethod
    def _unique_name(name: str, existing: set[str]) -> str:
        candidate, index = name, 2
        while candidate in existing:
            candidate = f"{name} ({index})"
            index += 1
        return candidate
