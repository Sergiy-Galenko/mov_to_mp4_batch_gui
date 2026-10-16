"""Packaged application self-test: QML, queue import, encode, pause/resume and cancel."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run_smoke(report_path: Path | None = None, *, require_tools: bool = True) -> int:
    started = time.perf_counter()
    # main.py establishes the isolated portable root before importing this module.
    from PySide6 import QtCore, QtQml, QtWidgets
    from PySide6.QtQuickControls2 import QQuickStyle

    from app.models import TaskStatus
    from app.paths import find_ffmpeg, find_ffprobe
    from ui.backend import Backend

    report = {"schema_version": 1, "frozen": bool(getattr(sys, "frozen", False)), "checks": {}}
    backend = engine = None
    original_critical = QtWidgets.QMessageBox.critical
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["MediaConverter self-test"])
    QQuickStyle.setStyle("Basic")

    def wait_for(predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise TimeoutError("Self-test stage timed out")
            app.processEvents()
            time.sleep(0.02)
        app.processEvents()

    try:
        ffmpeg = find_ffmpeg()
        ffprobe = find_ffprobe(ffmpeg)
        if not ffmpeg or (require_tools and not ffprobe):
            raise RuntimeError("Self-test requires bundled FFmpeg and FFprobe")
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        backend = Backend()
        # Self-tests never show blocking modal dialogs; report failures to the runner.
        QtWidgets.QMessageBox.critical = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Preflight failed"))
        engine = QtQml.QQmlApplicationEngine()
        engine.addImportPath(str(root / "ui" / "qml"))
        engine.rootContext().setContextProperty("backend", backend)
        engine.load(QtCore.QUrl.fromLocalFile(str(root / "ui" / "qml" / "Main.qml")))
        if not engine.rootObjects():
            raise RuntimeError("QML application failed to load")
        report["checks"]["qml_startup"] = True
        report["timings"] = {"startup_seconds": time.perf_counter() - started}
        with tempfile.TemporaryDirectory(prefix="media-converter-smoke-") as temporary:
            work = Path(temporary)
            source = work / "source.mov"
            out = work / "output"
            out.mkdir()
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=160x90:rate=30",
                    "-t",
                    "20",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    str(source),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            if require_tools:
                metadata = subprocess.run(
                    [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(source)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                assert float(json.loads(metadata.stdout)["format"]["duration"]) > 0
                report["checks"]["ffprobe_metadata"] = True
            backend.ffmpegPath = ffmpeg
            backend.ffmpeg_service.set_paths(ffmpeg, ffprobe)
            backend.ffmpeg_service.encoder_caps = {"libx264"}
            backend.outputDir = str(out)
            backend._add_paths([source])
            assert backend.queue_model.rowCount() == 1
            report["checks"]["queue_import"] = True
            settings = {
                "operation": "convert",
                "out_video_fmt": "mp4",
                "hw": "cpu",
                "overwrite": True,
                "preset": "ultrafast",
                "trim_end": 1,
                "cpu_load_limit": 100,
                "gpu_load_limit": 100,
            }
            backend.startConversion(settings)
            wait_for(lambda: not backend.isRunning and not backend.runner.is_running)
            output = out / "source.mp4"
            assert output.is_file() and output.stat().st_size > 0
            assert backend.queue_model.items()[0].status == TaskStatus.SUCCESS
            subprocess.run([ffmpeg, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, capture_output=True, timeout=20)
            report["checks"]["conversion_decode"] = True
            output.unlink()
            slow = {**settings, "trim_end": 20, "resize_w": 1920, "resize_h": 1080, "preset": "veryslow"}
            backend.startConversion(slow)
            wait_for(lambda: backend.converter.current_proc is not None)
            backend.pauseConversion()
            assert backend.isPaused and backend.converter.pause_event.is_set()
            report["checks"]["pause"] = True
            backend.resumeConversion()
            assert not backend.isPaused and not backend.converter.pause_event.is_set()
            report["checks"]["resume"] = True
            backend.stopConversion()
            wait_for(lambda: not backend.runner.is_running and not backend.isRunning)
            assert not output.exists()
            assert not list(out.glob(".*.partial*"))
            report["checks"]["cancel_cleanup"] = True
        report["ok"] = True
    except Exception as exc:
        # No paths or raw FFmpeg stderr leave the isolated package test.
        report["ok"] = False
        report["failure_type"] = type(exc).__name__
    finally:
        QtWidgets.QMessageBox.critical = original_critical
        if backend:
            backend.shutdown()
            if backend._converter_service and backend.converter.thread:
                backend.converter.thread.join(timeout=10)
        if engine:
            for window in engine.rootObjects():
                window.close()
            engine.deleteLater()
            app.processEvents()
        if report_path:
            from utils.state import save_json_file

            save_json_file(report_path, report)
        if sys.stdout is not None:
            print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1
