"""Behavioral coverage for the shared dropdown in clipped layouts and dialogs."""

from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPointF, QStringListModel, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

QML_DIR = Path(__file__).resolve().parents[1] / "ui" / "qml"


@pytest.fixture(scope="module")
def app():
    QQuickStyle.setStyle("Basic")
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dropdown(app):
    engines = []

    def create(kind="AppComboBox", extra="", width=480, height=360):
        engine = QQmlApplicationEngine()
        engines.append(engine)
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("backend", None)
        model = QStringListModel(["Preset A", "Preset B", "Preset C"], engine)
        engine.rootContext().setContextProperty("presetModel", model)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        engine.loadData(
            f'''
import QtQuick
import QtQuick.Controls.Basic
import "components"
import "editor"
ApplicationWindow {{
    width: {width}; height: {height}; visible: true
    property int activations: 0
    property string acceptedText: ""
    Item {{
        x: 20; y: 20; width: 220; height: 40; clip: true
        {kind} {{
            id: combo; objectName: "combo"; width: 220
            model: ["jpg", "png", "webp", "bmp", "tiff"]
            onActivated: activations++
            onAccepted: acceptedText = editText
            {extra}
        }}
    }}
    function openMenu() {{ combo.popup.open() }}
    function place(x, y) {{ combo.parent.x = x; combo.parent.y = y }}
    function rowAt(index) {{ return combo.popup.contentItem.itemAtIndex(index) }}
    function menu() {{ return combo.popup }}
}}
'''.encode(),
            QUrl.fromLocalFile(str(QML_DIR / "DropdownTest.qml")),
        )
        assert engine.rootObjects(), warnings
        window = engine.rootObjects()[0]
        window.requestActivate()
        QTest.qWait(30)
        combo = window.findChild(QQuickItem, "combo")
        popup = window.findChild(QObject, "comboPopup")
        assert popup is not None
        return window, combo, popup, warnings, model

    yield create
    for engine in engines:
        for window in engine.rootObjects():
            window.close()
        engine.deleteLater()
    app.processEvents()


def open_menu(window):
    assert QMetaObject.invokeMethod(window, "openMenu")
    QTest.qWait(80)


def descendants(item):
    yield item
    for child in item.childItems():
        yield from descendants(child)


def rows(popup):
    return sorted(
        (item for item in descendants(popup.property("contentItem")) if item.property("text") in {"jpg", "png", "webp", "bmp", "tiff"}),
        key=lambda item: item.y(),
    )


@pytest.mark.parametrize("kind", ["AppComboBox", "EditorCombo"])
@pytest.mark.parametrize("font_size", [13, 26])
def test_option_text_fits_and_mouse_selects_once(dropdown, kind, font_size):
    window, combo, popup, warnings, _ = dropdown(kind, f"font.pixelSize: {font_size}")
    open_menu(window)
    view = popup.property("contentItem")
    delegates = [item for item in descendants(view) if item.metaObject().indexOfProperty("highlighted") >= 0]
    assert len(delegates) >= 2
    for row in delegates:
        content = row.property("contentItem")
        assert content.height() >= content.property("implicitHeight"), "The delegate clips the option text vertically"
        assert row.width() <= view.width(), "The row extends into the popup padding"
    target = next(row for row in delegates if row.property("text") == "png")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, target.mapToScene(QPointF(target.width() / 2, target.height() / 2)).toPoint())
    QTest.qWait(80)
    assert combo.property("currentText") == "png"
    assert window.property("activations") == 1
    assert not popup.property("visible")
    assert not warnings


def test_popup_flips_above_bottom_edge_and_esc_keeps_selection(dropdown):
    window, combo, popup, warnings, _ = dropdown()
    QMetaObject.invokeMethod(window, "place", Q_ARG("QVariant", 380), Q_ARG("QVariant", 310))
    open_menu(window)
    assert popup.property("y") < 0
    item = popup.property("contentItem")
    rect = item.mapToScene(QPointF(0, 0))
    assert rect.x() >= 0 and rect.y() >= 0
    assert rect.x() + item.width() <= window.width()
    assert rect.y() + item.height() <= window.height()
    QTest.keyClick(window, Qt.Key_Down)
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(80)
    assert not popup.property("visible")
    assert combo.property("currentIndex") == 0
    assert window.property("activations") == 0
    assert not warnings


def test_keyboard_commit_and_outside_click(dropdown):
    window, combo, popup, warnings, _ = dropdown()
    combo.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Space)
    QTest.qWait(80)
    assert popup.property("visible")
    QTest.keyClick(window, Qt.Key_Down)
    QTest.keyClick(window, Qt.Key_Return)
    QTest.qWait(80)
    assert combo.property("currentText") == "png"
    assert window.property("activations") == 1
    assert not popup.property("visible")
    open_menu(window)
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPointF(450, 340).toPoint())
    QTest.qWait(80)
    assert not popup.property("visible")
    assert combo.property("currentText") == "png"
    assert not warnings


@pytest.mark.parametrize("model_expression,role,expected", [
    ('["first", "second"]', "", "second"),
    ('[{label: "Українська", code: "uk"}, {label: "English", code: "en"}]', "label", "English"),
    ('presetModel', "display", "Preset B"),
])
def test_models_and_roles(dropdown, model_expression, role, expected):
    window, combo, popup, warnings, _ = dropdown(extra=f'textRole: "{role}"')
    # Assign through QML so JS arrays and Qt item models keep their native types.
    context = QQmlApplicationEngine.contextForObject(combo)
    from PySide6.QtQml import QQmlExpression
    expression = QQmlExpression(context, combo, f"model = {model_expression}")
    expression.evaluate()
    assert not expression.hasError()
    open_menu(window)
    QTest.keyClick(window, Qt.Key_Down)
    QTest.keyClick(window, Qt.Key_Return)
    QTest.qWait(80)
    assert combo.property("currentText") == expected
    assert not popup.property("visible")
    assert not warnings
