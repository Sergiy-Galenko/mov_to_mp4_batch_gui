from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from PySide6 import QtCore

from app.dependency_bootstrap import compatible_version
from app.install_lock import install_lock
from app.paths import APP_DATA_DIR
from services.background_job import BackgroundJob
from services.whisper_environment import managed_runtime, save_runtime, worker_command, worker_environment

PACKAGES = {"whisper": "openai-whisper>=20250625", "faster-whisper": "faster-whisper"}


def read_worker_result(process) -> dict:
    if process.returncode:
        raise RuntimeError((process.stderr or process.stdout or "Whisper worker failed")[-4000:])
    for line in reversed(process.stdout.splitlines()):
        if line.startswith("WHISPER_RESULT="):
            return json.loads(line.removeprefix("WHISPER_RESULT="))
    raise RuntimeError("Whisper worker returned no result")


def check_runtime(context, python="") -> dict:
    context.progress("devices", 80)
    result = read_worker_result(context.run(worker_command("diagnose", python=python), timeout=120, env=worker_environment()))
    runtime = managed_runtime()
    if runtime and not python:
        save_runtime(runtime["python"], result)
    return result


def install_runtime(context, engine, base_python="", *, only_if_missing=False) -> dict:
    if engine not in PACKAGES:
        raise ValueError("Unsupported Whisper engine")
    context.progress("waiting", 5)
    with install_lock(APP_DATA_DIR / "whisper-runtime.install.lock", context.check):
        if only_if_missing:
            report = _startup_report(context)
            if _engine_ready(report, engine):
                return report
        return _install_runtime(context, engine, base_python)


def _install_runtime(context, engine, base_python="") -> dict:
    context.progress("environment", 10)
    directory = APP_DATA_DIR / "whisper-runtime"
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        base = base_python or (sys.executable if not getattr(sys, "frozen", False) else shutil.which("python3") or shutil.which("python"))
        if not base:
            raise RuntimeError("Install Python 3.12+ and choose its executable, then retry.")
        created = context.run([base, "-m", "venv", str(directory)], timeout=120)
        if created.returncode:
            raise RuntimeError((created.stderr or created.stdout)[-4000:])
    context.progress("installing", 35)
    installed = context.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                             "--timeout", "20", "--retries", "2", PACKAGES[engine]],
                            timeout=1800, env=worker_environment())
    if installed.returncode:
        raise RuntimeError((installed.stderr or installed.stdout)[-4000:])
    report = check_runtime(context, str(python))
    if not report["engines"][engine]["installed"]:
        raise RuntimeError("; ".join(report["engines"][engine]["errors"]) or "Whisper import failed")
    context.check()
    save_runtime(str(python), report)
    return report


def _engine_ready(report, engine):
    info = report.get("engines", {}).get(engine, {})
    return bool(info.get("installed")) and (engine != "whisper" or compatible_version(info.get("version", ""), ">=20250625"))


def _startup_report(context):
    try:
        return check_runtime(context)
    except (RuntimeError, OSError):
        context.check()
        return {"engines": {}}


def ensure_runtime(context, engine="auto") -> dict:
    """No pip/network activity when the selected inference engine already works."""
    if engine not in {*PACKAGES, "auto"}:
        raise ValueError("Unsupported Whisper engine")
    report = _startup_report(context)
    if engine == "auto":
        engine = next((name for name in PACKAGES if _engine_ready(report, name)), "whisper")
    if _engine_ready(report, engine):
        return report
    return install_runtime(context, engine, only_if_missing=True)


def test_recognition(context, source, model, engine, device, ffmpeg):
    if not Path(source).is_file():
        raise ValueError("Choose an audio or video file with speech.")
    if not ffmpeg:
        raise ValueError("FFmpeg is required for the recognition test.")
    context.progress("sample", 15)
    with tempfile.TemporaryDirectory(prefix="whisper-test-") as temporary:
        audio = str(Path(temporary) / "sample.wav")
        output = str(Path(temporary) / "sample.txt")
        # Limit decoding as well as inference to the first 12 seconds.
        sample = context.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", source,
                              "-t", "12", "-vn", "-ac", "1", "-ar", "16000", audio], timeout=45)
        if sample.returncode:
            raise RuntimeError(sample.stderr[-4000:])
        context.progress("recognizing", 50)
        return read_worker_result(context.run(worker_command("test", audio, output, model, engine, device),
                                              timeout=300, env=worker_environment(ffmpeg)))


class WhisperSetup(BackgroundJob):
    devicesChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._diagnostics = managed_runtime().get("report", {})
        self.completed.connect(self._remember)

    @QtCore.Property("QVariantMap", notify=devicesChanged)
    def diagnostics(self):
        return self._diagnostics

    @QtCore.Slot(dict)
    def _remember(self, report):
        if "engines" in report:
            self._diagnostics = report
            self.devicesChanged.emit()

    @QtCore.Slot()
    def check(self):
        self.start_job(check_runtime)

    @QtCore.Slot(str, str)
    def install(self, engine, base_python=""):
        self.start_job(lambda context: install_runtime(context, engine, base_python))

    @QtCore.Slot(str)
    def ensure(self, engine="auto"):
        self.start_job(lambda context: ensure_runtime(context, engine))

    @QtCore.Slot(str, str, str, str, str)
    def test(self, source, model, engine, device, ffmpeg):
        self.start_job(lambda context: test_recognition(context, source, model, engine, device, ffmpeg))
