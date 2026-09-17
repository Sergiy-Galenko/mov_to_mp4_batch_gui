"""Whisper downloads with byte progress, integrity checks and atomic publication.

The manager and transcription service use the same engine-specific caches.
Optional inference packages are not needed to download OpenAI checkpoints.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import urllib.request
from collections.abc import Callable
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from pathlib import Path

from services.whisper_runtime import available_devices, cache_root

# SHA-256 digests published in openai/whisper's checkpoint URLs.
_CHECKSUMS = {
    "tiny": "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9",
    "base": "ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e",
    "small": "9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794",
    "medium": "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1",
    "large-v3": "e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb",
    "large-v3-turbo": "aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a",
}
WHISPER_MODELS = [
    {"name": name, "size_mb": size, "vram_mb": memory}
    for name, size, memory in [
        ("tiny", 75, 1000),
        ("base", 145, 1000),
        ("small", 480, 2000),
        ("medium", 1500, 5000),
        ("large-v3", 3100, 10000),
        ("large-v3-turbo", 1600, 6000),
    ]
]
ProgressCallback = Callable[[float, str], None]


def normalize_model(name: str) -> str:
    name = {"large": "large-v3", "turbo": "large-v3-turbo"}.get(name, name)
    if name not in _CHECKSUMS:
        raise ValueError(f"Unknown Whisper model: {name}")
    return name


def faster_repo(name: str) -> str:
    name = normalize_model(name)
    if name == "large-v3-turbo":
        return "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
    return f"Systran/faster-whisper-{name}"


class WhisperModelManager:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else cache_root()
        self.hub_dir = (
            (self.cache_dir / "huggingface" / "hub")
            if cache_dir is not None
            else Path(
                os.environ.get("HF_HUB_CACHE")
                or os.environ.get("HUGGINGFACE_HUB_CACHE")
                or str(Path(os.environ.get("HF_HOME", str(self.cache_dir / "huggingface"))) / "hub")
            ).expanduser()
        )
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper-download")
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._active = ""
        self._closed = False
        self._states: dict[tuple[str, str], dict] = {}

    @staticmethod
    def _validate_engine(engine: str) -> None:
        if engine not in {"whisper", "faster-whisper"}:
            raise ValueError(f"Unsupported Whisper engine: {engine}")

    def get_cache_paths(self, model_name: str, engine: str = "whisper") -> list[Path]:
        name = normalize_model(model_name)
        self._validate_engine(engine)
        if engine == "whisper":
            return [self.cache_dir / "whisper" / f"{name}.pt"]
        return [
            self.cache_dir / "media-converter" / "faster-whisper" / name,
            self.hub_dir / ("models--" + faster_repo(name).replace("/", "--")),
        ]

    @staticmethod
    def _complete_faster_model(path: Path) -> bool:
        return all(
            (path / name).is_file() and (path / name).stat().st_size > 0 for name in ("config.json", "model.bin", "tokenizer.json")
        ) and any((path / name).is_file() and (path / name).stat().st_size > 0 for name in ("vocabulary.json", "vocabulary.txt"))

    def model_path(self, model_name: str, engine: str = "whisper") -> Path | None:
        for path in self.get_cache_paths(model_name, engine):
            if engine == "whisper":
                if path.is_file() and path.stat().st_size > 0:
                    return path
            elif self._complete_faster_model(path):
                return path
            else:
                for snapshot in sorted((path / "snapshots").glob("*")):
                    if self._complete_faster_model(snapshot):
                        return snapshot
        return None

    def list_models(self, engine: str = "whisper") -> list[dict]:
        self._validate_engine(engine)
        results = []
        with self._lock:
            for item in WHISPER_MODELS:
                name = item["name"]
                paths = self.get_cache_paths(name, engine)
                total = 0
                for path in paths:
                    files = path.rglob("*") if path.is_dir() else [path]
                    for file in files:
                        # HF snapshots are symlinks to blobs; count the actual files once.
                        try:
                            if not file.is_symlink() and file.is_file():
                                total += file.stat().st_size
                        except OSError:
                            continue
                path = self.model_path(name, engine)
                results.append(
                    {
                        **item,
                        "downloaded": path is not None,
                        "disk_bytes": total,
                        "disk_size_mb": round(total / 1024**2, 1),
                        "path": str(path or ""),
                        "state": "ready" if path else "missing",
                        "progress": 0.0,
                        "error": "",
                        **self._states.get((name, engine), {}),
                    }
                )
        return results

    def is_model_downloaded(self, model_name: str, engine: str = "whisper") -> bool:
        return self.model_path(model_name, engine) is not None

    def delete_model(self, model_name: str, engine: str = "whisper") -> bool:
        name = normalize_model(model_name)
        with self._lock:
            if self._active:
                raise RuntimeError("Wait for the current download to finish or cancel it first.")
            deleted = False
            for path in self.get_cache_paths(name, engine):
                if path.is_symlink():
                    path.unlink()
                    deleted = True
                elif path.is_dir():
                    shutil.rmtree(path)
                    deleted = True
                elif path.exists():
                    path.unlink()
                    deleted = True
            self._states.pop((name, engine), None)
            return deleted

    def download_model(self, model_name: str, progress_cb: ProgressCallback | None = None, engine: str = "whisper") -> Future[bool]:
        name = normalize_model(model_name)
        self._validate_engine(engine)
        with self._lock:
            if self._closed or self._active:
                raise RuntimeError("The model manager is closed or another download is running.")
            self._active = name
            self._cancel.clear()
            self._states[(name, engine)] = {"state": "downloading", "progress": 0.0, "error": ""}
            return self._executor.submit(self._run_download, name, progress_cb, engine)

    @property
    def closed(self) -> bool:
        return self._closed

    def cancel_download(self) -> None:
        self._cancel.set()

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            self._cancel.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise CancelledError()

    def _transfer(self, url: str, target: Path, checksum: str | None, progress: ProgressCallback) -> None:
        self._check_cancelled()
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        digest = hashlib.sha256()
        received = 0
        try:
            with urllib.request.urlopen(url, timeout=15) as response, partial.open("wb") as output:
                length = int(response.headers.get("Content-Length", 0))
                while True:
                    self._check_cancelled()
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    progress(min(0.99, received / length) if length else -1.0, target.name)
            self._check_cancelled()
            if not received or (length and received != length):
                raise RuntimeError("Incomplete model download. Please retry.")
            if checksum and digest.hexdigest() != checksum:
                raise RuntimeError("Model checksum mismatch. Please retry.")
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)

    def _download_faster(self, name: str, progress: ProgressCallback) -> None:
        repo = faster_repo(name)
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}?blobs=true", timeout=15) as response:
            manifest = json.load(response)
        revision = manifest["sha"]
        if not isinstance(revision, str) or not revision.isalnum():
            raise RuntimeError("Invalid model revision")
        files = [
            entry
            for entry in manifest["siblings"]
            if entry["rfilename"]
            in {
                "config.json",
                "preprocessor_config.json",
                "model.bin",
                "tokenizer.json",
                "vocabulary.json",
                "vocabulary.txt",
            }
        ]
        target = self.get_cache_paths(name, "faster-whisper")[0]
        staging = target.with_name(target.name + ".partial")
        try:
            for index, entry in enumerate(files):
                self._check_cancelled()
                filename = entry["rfilename"]
                self._transfer(
                    f"https://huggingface.co/{repo}/resolve/{revision}/{filename}",
                    staging / filename,
                    entry.get("lfs", {}).get("sha256"),
                    lambda pct, msg, index=index: progress((index + pct) / len(files) if pct >= 0 else -1, msg),
                )
            if not self._complete_faster_model(staging):
                raise RuntimeError("The downloaded faster-whisper model is incomplete.")
            self._check_cancelled()
            if target.exists():
                shutil.rmtree(target)
            staging.replace(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def _run_download(self, name: str, callback: ProgressCallback | None, engine: str) -> bool:
        def progress(pct: float, message: str) -> None:
            with self._lock:
                self._states[(name, engine)].update(progress=pct)
                closed = self._closed
            if callback and not closed:
                callback(pct, message)

        success = False
        state, error = "ready", ""
        try:
            progress(0.0, name)
            if not self.is_model_downloaded(name, engine):
                if engine == "whisper":
                    checksum = _CHECKSUMS[name]
                    url = f"https://openaipublic.azureedge.net/main/whisper/models/{checksum}/{name}.pt"
                    self._transfer(url, self.get_cache_paths(name, engine)[0], checksum, progress)
                else:
                    self._download_faster(name, progress)
            self._check_cancelled()
            success = True
        except CancelledError:
            state = "cancelled"
        except Exception as exc:
            state, error = "error", str(exc)
        finally:
            with self._lock:
                self._active = ""
                self._states[(name, engine)] = {"state": state, "progress": 1.0 if success else 0.0, "error": error}
            progress(1.0 if success else 0.0, error or state)
        return success

    @staticmethod
    def detect_available_devices(engine: str = "auto") -> list[str]:
        return available_devices(engine)
