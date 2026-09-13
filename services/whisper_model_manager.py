"""Whisper model management service for subtitle transcription.

Handles:
  - Model catalog inspection (tiny, base, small, medium, large-v3, large-v3-turbo).
  - Cache size discovery on local disk.
  - Asynchronous / thread-safe model download with progress reporting.
  - Model deletion to reclaim disk space.
  - Compute device detection (CUDA, Apple Silicon MPS, CPU).
"""

from __future__ import annotations

import platform
import shutil
import sys
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

WHISPER_MODELS: list[dict[str, str | int]] = [
    {"name": "tiny", "display_name": "Tiny (Швидка, базова точність)", "size_mb": 75, "speed": "~32x", "vram_mb": 1000},
    {"name": "base", "display_name": "Base (Збалансована для щоденного вжитку)", "size_mb": 145, "speed": "~16x", "vram_mb": 1200},
    {"name": "small", "display_name": "Small (Висока точність)", "size_mb": 480, "speed": "~6x", "vram_mb": 2000},
    {"name": "medium", "display_name": "Medium (Професійна якість)", "size_mb": 1500, "speed": "~2x", "vram_mb": 5000},
    {"name": "large-v3", "display_name": "Large-v3 (Максимальна якість)", "size_mb": 3100, "speed": "~1x", "vram_mb": 10000},
    {"name": "large-v3-turbo", "display_name": "Large-v3-Turbo (Швидкий Large)", "size_mb": 1600, "speed": "~4x", "vram_mb": 6000},
]


@dataclass
class ModelInfo:
    name: str
    display_name: str
    size_mb: int
    speed: str
    vram_mb: int
    downloaded: bool
    disk_bytes: int
    path: str


class WhisperModelManager:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or (Path.home() / ".cache")
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="whisper_dl")

    def get_cache_paths(self, model_name: str) -> list[Path]:
        """Return potential disk locations for a given Whisper model."""
        candidates: list[Path] = [
            # faster-whisper / huggingface cache
            self.cache_dir / "huggingface" / "hub" / f"models--Systran--faster-whisper-{model_name}",
            self.cache_dir / "huggingface" / "hub" / f"models--openai--whisper-{model_name}",
            # openai-whisper cache
            self.cache_dir / "whisper" / f"{model_name}.pt",
        ]
        return candidates

    def list_models(self) -> list[dict[str, str | int | bool]]:
        """Return list of all registered models with their download and disk status."""
        results: list[dict[str, str | int | bool]] = []
        for item in WHISPER_MODELS:
            name = str(item["name"])
            paths = self.get_cache_paths(name)
            downloaded = False
            total_bytes = 0
            found_path = ""

            for p in paths:
                if p.exists():
                    downloaded = True
                    found_path = str(p)
                    if p.is_dir():
                        total_bytes += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    else:
                        total_bytes += p.stat().st_size

            results.append({
                "name": name,
                "display_name": str(item["display_name"]),
                "size_mb": int(item["size_mb"]),
                "speed": str(item["speed"]),
                "vram_mb": int(item["vram_mb"]),
                "downloaded": downloaded,
                "disk_bytes": total_bytes,
                "disk_size_mb": round(total_bytes / (1024 * 1024), 1) if total_bytes else 0,
                "path": found_path,
            })
        return results

    def is_model_downloaded(self, model_name: str) -> bool:
        return any(p.exists() for p in self.get_cache_paths(model_name))

    def delete_model(self, model_name: str) -> bool:
        """Remove a cached model to free disk space."""
        deleted = False
        for p in self.get_cache_paths(model_name):
            if p.exists():
                try:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    deleted = True
                except OSError:
                    pass
        return deleted

    def download_model(
        self,
        model_name: str,
        progress_cb: Callable[[float, str], None] | None = None,
    ) -> Future[bool]:
        """Download model asynchronously in background thread."""
        return self._executor.submit(self._run_download, model_name, progress_cb)

    def _run_download(
        self,
        model_name: str,
        progress_cb: Callable[[float, str], None] | None = None,
    ) -> bool:
        if progress_cb:
            progress_cb(0.05, f"Ініціалізація завантаження {model_name}...")

        # 1. Try faster-whisper download helper if available
        try:
            import faster_whisper  # type: ignore
            if progress_cb:
                progress_cb(0.3, f"Завантаження моделі {model_name} (faster-whisper)...")
            faster_whisper.download_model(model_name)
            if progress_cb:
                progress_cb(1.0, f"Модель {model_name} успішно завантажена")
            return True
        except Exception:
            pass

        # 2. Try openai-whisper download helper if available
        try:
            import whisper  # type: ignore
            if progress_cb:
                progress_cb(0.3, f"Завантаження моделі {model_name} (whisper)...")
            whisper.load_model(model_name)
            if progress_cb:
                progress_cb(1.0, f"Модель {model_name} успішно завантажена")
            return True
        except Exception:
            pass

        # 3. Fallback direct download via urllib for openai whisper weights
        whisper_urls = {
            "tiny": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26fde3f8dd461517c45941c167d5e45952f48a/tiny.pt",
            "base": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f83f07d4744d85a2d6ed9d4/base.pt",
            "small": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968e7bd85e888d298718213f0775965bc08e4f3acf4/small.pt",
            "medium": "https://openaipublic.azureedge.net/main/whisper/models/34508463f703c9f5842e9a978324e1306043d077643e8a7183c5b61a382e2f63/medium.pt",
        }
        url = whisper_urls.get(model_name)
        if url:
            try:
                import urllib.request
                target_dir = self.cache_dir / "whisper"
                target_dir.mkdir(parents=True, exist_ok=True)
                dest = target_dir / f"{model_name}.pt"
                temp_dest = dest.with_suffix(".tmp")

                def hook(blocks, block_size, total_size):
                    if total_size > 0 and progress_cb:
                        pct = min(0.99, (blocks * block_size) / total_size)
                        progress_cb(pct, f"Завантаження {model_name}: {int(pct * 100)}%")

                urllib.request.urlretrieve(url, temp_dest, reporthook=hook)
                temp_dest.replace(dest)
                if progress_cb:
                    progress_cb(1.0, f"Модель {model_name} завантажена")
                return True
            except Exception as exc:
                if progress_cb:
                    progress_cb(0.0, f"Помилка завантаження: {exc}")
                return False

        if progress_cb:
            progress_cb(0.0, "Для завантаження потрібен пакет faster-whisper або openai-whisper")
        return False

    @staticmethod
    def detect_available_devices() -> list[str]:
        """Detect supported inference compute accelerators."""
        devices = ["auto", "cpu"]
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                devices.append("cuda")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                devices.append("mps")
        except Exception:
            # Check for Apple Silicon platform
            if sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}:
                devices.append("mps")
        return devices
