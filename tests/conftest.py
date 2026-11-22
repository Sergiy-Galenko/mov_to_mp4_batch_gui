import atexit
import os
import shutil
import sys
import tempfile

import pytest
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

# Tests must never read or overwrite the user's presets, history or Whisper manifest.
_test_portable_root = tempfile.mkdtemp(prefix="media-converter-tests-")
os.environ["MEDIA_CONVERTER_PORTABLE_DIR"] = _test_portable_root
atexit.register(shutil.rmtree, _test_portable_root, ignore_errors=True)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if sys.platform.startswith("linux") and os.environ["QT_QPA_PLATFORM"] == "offscreen":
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
QQuickStyle.setStyle("Basic")


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    # Backend constructs timers and reads style hints, even in tests without a window.
    return QApplication.instance() or QApplication([])


def pytest_sessionfinish():
    # Preserve thread stacks if a third-party worker prevents interpreter shutdown in CI.
    if os.environ.get("CI"):
        import faulthandler

        faulthandler.dump_traceback_later(90, repeat=True)
