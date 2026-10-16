"""Support report built from allowlisted fields, never raw paths, settings or logs."""

from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path

from app.constants import APP_VERSION
from services.cache_manager import CacheManager
from services.task_journal import TaskJournal
from utils.state import save_json_file


def error_category(message: str) -> str:
    text = str(message).lower()
    categories = {
        "disk_full": ("no space", "disk full", "недостатньо місця"),
        "permission_denied": ("permission", "access denied", "доступ"),
        "encoder_failure": ("encoder", "driver", "енкодер", "кодек"),
        "missing_file": ("not found", "не знайдено", "missing"),
        "cancelled": ("cancel", "скасовано", "interrupted"),
        "validation": ("invalid", "несуміс", "не підтрим"),
    }
    return next((category for category, words in categories.items() if any(word in text for word in words)), "other")


def summarize_command(command: list[str]) -> dict:
    def option(flag):
        return command[command.index(flag) + 1] if flag in command and command.index(flag) + 1 < len(command) else None

    # Codec identifiers must be identifiers; filter values and file arguments are never exported.
    result = {
        "video_codec": option("-c:v") or option("-c"),
        "audio_codec": option("-c:a") or option("-c"),
        "hardware_decoder": option("-hwaccel"),
        "filter_graph": "-filter_complex" in command,
        "video_filter": "-vf" in command,
        "audio_filter": "-filter:a" in command or "-af" in command,
        "input_count": command.count("-i"),
    }
    for key in ("video_codec", "audio_codec", "hardware_decoder"):
        value = result[key]
        result[key] = value if value is None or re.fullmatch(r"[a-zA-Z0-9_-]+", value) else "redacted"
    return result


def build_report(ffmpeg, *, logs=(), plans=(), context=None, cache=None, journal=None):
    import psutil
    import PySide6

    from services.native_acceleration import NATIVE_AVAILABLE

    def version(executable, name):
        if not executable:
            return "unavailable"
        try:
            if context:
                result = context.run([executable, "-version"], timeout=5)
            else:
                result = subprocess.run(
                    [executable, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            match = re.match(rf"{name} version ([a-zA-Z0-9_.+-]+)", result.stdout)
            return match[1] if result.returncode == 0 and match else "unknown"
        except (OSError, TimeoutError, subprocess.SubprocessError):
            return "unavailable"

    safe_plans = []
    for plan in list(plans)[-20:]:
        if not isinstance(plan, dict):
            continue
        safe = {key: bool(plan.get(key)) for key in ("filter_graph", "video_filter", "audio_filter")}
        safe["input_count"] = max(0, min(1000, int(plan.get("input_count") or 0)))
        for key in ("video_codec", "audio_codec", "hardware_decoder"):
            value = plan.get(key)
            safe[key] = value if isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_-]+", value) else None
        safe_plans.append(safe)
    memory = psutil.virtual_memory()
    events = (journal or TaskJournal()).recent_events(50)
    errors = [
        {"status": row["status"], "category": error_category(row["message"]), "time": row["time"]}
        for row in events
        if row["status"] == "failed"
    ]
    errors += [{"status": "log", "category": error_category(line)} for line in list(logs)[-100:] if str(line).startswith(("ERROR", "WARN"))]
    return {
        "schema_version": 1,
        "privacy": "No source paths, filenames, raw commands, log messages or secrets are exported",
        "application": APP_VERSION,
        "python": platform.python_version(),
        "qt": PySide6.__version__,
        "system": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "logical_cpus": psutil.cpu_count(),
            "ram_bytes": memory.total,
        },
        "native_available": NATIVE_AVAILABLE,
        "ffmpeg_version": version(ffmpeg.ffmpeg_path, "ffmpeg"),
        "ffprobe_version": version(ffmpeg.ffprobe_path, "ffprobe"),
        "verified_encoders": sorted(value for value in ffmpeg.encoder_caps if re.fullmatch(r"[a-zA-Z0-9_-]+", value)),
        "cache": (cache or CacheManager()).statistics(),
        "recent_processing_plans": safe_plans,
        "recent_errors": errors[-50:],
    }


def export_report(target: Path, ffmpeg, **kwargs):
    report = build_report(ffmpeg, **kwargs)
    save_json_file(target, report)
    return report
