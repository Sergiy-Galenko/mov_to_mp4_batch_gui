import os
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from ui.backend import Backend


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
        main_qml = qml_dir / "Main.qml"

        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        backend = Backend()
        engine.rootContext().setContextProperty("backend", backend)
        engine.load(QUrl.fromLocalFile(str(main_qml)))

        self.assertTrue(engine.rootObjects(), "QML root objects should be created")
        root = engine.rootObjects()[0]
        self.assertGreater(
            root.property("queueDropZoneHeight"),
            0,
            "Queue drop zone should have a real drop area",
        )
        self.assertIsNotNone(
            root.findChild(QObject, "queueAppendDropArea"),
            "Queue should keep a file drop area after the first item is added",
        )

    def test_queue_item_media_type_icon_loads(self):
        project_root = Path(__file__).resolve().parents[1]
        qml_dir = project_root / "ui" / "qml"

        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        qml = b'''
import QtQuick 2.15
import "components"

QueueItemCard {
    width: 720
    fileName: "report.pdf"
    filePath: "C:/Temp/report.pdf"
    mediaType: "text"
    thumbnailSource: ""
    status: "queued"
}
'''
        component = QQmlComponent(engine)
        component.setData(qml, QUrl.fromLocalFile(str(qml_dir / "InlineQueueItem.qml")))

        self.assertFalse(component.isError(), "\n".join(error.toString() for error in component.errors()))
        item = component.create()
        self.assertIsNotNone(item, "Queue item with media type icon should be created")
        item.deleteLater()


if __name__ == "__main__":
    unittest.main()
