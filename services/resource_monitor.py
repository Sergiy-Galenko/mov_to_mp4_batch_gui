"""Non-blocking resource sampling shared by analytics and the idle scheduler."""

import shutil
import subprocess
import threading
import time


class ResourceMonitor:
    def __init__(self, interval: float = 2.0) -> None:
        self._interval = interval
        self._sample = {"cpu": 100.0, "gpu": None, "ram": None, "available_bytes": None}
        self._next_sample = 0.0
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None

    def sample(self) -> dict[str, float | None]:
        with self._lock:
            now = time.monotonic()
            if now >= self._next_sample and (self._worker is None or not self._worker.is_alive()):
                self._next_sample = now + self._interval
                self._worker = threading.Thread(target=self._collect, name="resource-monitor", daemon=True)
                self._worker.start()
            return dict(self._sample)

    def _collect(self) -> None:
        sample = {"cpu": None, "gpu": None, "ram": None, "available_bytes": None}
        try:
            import psutil  # type: ignore

            # Sample in the worker: a new thread's first non-blocking CPU reading
            # is meaningless and could incorrectly trigger the idle scheduler.
            sample["cpu"] = float(psutil.cpu_percent(interval=0.1))
            memory = psutil.virtual_memory()
            sample["ram"] = float(memory.percent)
            sample["available_bytes"] = float(memory.available)
        except (ImportError, OSError):
            pass
        executable = shutil.which("nvidia-smi")
        if executable:
            try:
                result = subprocess.run(
                    [executable, "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=0.4,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0:
                    values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
                    if values:
                        sample["gpu"] = max(values)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        with self._lock:
            self._sample = sample
