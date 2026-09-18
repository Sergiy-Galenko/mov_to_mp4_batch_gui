import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QUrl
from PySide6.QtGui import QKeySequence
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.backend import Backend


@pytest.fixture
def window(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    if not QApplication.instance():
        QQuickStyle.setStyle("Basic")
    app = QApplication.instance() or QApplication([])
    backend = Backend()
    backend.settings_manager.save = Mock()
    backend.settings_manager.state["auto_tune_enabled"] = False
    backend._last_settings_map = {}
    backend.startSystemScan = Mock()
    backend.refreshEncoders = Mock()
    backend.setupSystemTray = Mock()
    engine = QQmlApplicationEngine()
    directory = Path(__file__).resolve().parents[1] / "ui/qml"
    engine.addImportPath(str(directory))
    engine.rootContext().setContextProperty("backend", backend)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    engine.load(QUrl.fromLocalFile(str(directory / "Main.qml")))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    QTest.qWait(30)
    yield root, backend, app
    backend.shutdown()
    root.close()
    engine.deleteLater()
    app.processEvents()
    assert not [warning for warning in warnings if any(name in warning for name in ("UndoHistory.qml", "HistoryButtons.qml", "SystemStatusBar.qml", "WhisperSetupDialog.qml"))], warnings


def invoke(obj, method, *values):
    assert QMetaObject.invokeMethod(obj, method, *[Q_ARG("QVariant", value) for value in values])


def test_settings_undo_redo_and_branching(window):
    root, _backend, _ = window
    history = root.findChild(QObject, "settingsUndoHistory")
    field = root.findChild(QObject, "targetSizeField")
    original = field.property("text")
    invoke(history, "reset")
    original_settings = json.loads(history.property("current"))
    field.setProperty("text", "123")
    # Undo works even before the coalescing timer fires.
    invoke(history, "undo")
    assert field.property("text") == original
    assert json.loads(history.property("current")) == original_settings
    invoke(history, "redo")
    assert field.property("text") == "123"
    invoke(history, "undo")
    field.setProperty("text", "456")
    invoke(history, "flush")
    assert not history.property("canRedo")
    invoke(history, "undo")
    assert field.property("text") == original
    assert not history.property("canUndo")
    assert history.property("canRedo")


def test_montage_gesture_is_one_edit_and_reopen_clears_history(window):
    root, _backend, _ = window
    montage = root.findChild(QObject, "montageEditorDialog")
    invoke(montage, "openForFile", "")
    QTest.qWait(30)
    history = montage.findChild(QObject, "montageUndoHistory")
    invoke(history, "reset")
    invoke(history, "begin")
    montage.setProperty("inPoint", 1.0)
    QTest.qWait(350)
    montage.setProperty("inPoint", 2.0)
    montage.setProperty("cropEnabled", True)
    montage.setProperty("cropX", 100)
    montage.setProperty("cropW", 1280)
    invoke(history, "end")
    invoke(history, "undo")
    assert montage.property("inPoint") == 0
    assert montage.property("cropX") == 0
    assert not montage.property("cropEnabled")
    assert not history.property("canUndo")
    invoke(history, "redo")
    assert montage.property("inPoint") == 2
    assert montage.property("cropX") == 100
    assert montage.property("cropW") == 1280
    # Playback isn't an edit and must not clear redo.
    invoke(history, "undo")
    montage.setProperty("playhead", 20.0)
    QTest.qWait(350)
    assert history.property("canRedo")
    invoke(montage, "openForFile", "")
    QTest.qWait(30)
    assert not history.property("canUndo")
    assert not history.property("canRedo")
    montage.close()


def test_auto_profile_respects_opt_out_and_preserves_video_quality(window):
    root, backend, _ = window
    field = root.findChild(QObject, "targetSizeField")
    field.setProperty("text", "321")
    backend.concurrencyLimit = 5
    recommendation = {"concurrency_limit": 1, "cpu_load_limit": 75, "gpu_load_limit": 90, "low_resource_mode": True}
    backend._apply_system_profile({"recommendation": recommendation})
    assert backend.concurrencyLimit == 5
    backend.autoTuneEnabled = True
    backend._apply_system_profile({"recommendation": recommendation})
    QTest.qWait(300)
    assert backend.concurrencyLimit == 1
    assert backend._last_settings_map["concurrency_limit"] == 1
    assert backend._last_settings_map["cpu_load_limit"] == 75
    assert field.property("text") == "321"
    history = root.findChild(QObject, "settingsUndoHistory")
    invoke(history, "undo")
    assert field.property("text") != "321"
    # An unrelated undo cannot restore the old, excessive workload.
    assert backend.concurrencyLimit == 1
    assert json.loads(history.property("current"))["cpu_load_limit"] == 75


def test_tuning_waits_for_running_conversion(window):
    _root, backend, _ = window
    backend.autoTuneEnabled = True
    backend.concurrencyLimit = 3
    backend._is_running = True
    backend._apply_system_profile({"recommendation": {"concurrency_limit": 1, "cpu_load_limit": 75, "gpu_load_limit": 90}})
    assert backend.concurrencyLimit == 3
    assert backend.autoTunePending
    backend._is_running = False
    backend.isRunningChanged.emit()
    assert not backend.autoTunePending
    assert backend.concurrencyLimit == 1


def test_system_and_whisper_setup_controls_load(window):
    root, _, _ = window
    assert root.findChild(QObject, "systemStatusBar")
    system = root.findChild(QObject, "systemProfileDialog")
    invoke(system, "open")
    assert system.property("visible")
    invoke(system, "close")
    setup = root.findChild(QObject, "whisperSetupDialog")
    assert setup
    invoke(root.findChild(QObject, "whisperModelManager"), "open")
    QTest.qWait(30)
    invoke(setup, "open")
    QTest.qWait(30)
    assert setup.property("visible")
    assert not setup.findChild(QObject, "whisperTestButton").property("enabled")
    invoke(setup, "close")


def test_shortcut_undo_redo_and_native_text_editing(window):
    root, _, _ = window
    invoke(root, "openSidebarSection", 5, "core", -1)
    root.requestActivate()
    QTest.qWait(30)
    field = root.findChild(QQuickItem, "targetSizeField")
    history = root.findChild(QObject, "settingsUndoHistory")
    field.setProperty("text", "")
    invoke(history, "reset")
    field.forceActiveFocus()
    for key in (Qt.Key_1, Qt.Key_2, Qt.Key_3):
        QTest.keyClick(root, key)
    assert field.property("text") == "123"
    # Text controls retain their own standard editing shortcuts.
    QTest.keySequence(root, QKeySequence(QKeySequence.StandardKey.Undo))
    assert field.property("text") == ""
    QTest.keySequence(root, QKeySequence(QKeySequence.StandardKey.Redo))
    assert field.property("text") == "123"
    root.contentItem().forceActiveFocus()
    QTest.qWait(20)
    QTest.keySequence(root, QKeySequence(QKeySequence.StandardKey.Undo))
    assert field.property("text") == ""
    QTest.keySequence(root, QKeySequence(QKeySequence.StandardKey.Redo))
    assert field.property("text") == "123"
