import os
import unittest
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuickControls2 import QQuickStyle

from ui.qml_backend import Backend


class QmlLoadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        QQuickStyle.setStyle("Basic")
        cls._app = QApplication.instance() or QApplication([])

    def test_main_qml_loads(self):
        project_root = Path(__file__).resolve().parents[1]
        qml_dir = project_root / "ui" / "qml"
        theme_qml = qml_dir / "Theme.qml"
        main_qml = qml_dir / "Main.qml"

        qmlRegisterSingletonType(QUrl.fromLocalFile(str(theme_qml)), "App", 1, 0, "Theme")

        engine = QQmlApplicationEngine()
        backend = Backend()
        engine.rootContext().setContextProperty("backend", backend)
        engine.load(QUrl.fromLocalFile(str(main_qml)))

        self.assertTrue(engine.rootObjects(), "QML root objects should be created")


if __name__ == "__main__":
    unittest.main()
