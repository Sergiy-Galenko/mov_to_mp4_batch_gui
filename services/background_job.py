"""Cancellable, bounded subprocess jobs; all public state changes occur on Qt's thread."""
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import threading
import time

from PySide6 import QtCore


class JobCancelled(Exception):
    pass


class JobContext:
    def __init__(self, progress):
        self.cancelled = threading.Event()
        self.progress = progress

    def check(self):
        if self.cancelled.is_set():
            raise JobCancelled()

    def run(self, args, *, timeout=30, env=None):
        self.check()
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              encoding="utf-8", errors="replace", env=env, creationflags=flags,
                              start_new_session=os.name != "nt") as process:
            deadline = time.monotonic() + timeout
            try:
                while True:
                    self.check()
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"{os.path.basename(str(args[0]))}: timeout ({timeout}s)")
                    try:
                        stdout, stderr = process.communicate(timeout=0.2)
                        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                if process.poll() is None:
                    if os.name == "nt":
                        try:
                            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                           capture_output=True, timeout=3, creationflags=flags)
                        except (OSError, subprocess.TimeoutExpired):
                            process.kill()
                    else:
                        with contextlib.suppress(ProcessLookupError):
                            os.killpg(process.pid, signal.SIGKILL)
                    if process.poll() is None:
                        process.kill()
                    process.communicate()


class BackgroundJob(QtCore.QObject):
    changed = QtCore.Signal()
    completed = QtCore.Signal(dict)
    _progress = QtCore.Signal(str, int)
    _finished = QtCore.Signal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._stage = "idle"
        self._percent = 0
        self._error = ""
        self._result = {}
        self._context = None
        self._thread = None
        self._closed = False
        self._progress.connect(self._set_progress)
        self._finished.connect(self._finish)

    @QtCore.Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @QtCore.Property(str, notify=changed)
    def stage(self):
        return self._stage

    @QtCore.Property(int, notify=changed)
    def progress(self):
        return self._percent

    @QtCore.Property(str, notify=changed)
    def error(self):
        return self._error

    @QtCore.Property("QVariantMap", notify=changed)
    def result(self):
        return self._result

    def start_job(self, work):
        if self._busy or self._closed:
            return False
        self._busy, self._stage, self._percent, self._error = True, "starting", 0, ""
        self._result = {}
        context = JobContext(self._progress.emit)
        self._context = context
        self.changed.emit()

        def execute():
            result, error = {}, ""
            try:
                result = work(context)
                context.check()
            except JobCancelled:
                error = "cancelled"
            except Exception as exc:
                error = str(exc)[-4000:]
            if not self._closed:
                self._finished.emit(result, error)

        self._thread = threading.Thread(target=execute, daemon=True)
        self._thread.start()
        return True

    @QtCore.Slot(str, int)
    def _set_progress(self, stage, percent):
        if self._closed:
            return
        self._stage, self._percent = stage, percent
        self.changed.emit()

    @QtCore.Slot(dict, str)
    def _finish(self, result, error):
        if self._closed:
            return
        self._busy = False
        self._error = error
        self._stage = "cancelled" if error == "cancelled" else "error" if error else "ready"
        self._percent = 100 if not error else self._percent
        self._result = result
        self.changed.emit()
        if not error:
            self.completed.emit(result)

    @QtCore.Slot()
    def cancel(self):
        if self._context:
            self._context.cancelled.set()

    def shutdown(self):
        self._closed = True
        self.cancel()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=4)
