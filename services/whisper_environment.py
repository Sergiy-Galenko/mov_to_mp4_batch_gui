"""Optional isolated Python runtime shared by setup, model selection and transcription."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from app.paths import APP_DATA_DIR


def manifest_path() -> Path:
    return APP_DATA_DIR / "whisper-runtime.json"


def managed_runtime() -> dict:
    if os.environ.get("MEDIA_CONVERTER_WHISPER_WORKER") == "1":
        return {}
    try:
        data = json.loads(manifest_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("report"), dict):
            return {}
        engines = data["report"].get("engines")
        if not isinstance(engines, dict) or not all(isinstance(value, dict) for value in engines.values()):
            return {}
        return data if Path(data.get("python", "")).is_file() else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_runtime(python: str, report: dict):
    path = manifest_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"python": python, "report": report}, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def worker_command(action: str, *args: str, python: str = "") -> list[str]:
    interpreter = python or managed_runtime().get("python", "")
    if interpreter or not getattr(sys, "frozen", False):
        script = Path(__file__).with_name("whisper_worker.py")
        return [interpreter or sys.executable, str(script), action, *args]
    return [sys.executable, "--whisper-setup-worker", action, *args]


def worker_environment(ffmpeg_path: str = "") -> dict:
    env = dict(os.environ)
    env["MEDIA_CONVERTER_WHISPER_WORKER"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("PYTHONHOME", None)
    if ffmpeg_path:
        env["MEDIA_CONVERTER_FFMPEG"] = ffmpeg_path
        env["PATH"] = str(Path(ffmpeg_path).parent) + os.pathsep + env.get("PATH", "")
    return env
