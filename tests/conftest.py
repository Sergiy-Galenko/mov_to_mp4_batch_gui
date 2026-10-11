import atexit
import os
import shutil
import tempfile

from PySide6.QtQuickControls2 import QQuickStyle

# Tests must never read or overwrite the user's presets, history or Whisper manifest.
_test_portable_root = tempfile.mkdtemp(prefix="media-converter-tests-")
os.environ["MEDIA_CONVERTER_PORTABLE_DIR"] = _test_portable_root
atexit.register(shutil.rmtree, _test_portable_root, ignore_errors=True)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
QQuickStyle.setStyle("Basic")
