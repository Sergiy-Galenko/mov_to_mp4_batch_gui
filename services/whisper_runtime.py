"""Shared Whisper engine/device selection for the manager and transcription worker."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from services.whisper_environment import managed_runtime


def package_available(name: str) -> bool:
    runtime = managed_runtime()
    if runtime and name in {"whisper", "faster_whisper"}:
        engine = "faster-whisper" if name == "faster_whisper" else "whisper"
        return bool(runtime.get("report", {}).get("engines", {}).get(engine, {}).get("installed"))
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def cache_root() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))).expanduser()


def engine_for(device: str = "auto", engine: str = "auto") -> str:
    if device == "mps":
        if engine == "faster-whisper":
            raise ValueError("MPS requires openai-whisper; faster-whisper supports CPU/CUDA.")
        return "whisper"
    if engine in {"whisper", "openai-whisper"}:
        return "whisper"
    if engine == "faster-whisper":
        return engine
    if engine not in {"", "auto"}:
        raise ValueError(f"Unsupported Whisper engine: {engine}")
    if package_available("whisper") or not package_available("faster_whisper"):
        return "whisper"
    return "faster-whisper"


def available_devices(engine: str = "auto") -> list[str]:
    devices = ["auto", "cpu"]
    selected = engine_for(engine=engine)
    runtime = managed_runtime()
    if runtime:
        verified = runtime.get("report", {}).get("engines", {}).get(selected, {}).get("devices", [])
        return ["auto", *dict.fromkeys(["cpu", *verified])]
    if selected == "faster-whisper":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                devices.append("cuda")
        except (ImportError, RuntimeError, OSError):
            pass
    else:
        try:
            import torch

            if torch.cuda.is_available():
                devices.append("cuda")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                devices.append("mps")
        except (ImportError, RuntimeError, OSError):
            pass
    return devices


def resolve_device(requested: str, engine: str) -> str:
    devices = available_devices(engine)
    if requested == "auto":
        return next((device for device in ("cuda", "mps") if device in devices), "cpu")
    if requested not in devices:
        raise RuntimeError(
            f"Whisper device {requested.upper()} is unavailable for {engine}. Select Auto or CPU, or install a compatible runtime."
        )
    return requested
