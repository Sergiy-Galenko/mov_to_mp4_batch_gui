import os
from PySide6.QtQuickControls2 import QQuickStyle

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
QQuickStyle.setStyle("Basic")

