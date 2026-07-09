import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def load_json_state(path: Path) -> dict[str, Any]:
    data = load_json_file(path)
    return data if isinstance(data, dict) else {}


def load_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data


def save_json_state(path: Path, state: dict[str, Any]) -> None:
    save_json_file(path, state)


def save_json_file(path: Path, state: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd = -1
    tmp_path = ""
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            tmp_fd = -1
            json.dump(state, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_fd != -1:
            with contextlib.suppress(OSError):
                os.close(tmp_fd)
        if tmp_path:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_path)
        raise


def load_state(state_path: Path) -> dict[str, Any]:
    return load_json_state(state_path)


def save_state(state_path: Path, data: dict[str, Any]) -> None:
    save_json_state(state_path, data)
