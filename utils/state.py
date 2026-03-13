import json
from pathlib import Path
from typing import Any, Dict


def load_json_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_json_state(path: Path, state: Dict[str, Any]) -> None:
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
    except Exception:
        return
