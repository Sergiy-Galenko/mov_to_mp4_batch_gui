"""Machine-local, bounded measurements used for memory admission and startup ETA."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import statistics
import threading
import time
from pathlib import Path

import psutil

from app.paths import APP_DATA_DIR
from utils.sqlite_store import database


class WorkloadHistory:
    def __init__(self, path: Path = APP_DATA_DIR / "workloads.sqlite3"):
        self.path = path
        self.machine = hashlib.sha256(f"{platform.node()}:{platform.system()}:{platform.machine()}:{os.cpu_count()}".encode()).hexdigest()
        with database(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS samples (id INTEGER PRIMARY KEY, profile TEXT NOT NULL, "
                "elapsed REAL NOT NULL, duration REAL NOT NULL, peak_rss INTEGER NOT NULL, created REAL NOT NULL)"
            )
            db.execute("CREATE INDEX IF NOT EXISTS sample_profile ON samples(profile)")

    def profile(self, settings, info, encoder: str, *, tool: str = "", threads: int | None = None) -> str:
        width = max((info.width or 1920) if info else 1920, settings.resize_w or 0)
        height = max((info.height or 1080) if info else 1080, settings.resize_h or 0)
        bucket = (
            "sd"
            if width * height <= 1280 * 720
            else "hd"
            if width * height <= 1920 * 1080
            else "4k"
            if width * height <= 3840 * 2160
            else "8k+"
        )
        payload = [
            self.machine,
            tool,
            settings.operation,
            encoder,
            bucket,
            info.vcodec if info else None,
            info.pix_fmt if info else None,
            round(info.fps, 2) if info and info.fps else None,
            info.dynamic_range if info else None,
            settings.resize_w,
            settings.resize_h,
            settings.preset,
            settings.crf,
            settings.normalize_audio,
            bool(settings.watermark_path),
            settings.subtitle_mode,
            bool(settings.target_size_mb),
            settings.portrait,
            settings.hdr_tone_mapping,
            threads,
            settings.subtitle_model if settings.operation == "auto_subtitle" else None,
            settings.subtitle_engine if settings.operation == "auto_subtitle" else None,
            settings.subtitle_device if settings.operation == "auto_subtitle" else None,
        ]
        return hashlib.sha256(json.dumps(payload).encode()).hexdigest()

    def record(self, profile: str, elapsed: float, duration: float, peak_rss: int):
        if not all(math.isfinite(value) for value in (elapsed, duration)) or elapsed <= 0 or duration <= 0 or peak_rss <= 0:
            return
        with database(self.path) as db:
            db.execute(
                "INSERT INTO samples(profile,elapsed,duration,peak_rss,created) VALUES (?,?,?,?,?)",
                (profile, elapsed, duration, peak_rss, time.time()),
            )
            db.execute(
                "DELETE FROM samples WHERE profile=? AND id NOT IN (SELECT id FROM samples WHERE profile=? ORDER BY id DESC LIMIT 30)",
                (profile, profile),
            )
            db.execute("DELETE FROM samples WHERE id NOT IN (SELECT id FROM samples ORDER BY id DESC LIMIT 3000)")

    def estimate(self, profile: str, duration: float | None = None) -> dict:
        with database(self.path) as db:
            rows = db.execute(
                "SELECT elapsed,duration,peak_rss FROM samples WHERE profile=? ORDER BY id DESC LIMIT 30", (profile,)
            ).fetchall()
        if len(rows) < 3:
            return {}
        memory = sorted(row["peak_rss"] for row in rows)
        # Conservative upper quantile plus headroom; timing uses a robust median.
        peak = memory[min(len(memory) - 1, math.ceil(len(memory) * 0.9) - 1)]
        ratio = statistics.median(row["elapsed"] / row["duration"] for row in rows)
        return {"samples": len(rows), "memory_bytes": int(peak * 1.25), "seconds": ratio * duration if duration and duration > 0 else None}


class ProcessMemorySampler:
    def __init__(self, pid: int):
        self.peak_rss = 0
        self._stop = threading.Event()
        self._process = psutil.Process(pid)
        self._thread = threading.Thread(target=self._collect, name="process-memory-sampler", daemon=True)
        self._thread.start()

    def _collect(self):
        while not self._stop.is_set():
            try:
                self.peak_rss = max(self.peak_rss, self._process.memory_info().rss)
            except (psutil.Error, OSError):
                return
            self._stop.wait(0.1)

    def close(self):
        self._stop.set()
        self._thread.join(timeout=1)
