from __future__ import annotations

import hashlib
import os
from pathlib import Path

SUPPORTED_CHECKSUMS = {"md5", "sha256"}


def checksum_file(path: Path, algorithm: str) -> str:
    normalized = str(algorithm or "").strip().lower()
    if normalized not in SUPPORTED_CHECKSUMS:
        raise ValueError(f"Unsupported checksum algorithm: {algorithm}")
    digest = hashlib.new(normalized)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum_sidecar(path: Path, algorithm: str) -> Path:
    digest = checksum_file(path, algorithm)
    sidecar = path.with_suffix(path.suffix + f".{algorithm}")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return sidecar


def secure_delete(path: Path, *, passes: int = 1) -> None:
    if not path.exists() or not path.is_file():
        return
    size = path.stat().st_size
    with path.open("r+b", buffering=0) as fh:
        for _ in range(max(1, passes)):
            fh.seek(0)
            remaining = size
            while remaining > 0:
                chunk_size = min(1024 * 1024, remaining)
                fh.write(os.urandom(chunk_size))
                remaining -= chunk_size
            fh.flush()
            os.fsync(fh.fileno())
    path.unlink()
