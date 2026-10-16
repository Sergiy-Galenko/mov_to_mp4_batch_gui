"""Versioned, quota-controlled artifact cache with atomic cross-process producers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from app.install_lock import install_lock
from app.paths import APP_DATA_DIR
from utils.artifact_lock import artifact_lock
from utils.sqlite_store import database

DEFAULT_CACHE_ROOT = APP_DATA_DIR / "cache"


def source_fingerprint(source: Path) -> dict:
    source = source.expanduser().resolve()
    stat = source.stat()
    return {"path": str(source), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns, "inode": stat.st_ino}


def tool_fingerprint(executable: str | None) -> str:
    if not executable:
        return "unavailable"
    try:
        return json.dumps(source_fingerprint(Path(executable)), sort_keys=True)
    except OSError:
        return str(executable)


class CacheManager:
    def __init__(self, root: Path = DEFAULT_CACHE_ROOT, *, max_bytes: int = 2 * 1024**3, max_age_days: float = 30):
        self.root = Path(root).resolve()
        self.max_bytes = max(0, int(max_bytes))
        self.max_age_seconds = max(0, max_age_days * 86400)
        self.index = self.root / "cache.sqlite3"
        with install_lock(self.root / ".index.lock", timeout=15), database(self.index) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS entries (key TEXT PRIMARY KEY, namespace TEXT NOT NULL, path TEXT NOT NULL, "
                "size INTEGER NOT NULL, accessed REAL NOT NULL, identity TEXT)"
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(entries)")}
            if "identity" not in columns:
                db.execute("ALTER TABLE entries ADD COLUMN identity TEXT")
        self.cleanup()

    def key(self, source: Path, namespace: str, parameters: dict | None = None) -> str:
        payload = {"version": 1, "source": source_fingerprint(source), "namespace": namespace, "parameters": parameters or {}}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()

    def path(self, key: str, namespace: str, suffix: str, *, filename: str | None = None) -> Path:
        if not re.fullmatch(r"[a-z0-9_-]+", namespace) or not re.fullmatch(r"[a-f0-9]{64}", key):
            raise ValueError("Invalid cache namespace or key")
        if not re.fullmatch(r"\.[a-z0-9]+", suffix):
            raise ValueError("Invalid cache artifact suffix")
        name = filename or key + suffix
        if Path(name).name != name or not name.endswith(suffix):
            raise ValueError("Invalid cache artifact filename")
        return self.root / namespace / name

    def known(self, key: str) -> bool:
        with database(self.index) as db:
            return db.execute("SELECT 1 FROM entries WHERE key=?", (key,)).fetchone() is not None

    def _valid(self, row, target: Path) -> bool:
        try:
            target.resolve().relative_to(self.root)
            if not target.is_file():
                return False
            identity = source_fingerprint(target)
            return identity["size"] > 0 and identity["size"] == row["size"] and identity == json.loads(row["identity"] or "null")
        except (OSError, ValueError, TypeError):
            return False

    def get(self, key: str) -> Path | None:
        with database(self.index) as db:
            row = db.execute("SELECT * FROM entries WHERE key=?", (key,)).fetchone()
            if row:
                target = self.root / row["path"]
                if self._valid(row, target):
                    db.execute("UPDATE entries SET accessed=? WHERE key=?", (time.time(), key))
                    return target
        return None

    def register(self, key: str, namespace: str, target: Path) -> None:
        relative = target.resolve().relative_to(self.root)
        size = target.stat().st_size
        if size <= 0:
            raise ValueError("Empty cache artifact")
        with database(self.index) as db:
            db.execute(
                "INSERT OR REPLACE INTO entries(key,namespace,path,size,accessed,identity) VALUES (?,?,?,?,?,?)",
                (key, namespace, str(relative), size, time.time(), json.dumps(source_fingerprint(target), sort_keys=True)),
            )

    @contextmanager
    def lease(self, target: Path):
        """Readers can retain an artifact while cleanup runs in another process."""
        key = hashlib.sha256(str(target.resolve()).encode()).hexdigest()
        with artifact_lock(self.root / ".leases" / (key + ".lock"), shared=True, timeout=600):
            yield target

    def produce(
        self, source: Path, namespace: str, parameters: dict, suffix: str, producer: Callable[[Path], bool], *, filename: str | None = None
    ) -> Path | None:
        fingerprint = source_fingerprint(source)
        key = self.key(source, namespace, parameters)
        target = self.path(key, namespace, suffix, filename=filename)
        with install_lock(self.root / ".locks" / (key + ".lock"), timeout=600), self.lease(target):
            cached = self.get(key)
            if cached:
                return cached
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{key}.{uuid.uuid4().hex}.partial{suffix}")
            try:
                if not producer(temporary) or not temporary.is_file() or not 0 < temporary.stat().st_size <= self.max_bytes:
                    return None
                if source_fingerprint(source) != fingerprint:
                    return None
                with temporary.open("rb") as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
                self.register(key, namespace, target)
            finally:
                temporary.unlink(missing_ok=True)
            self.cleanup(protect={target})
            return target

    def cleanup(self, *, protect: set[Path] | None = None, namespace: str | None = None, clear: bool = False) -> int:
        protected = {p.resolve() for p in protect or set()}
        removed = 0
        now = time.time()
        with database(self.index) as db:
            rows = db.execute("SELECT * FROM entries ORDER BY accessed ASC").fetchall()
            total = sum(row["size"] for row in rows)
            for row in rows:
                if namespace is not None and row["namespace"] != namespace:
                    continue
                target = self.root / row["path"]
                if target.resolve() in protected:
                    continue
                expired = now - row["accessed"] > self.max_age_seconds
                if not clear and not expired and total <= self.max_bytes and self._valid(row, target):
                    continue
                try:
                    target.resolve().relative_to(self.root)
                    with artifact_lock(
                        self.root / ".leases" / (hashlib.sha256(str(target.resolve()).encode()).hexdigest() + ".lock"),
                        shared=False,
                        timeout=0,
                    ):
                        target.unlink(missing_ok=True)
                        db.execute("DELETE FROM entries WHERE key=?", (row["key"],))
                        total -= row["size"]
                        removed += 1
                except (OSError, ValueError, TimeoutError):
                    continue
        # Only our incomplete producer artifacts are eligible, never unrelated files.
        for partial in self.root.glob("*/.*.partial.*"):
            try:
                if now - partial.stat().st_mtime > 3600:
                    partial.unlink()
            except OSError:
                pass
        return removed

    def statistics(self) -> dict:
        with database(self.index) as db:
            row = db.execute("SELECT COUNT(*) count, COALESCE(SUM(size),0) bytes FROM entries").fetchone()
        return {"entries": row["count"], "bytes": row["bytes"], "limit_bytes": self.max_bytes}


def media_info_matches_source(info, source: Path) -> bool:
    if info is None:
        return False
    identity = getattr(info, "source_identity", None)
    # Hand-supplied metadata has no cached filesystem identity.
    if identity is None:
        return True
    try:
        return identity == source_fingerprint(source)
    except OSError:
        return False
