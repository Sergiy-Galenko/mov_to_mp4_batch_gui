"""Prepare runtime libraries before importing Qt. This module uses only stdlib."""

from __future__ import annotations

import contextlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.install_lock import install_lock

REQUIREMENT_IMPORTS = {
    "PySide6": "PySide6",
    "psutil": "psutil",
    "pypdf": "pypdf",
    "reportlab": "reportlab",
    "yt-dlp": "yt_dlp",
    "defusedxml": "defusedxml",
    "openai-whisper": "whisper",
}


class DependencyBootstrapError(RuntimeError):
    pass


class BootstrapCancelled(DependencyBootstrapError):
    pass


def bootstrap_enabled() -> bool:
    return os.environ.get("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", "").lower() not in {"1", "true", "yes"} and os.environ.get(
        "MEDIA_CONVERTER_AUTO_INSTALL_DEPS", "1"
    ).lower() not in {"0", "false", "no"}


def requirements(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        raise DependencyBootstrapError(f"Runtime requirements file is missing: {path}")
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.-]*)([<>=!0-9.,\s]*)", text)
        if not match:
            raise DependencyBootstrapError(f"Unsupported runtime requirement: {text}")
        result.append((match[1], match[2]))
    return result


def compatible_version(version: str, constraints: str) -> bool:
    # Runtime requirements deliberately use numeric release bounds only.
    release = version.split("+", 1)[0]
    if not re.fullmatch(r"\d+(?:\.\d+)*", release):
        return False
    for constraint in constraints.split(","):
        if not constraint.strip():
            continue
        match = re.fullmatch(r"\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)\s*", constraint)
        if not match:
            raise DependencyBootstrapError(f"Unsupported version constraint: {constraint}")
        left, right = [tuple(map(int, value.split("."))) for value in (release, match[2])]
        length = max(len(left), len(right))
        left += (0,) * (length - len(left))
        right += (0,) * (length - len(right))
        if not {">=": left >= right, "<=": left <= right, "==": left == right, "!=": left != right, ">": left > right, "<": left < right}[
            match[1]
        ]:
            return False
    return True


def missing_runtime_dependencies(requirements_path: Path) -> list[str]:
    missing = []
    for package, constraints in requirements(requirements_path):
        module = REQUIREMENT_IMPORTS.get(package, package.replace("-", "_"))
        try:
            available = importlib.util.find_spec(module) is not None
            # Frozen packages need not carry their distribution metadata.
            if available and not getattr(sys, "frozen", False):
                available = compatible_version(importlib.metadata.version(package), constraints)
        except (ImportError, ValueError, importlib.metadata.PackageNotFoundError):
            available = False
        if not available:
            missing.append(package)
    return missing


class BootstrapProcess:
    def __init__(self, progress=print, cancelled=None):
        self.progress = progress
        self.cancelled = cancelled or threading.Event()

    def check(self):
        if self.cancelled.is_set():
            raise BootstrapCancelled("Library installation cancelled")

    def run(self, args, *, timeout=1800):
        self.check()
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        env.pop("PYTHONHOME", None)
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=flags,
            start_new_session=os.name != "nt",
        ) as process:
            lines = []

            def read():
                for line in process.stdout:
                    lines.append(line)
                    self.progress(line.rstrip())

            reader = threading.Thread(target=read, daemon=True)
            reader.start()
            deadline = time.monotonic() + timeout
            try:
                while process.poll() is None:
                    self.check()
                    if time.monotonic() > deadline:
                        raise DependencyBootstrapError("Library installation timed out. Check the internet connection and retry.")
                    time.sleep(0.1)
            finally:
                if process.poll() is None:
                    if os.name == "nt":
                        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                            subprocess.run(
                                ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=3, creationflags=flags
                            )
                    else:
                        with contextlib.suppress(ProcessLookupError):
                            os.killpg(process.pid, signal.SIGKILL)
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                reader.join(timeout=5)
            output = "".join(lines)
            if process.returncode:
                raise DependencyBootstrapError(output[-4000:] or f"Library installer exited with code {process.returncode}")
            return output


@dataclass
class PreparedRuntime:
    python: str = sys.executable
    installed: list[str] = field(default_factory=list)


def probe_runtime(python: str, path: Path, process: BootstrapProcess) -> list[str]:
    script = (
        "import json,sys; sys.path.insert(0,sys.argv[1]); from pathlib import Path; "
        "from app.dependency_bootstrap import missing_runtime_dependencies; "
        "print('DEPENDENCIES='+json.dumps(missing_runtime_dependencies(Path(sys.argv[2]))))"
    )
    output = process.run([python, "-c", script, str(Path(__file__).resolve().parents[1]), str(path)], timeout=30)
    for line in reversed(output.splitlines()):
        if line.startswith("DEPENDENCIES="):
            return json.loads(line.removeprefix("DEPENDENCIES="))
    raise DependencyBootstrapError("Could not verify installed libraries")


def prepare_runtime(requirements_path: Path, process: BootstrapProcess | None = None) -> PreparedRuntime:
    path = requirements_path.expanduser().resolve()
    if os.environ.get("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", "").lower() in {"1", "true", "yes"}:
        return PreparedRuntime()
    missing = missing_runtime_dependencies(path)
    if not missing:
        return PreparedRuntime()
    if getattr(sys, "frozen", False):
        raise DependencyBootstrapError("The application bundle is incomplete. Reinstall Media Converter. Missing: " + ", ".join(missing))
    if not bootstrap_enabled():
        raise DependencyBootstrapError("Automatic library installation is disabled. Missing or incompatible: " + ", ".join(missing))
    from app.paths import APP_DATA_DIR

    process = process or BootstrapProcess()
    process.progress("Підготовка бібліотек / Preparing libraries: " + ", ".join(missing))
    # Never install into a system or Homebrew Python. Reuse a user's active venv.
    managed = sys.prefix == sys.base_prefix
    directory = (
        APP_DATA_DIR / f"python-runtime-{sys.version_info.major}.{sys.version_info.minor}-{platform.machine()}"
        if managed
        else Path(sys.prefix)
    )
    python = str(directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")) if managed else sys.executable
    process.progress("Очікування інсталятора / Waiting for the installer…")
    with install_lock(directory / ".install.lock", process.check):
        if managed and not Path(python).is_file():
            process.progress("Створення середовища / Creating application environment…")
            process.run([sys.executable, "-m", "venv", str(directory)], timeout=120)
        remaining = probe_runtime(python, path, process)
        if remaining:
            process.progress("Завантаження бібліотек / Downloading libraries…")
            try:
                process.run([python, "-m", "pip", "--version"], timeout=30)
            except DependencyBootstrapError:
                process.check()
                process.run([python, "-m", "ensurepip", "--upgrade"], timeout=120)
            process.run(
                [
                    python,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-input",
                    "--timeout",
                    "20",
                    "--retries",
                    "2",
                    "-r",
                    str(path),
                ]
            )
            if unresolved := probe_runtime(python, path, process):
                raise DependencyBootstrapError("Libraries still missing or incompatible: " + ", ".join(unresolved))
        process.check()
    return PreparedRuntime(python, remaining)
