import os
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import QObject, QSettings, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models import TaskItem, TaskStatus
from ui.backend import Backend


class QmlLoadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        QQuickStyle.setStyle("Basic")
        cls._app = QApplication.instance() or QApplication([])
        cls._app.setOrganizationName("MediaConverterTests")
        cls._app.setApplicationName("MediaConverterTests")
        QSettings.setDefaultFormat(QSettings.IniFormat)
        import tempfile

        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.gettempdir())

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
        backend.settings_manager.save = Mock()
        backend.shutdown()

    def test_queue_views_search_and_status_filter_remain_in_sync(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        backend = Backend()
        backend.settings_manager.save = Mock()
        backend.queueViewMode = "list"
        first = TaskItem(Path("/demo/first.mp4"), "video", status=TaskStatus.RUNNING)
        second = TaskItem(Path("/demo/second.mp4"), "video")
        backend.queue_model.set_items([first, second])
        engine.rootContext().setContextProperty("backend", backend)
        try:
            engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
            self.assertTrue(engine.rootObjects())
            root = engine.rootObjects()[0]
            QTest.qWait(30)
            queue_list = root.findChild(QObject, "queueList")
            queue_grid = root.findChild(QObject, "queueGrid")
            self.assertEqual(queue_list.property("count"), 2)
            self.assertEqual(queue_grid.property("count"), 0)

            backend.queueViewMode = "grid"
            QTest.qWait(30)
            self.assertEqual(queue_list.property("count"), 0)
            self.assertEqual(queue_grid.property("count"), 2)

            root.setProperty("queueSearchText", "second")
            QTest.qWait(230)
            self.assertEqual(backend.visibleQueuePaths, [str(second.path)])
            self.assertEqual(queue_grid.property("count"), 1)

            root.setProperty("queueSearchText", "")
            root.setProperty("queueStatusFilter", "processing")
            QTest.qWait(30)
            self.assertEqual(backend.visibleQueuePaths, [str(first.path)])
            backend.queue_model.update_task_state(first.path, TaskStatus.SUCCESS)
            QTest.qWait(30)
            self.assertEqual(backend.visibleQueueCount, 0)
            self.assertEqual(queue_grid.property("count"), 0)
        finally:
            backend.shutdown()

    def test_queue_item_media_type_icon_loads(self):
        project_root = Path(__file__).resolve().parents[1]
        qml_dir = project_root / "ui" / "qml"

        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        qml = b"""
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
"""
        component = QQmlComponent(engine)
        component.setData(qml, QUrl.fromLocalFile(str(qml_dir / "InlineQueueItem.qml")))

        self.assertFalse(component.isError(), "\n".join(error.toString() for error in component.errors()))
        item = component.create()
        self.assertIsNotNone(item, "Queue item with media type icon should be created")
        item.deleteLater()


if __name__ == "__main__":
    unittest.main()
