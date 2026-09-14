import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import QMetaObject, QObject, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QColor, QPalette
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models import TaskItem, TaskStatus
from services.theme_manager import ThemeManager
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
        brand = root.findChild(QObject, "brandMark")
        self.assertIsNotNone(brand)
        self.assertTrue(brand.property("ready"), "The integrated logo should load from the bundled assets")
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
            for _ in range(30):
                QTest.qWait(50)
                if backend.visibleQueuePaths == [str(second.path)]:
                    break
            self.assertEqual(backend.visibleQueuePaths, [str(second.path)])
            self.assertEqual(queue_grid.property("count"), 1)

            root.setProperty("queueSearchText", "")
            root.setProperty("queueStatusFilter", "processing")
            for _ in range(30):
                QTest.qWait(50)
                if backend.visibleQueuePaths == [str(first.path)]:
                    break
            self.assertEqual(backend.visibleQueuePaths, [str(first.path)])
            backend.queue_model.update_task_state(first.path, TaskStatus.SUCCESS)
            for _ in range(30):
                QTest.qWait(50)
                if backend.visibleQueueCount == 0 and queue_grid.property("count") == 0:
                    break
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

    def test_theme_editor_live_colors_modes_and_recovery(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        with tempfile.TemporaryDirectory() as temporary:
            backend = Backend()
            backend.settings_manager.save = Mock()
            backend.theme_manager = ThemeManager(Path(temporary) / "theme.json")
            engine = QQmlApplicationEngine()
            engine.addImportPath(str(qml_dir))
            engine.rootContext().setContextProperty("backend", backend)
            try:
                engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
                self.assertTrue(engine.rootObjects())
                root = engine.rootObjects()[0]
                root.setProperty("visibility", 2)
                root.setWidth(1100)
                root.setHeight(800)
                self.assertTrue(QMetaObject.invokeMethod(root, "openAppearance"))
                QTest.qWait(100)
                editor = root.findChild(QObject, "themeEditorDialog")
                self.assertIsNotNone(editor)
                self.assertTrue(editor.property("visible"))
                self.assertEqual(root.property("color").name(), "#0c0c0c")

                def find_visual(item, name):
                    if item.objectName() == name:
                        return item
                    for child in item.childItems():
                        found = find_visual(child, name)
                        if found is not None:
                            return found
                    return None

                color_list = editor.findChild(QObject, "themeColorList")
                field = find_visual(color_list.property("contentItem"), "themeHex_windowBackground")
                self.assertIsNotNone(field)
                field.setProperty("text", "#112233")
                self.assertTrue(QMetaObject.invokeMethod(field, "editingFinished"))
                QTest.qWait(30)
                self.assertEqual(root.property("color").name(), "#112233")
                self.assertEqual(ThemeManager(backend.theme_manager.path).palette()["windowBackground"], "#112233")
                editor.setProperty("editingColorKey", "accent")
                picker = editor.findChild(QObject, "themeColorDialog")
                self.assertIsNotNone(picker)
                self.assertTrue(QMetaObject.invokeMethod(picker, "open"))
                QTest.qWait(30)
                self.assertTrue(picker.property("visible"))
                picker.setProperty("selectedColor", QColor("#80556677"))
                self.assertTrue(QMetaObject.invokeMethod(picker, "accepted"))
                QMetaObject.invokeMethod(picker, "close")
                self.assertEqual(backend.themePalette["accent"], "#80556677")
                self.assertTrue(backend.setThemeColor("textPrimary", "#CDEFFF"))
                self.assertEqual(QApplication.palette().color(QPalette.Text).name(), "#cdefff")
                backend.saveNamedTheme("Test colors")
                backend.themeMode = "light"
                QTest.qWait(30)
                self.assertEqual(editor.findChild(QObject, "themeModeCombo").property("currentIndex"), 1)
                self.assertNotEqual(root.property("color").name(), "#112233")
                self.assertTrue(backend.loadNamedTheme("Test colors"))
                QTest.qWait(30)
                self.assertEqual(root.property("color").name(), "#112233")
                root.requestActivate()
                QTest.qWait(30)
                QTest.keyClick(root, Qt.Key_0, Qt.ControlModifier | Qt.AltModifier)
                QTest.qWait(30)
                self.assertEqual(root.property("color").name(), "#0c0c0c")
                self.assertEqual(backend.themeColorOverrides, {})
            finally:
                backend.shutdown()

    def test_button_mouse_keyboard_and_disabled_interactions(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        engine.loadData(b'''
import QtQuick 2.15
import QtQuick.Controls 2.15
import "components"
ApplicationWindow {
    visible: true; width: 640; height: 160
    property int activationCount: 0
    PrimaryButton { objectName: "primaryAction"; x: 20; y: 50; text: "Convert"; iconName: "play"; onClicked: activationCount++ }
    SecondaryButton { objectName: "disabledAction"; x: 220; y: 50; text: "Unavailable"; enabled: false; onClicked: activationCount++ }
    GhostButton { objectName: "toggleAction"; x: 420; y: 50; text: "Preview"; checkable: true }
}
''', QUrl.fromLocalFile(str(qml_dir / "ButtonInteractionTest.qml")))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        try:
            window.requestActivate()
            QTest.qWait(60)
            primary = window.findChild(QQuickItem, "primaryAction")
            disabled = window.findChild(QQuickItem, "disabledAction")
            toggle = window.findChild(QQuickItem, "toggleAction")

            def center(item):
                return item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()

            QTest.mouseMove(window, center(primary))
            self.assertTrue(primary.property("hovered"))
            QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, center(primary))
            self.assertTrue(primary.property("down"))
            QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, center(primary))
            self.assertEqual(window.property("activationCount"), 1)
            QTest.keyClick(window, Qt.Key_Tab)
            self.assertTrue(toggle.property("activeFocus"), "Tab must skip the disabled action")
            QTest.keyClick(window, Qt.Key_Space)
            self.assertTrue(toggle.property("checked"))
            QTest.keyClick(window, Qt.Key_Tab, Qt.ShiftModifier)
            self.assertTrue(primary.property("visualFocus"))
            QTest.keyClick(window, Qt.Key_Space)
            self.assertEqual(window.property("activationCount"), 2)
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center(disabled))
            primary.setProperty("enabled", False)
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center(primary))
            self.assertEqual(window.property("activationCount"), 2)
        finally:
            window.close()

    def test_media_editing_components_load(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        for name in ("ABCompareSlider", "TimelineTrimSlider", "CropOverlay"):
            with self.subTest(component=name):
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / "components" / f"{name}.qml")))
                self.assertFalse(component.isError(), "\n".join(error.toString() for error in component.errors()))
                item = component.create()
                self.assertIsNotNone(item)
                item.deleteLater()


if __name__ == "__main__":
    unittest.main()
