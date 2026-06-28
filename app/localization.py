from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


SUPPORTED_LANGUAGES = {"uk", "en", "pl", "de"}
DEFAULT_LANGUAGE = "uk"


def normalize_language(value: str) -> str:
    language = str(value or DEFAULT_LANGUAGE).strip().lower()
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def translations_dir() -> Path:
    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    preferred = ui_dir / "i18n"
    if preferred.exists():
        return preferred
    return ui_dir / "qml" / "translations"


@lru_cache(maxsize=8)
def load_translations(language: str) -> Dict[str, str]:
    normalized = normalize_language(language)
    path = translations_dir() / f"{normalized}.json"
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    normalized = normalize_language(language)
    text = load_translations(normalized).get(key) or load_translations("en").get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
