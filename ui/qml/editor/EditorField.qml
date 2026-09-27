import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0
TextField {
    id: control
    implicitHeight: EditorTheme.controlHeight
    implicitWidth: 100
    color: enabled ? EditorTheme.text : EditorTheme.muted
    placeholderTextColor: EditorTheme.muted
    selectedTextColor: "white"
    selectionColor: EditorTheme.accent
    font.family: Theme.bodyFont
    font.pixelSize: EditorTheme.fontSize
    padding: 7
    selectByMouse: true
    background: Rectangle { radius: 4; color: EditorTheme.background; border.width: 1; border.color: control.activeFocus ? EditorTheme.accent : EditorTheme.border }
}
