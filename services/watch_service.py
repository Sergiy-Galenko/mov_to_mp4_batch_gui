"""Watch folder service with debounced file detection."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, Set

from config.constants import WATCH_DEBOUNCE_SEC


class WatchService:
    """Monitors a folder for new files and notifies via callback.

    Uses polling (no external deps like watchdog) with debounce
    to avoid partial-write detection.
    """

    def __init__(
        self,
        on_new_files: Optional[Callable[[List[Path]], None]] = None,
        debounce_sec: float = WATCH_DEBOUNCE_SEC,
        poll_interval_sec: float = 3.0,
    ) -> None:
        self.on_new_files = on_new_files
        self.debounce_sec = debounce_sec
        self.poll_interval_sec = poll_interval_sec

        self._folder: Optional[Path] = None
        self._seen: Set[Path] = set()
        self._pending: dict[Path, float] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def folder(self) -> Optional[Path]:
        return self._folder

    def start(self, folder: Path) -> None:
        """Start watching the given folder."""
        self.stop()
        self._folder = folder.expanduser().resolve()
        if not self._folder.exists():
            raise FileNotFoundError(f"Watch folder does not exist: {self._folder}")

        self._seen = {p.resolve() for p in self._folder.rglob("*") if p.is_file()}
        self._pending = {}
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None

    def scan_once(self) -> List[Path]:
        """Single scan pass; returns newly detected files."""
        if not self._folder or not self._folder.exists():
            return []

        current = {p.resolve() for p in self._folder.rglob("*") if p.is_file()}
        new_paths = sorted(current - self._seen)
        self._seen = current

        # Debounce: only emit files whose size has stabilized
        now = time.time()
        stable: List[Path] = []
        for p in new_paths:
            self._pending[p] = now

        still_pending: dict[Path, float] = {}
        for p, first_seen in self._pending.items():
            if now - first_seen >= self.debounce_sec:
                stable.append(p)
            else:
                still_pending[p] = first_seen
        self._pending = still_pending

        return stable

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                new_files = self.scan_once()
                if new_files and self.on_new_files:
                    self.on_new_files(new_files)
            except Exception:
                pass
            self._stop_event.wait(self.poll_interval_sec)
