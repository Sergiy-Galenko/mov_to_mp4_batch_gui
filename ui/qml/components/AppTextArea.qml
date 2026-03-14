import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

TextArea {
    id: control
    font.pixelSize: 13
    color: Theme.text
    padding: 13
    Layout.fillWidth: true
    selectionColor: Theme.accent
    selectedTextColor: "#FFFFFF"
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.inputHover : Theme.input) : Theme.disabledBg
        border.width: 1
        border.color: control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
