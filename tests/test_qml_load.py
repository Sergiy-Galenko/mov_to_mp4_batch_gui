import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import Q_ARG, QEvent, QMetaObject, QObject, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QColor, QMouseEvent, QPalette
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

    def test_whisper_manager_selection_progress_errors_and_reopening(self):
        from services.whisper_model_manager import WhisperModelManager

        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        with tempfile.TemporaryDirectory() as temporary:
            backend = Backend()
            backend.settings_manager.save = Mock()
            backend.whisper_model_manager.shutdown()
            backend.whisper_model_manager = WhisperModelManager(Path(temporary))
            engine = QQmlApplicationEngine()
            engine.addImportPath(str(qml_dir))
            engine.rootContext().setContextProperty("backend", backend)
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
            try:
                engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
                self.assertTrue(engine.rootObjects())
                root = engine.rootObjects()[0]
                manager = root.findChild(QObject, "whisperModelManager")
                self.assertIsNotNone(manager)
                self.assertTrue(QMetaObject.invokeMethod(manager, "open"))
                QTest.qWait(80)
                self.assertTrue(manager.property("visible"))
                self.assertEqual(root.findChild(QObject, "whisperModelsList").property("count"), 6)
                self.assertTrue(QMetaObject.invokeMethod(manager, "chooseModel", Q_ARG("QVariant", "tiny")))
                self.assertTrue(QMetaObject.invokeMethod(manager, "chooseDevice", Q_ARG("QVariant", "cpu")))
                for _ in range(20):
                    QTest.qWait(50)
                    if backend._last_settings_map.get("subtitle_device") == "cpu":
                        break
                self.assertEqual(manager.property("selectedModel"), "tiny")
                self.assertEqual(manager.property("selectedDevice"), "cpu")
                self.assertEqual(backend._last_settings_map["subtitle_model"], "tiny")
                self.assertEqual(backend._last_settings_map["subtitle_device"], "cpu")
                # A zero-percent event is still an active transfer, not completion.
                manager.setProperty("activeDownloadingModel", "tiny")
                backend.whisperDownloadProgress.emit("tiny", 0.0, "tiny.pt")
                QTest.qWait(20)
                self.assertTrue(manager.property("downloading"))
                QMetaObject.invokeMethod(manager, "close")
                backend.whisper_model_manager._states[("tiny", "whisper")] = {
                    "state": "error",
                    "error": "Checksum mismatch",
                    "progress": 0.0,
                }
                QMetaObject.invokeMethod(manager, "open")
                QTest.qWait(80)
                self.assertFalse(manager.property("downloading"))
                self.assertEqual(manager.property("selectedDevice"), "cpu")
                self.assertFalse([warning for warning in warnings if "WhisperModelManagerModal.qml" in warning], warnings)
            finally:
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
                self.assertEqual(root.property("color").name(), backend.themePalette["windowBackground"].lower())

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
                self.assertEqual(root.property("color").name(), backend.themePalette["windowBackground"].lower())
                self.assertEqual(backend.themeColorOverrides, {})
            finally:
                backend.shutdown()

    def test_button_mouse_keyboard_and_disabled_interactions(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        engine.loadData(
            b"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import "components"
ApplicationWindow {
    visible: true; width: 640; height: 200
    property int activationCount: 0
    PrimaryButton { objectName: "primaryAction"; x: 20; y: 50; text: "Convert"; iconName: "play"; onClicked: activationCount++ }
    SecondaryButton { objectName: "disabledAction"; x: 220; y: 50; text: "Unavailable"; enabled: false; onClicked: activationCount++ }
    GhostButton { objectName: "toggleAction"; x: 420; y: 50; text: "Preview"; checkable: true }
    AppSwitch { objectName: "featureSwitch"; x: 20; y: 120; width: 260; text: "Enable feature" }
}
""",
            QUrl.fromLocalFile(str(qml_dir / "ButtonInteractionTest.qml")),
        )
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
            feature_switch = window.findChild(QQuickItem, "featureSwitch")
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center(feature_switch))
            self.assertTrue(feature_switch.property("checked"))
            feature_switch.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_Space)
            self.assertFalse(feature_switch.property("checked"))
            feature_switch.setProperty("enabled", False)
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center(feature_switch))
            self.assertFalse(feature_switch.property("checked"))
        finally:
            window.close()

    def test_settings_navigation_preserves_values_and_history(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        with tempfile.TemporaryDirectory() as temporary:
            backend = Backend()
            backend.settings_manager.save = Mock()
            backend.theme_manager = ThemeManager(Path(temporary) / "theme.json")
            engine = QQmlApplicationEngine()
            engine.addImportPath(str(qml_dir))
            engine.rootContext().setContextProperty("backend", backend)
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
            try:
                engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
                self.assertTrue(engine.rootObjects(), warnings)
                window = engine.rootObjects()[0]
                window.setProperty("visibility", 2)
                window.setWidth(1240)
                window.setHeight(840)
                QMetaObject.invokeMethod(window.findChild(QObject, "whatsNewPopup"), "close")

                def open_page(target):
                    self.assertTrue(
                        QMetaObject.invokeMethod(
                            window, "openSidebarSection", Q_ARG("QVariant", 5), Q_ARG("QVariant", target), Q_ARG("QVariant", -1)
                        )
                    )
                    QTest.qWait(70)

                open_page("core")
                field = window.findChild(QObject, "targetSizeField")
                field.setProperty("text", "125")
                open_page("smart_convert")
                switch = window.findChild(QQuickItem, "smartConvertSwitch")
                switch.setProperty("checked", True)
                pages = [
                    "output",
                    "video",
                    "video_editor",
                    "audio_subtitles",
                    "subtitle_tools",
                    "images_sheets",
                    "watermark_text",
                    "metadata_hooks",
                    "privacy_security",
                    "cloud_integration",
                    "device_profiles",
                    "ffmpeg_watch",
                    "commercial_license",
                ]
                for target in pages:
                    with self.subTest(page=target):
                        open_page(target)
                        current = window.findChild(QQuickItem, "settingsPage_" + target)
                        self.assertTrue(current.isVisible())
                        self.assertGreater(current.width(), 0)
                        for page in window.findChildren(QQuickItem):
                            if page.objectName().startswith("settingsPage_") and page is not current:
                                self.assertFalse(page.isVisible(), page.objectName())
                viewport = window.findChild(QObject, "navigationScroll").property("contentItem")
                self.assertGreater(viewport.property("contentY"), 0, "Last section must scroll into view")
                open_page("smart_convert")
                self.assertTrue(switch.property("checked"))
                open_page("core")
                self.assertEqual(field.property("text"), "125")
                cursor = window.property("navigationCursor")
                open_page("core")
                self.assertEqual(window.property("navigationCursor"), cursor, "Reopening a page must not duplicate history")
                self.assertTrue(QMetaObject.invokeMethod(window, "navigateHistory", Q_ARG("QVariant", -1)))
                self.assertEqual(window.property("pendingSettingsTarget"), "smart_convert")
                self.assertTrue(window.property("canNavigateForward"))
                self.assertTrue(QMetaObject.invokeMethod(window, "navigateHistory", Q_ARG("QVariant", 1)))
                self.assertEqual(window.property("pendingSettingsTarget"), "core")
                QMetaObject.invokeMethod(window, "navigateHistory", Q_ARG("QVariant", -1))
                open_page("output")
                self.assertFalse(window.property("canNavigateForward"), "New page replaces the forward branch")
                self.assertEqual(window.findChild(QObject, "languageMenu").property("count"), 4)
                window.requestActivate()
                search = window.findChild(QQuickItem, "sidebarSearchField")
                search.forceActiveFocus()
                search.setProperty("text", "audio")
                QTest.qWait(60)
                self.assertTrue(search.property("activeFocus"), "Search results must not steal typing focus")
                QTest.keyClick(window, Qt.Key_Return)
                self.assertEqual(window.property("pendingSettingsTarget"), "audio_subtitles")
                search.setProperty("text", "")
                window.setProperty("sidebarCollapsed", True)
                QTest.qWait(60)
                self.assertLess(window.findChild(QQuickItem, "appSidebar").width(), 100)
                self.assertFalse(warnings, warnings)
            finally:
                backend.shutdown()

    def test_media_editing_components_load(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        for name in ("ABCompareSlider", "TimelineTrimSlider", "CropOverlay", "InOutMarker", "Timeline"):
            with self.subTest(component=name):
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / "components" / f"{name}.qml")))
                self.assertFalse(component.isError(), "\n".join(error.toString() for error in component.errors()))
                item = component.create()
                self.assertIsNotNone(item)
                item.deleteLater()

    def test_montage_editor_dialog_loads(self):
        qml_dir = Path(__file__).resolve().parents[1] / "ui" / "qml"
        backend = Backend()
        backend.settings_manager.save = Mock()
        try:
            engine = QQmlApplicationEngine()
            engine.addImportPath(str(qml_dir))
            engine.rootContext().setContextProperty("backend", backend)
            component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / "components" / "MontageEditorDialog.qml")))
            self.assertFalse(component.isError(), "\n".join(error.toString() for error in component.errors()))
            dialog = component.create()
            self.assertIsNotNone(dialog)
            self.assertEqual(dialog.property("duration"), 0.0)
            self.assertFalse(dialog.property("cropEnabled"))
            dialog.deleteLater()
        finally:
            backend.shutdown()

    def test_title_bar_dragging(self):
        project_root = Path(__file__).resolve().parents[1]
        qml_dir = project_root / "ui" / "qml"
        main_qml = qml_dir / "Main.qml"

        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        backend = Backend()
        backend.settings_manager.save = Mock()
        try:
            engine.rootContext().setContextProperty("backend", backend)
            engine.load(QUrl.fromLocalFile(str(main_qml)))
            self.assertTrue(engine.rootObjects(), "QML root objects should be created")
            root = engine.rootObjects()[0]
            root.show()

            root.setX(100)
            root.setY(100)

            drag_area = root.findChild(QObject, "titleBarDragArea")
            self.assertIsNotNone(drag_area, "titleBarDragArea should exist in AppTitleBar")

            # Simulate mouse press on title bar
            click_pos = QPointF(400, 20)
            global_pos = QPointF(root.x() + 400, root.y() + 20)
            press_ev = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                click_pos,
                global_pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QApplication.sendEvent(root, press_ev)

            # Move mouse by +50 in x and +30 in y
            move_pos = QPointF(450, 50)
            global_move_pos = QPointF(root.x() + 450, root.y() + 50)
            move_ev = QMouseEvent(
                QEvent.Type.MouseMove,
                move_pos,
                global_move_pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QApplication.sendEvent(root, move_ev)

            self.assertEqual(root.x(), 150)
            self.assertEqual(root.y(), 130)

            # Release mouse
            release_ev = QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                move_pos,
                global_move_pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QApplication.sendEvent(root, release_ev)
            self.assertFalse(drag_area.property("manualDragging"))
        finally:
            backend.shutdown()


if __name__ == "__main__":
    unittest.main()

