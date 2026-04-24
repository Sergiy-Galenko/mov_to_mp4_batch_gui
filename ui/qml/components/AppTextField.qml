import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

TextField {
    id: control
    property bool invalid: false
    font.pixelSize: 13
    color: Theme.text
    padding: 13
    implicitHeight: Theme.inputHeight
    Layout.fillWidth: true
    placeholderTextColor: Theme.subtleText
    selectionColor: Theme.accent
    selectedTextColor: "#FFFFFF"
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.inputHover : Theme.input) : Theme.disabledBg
        border.width: 1
        border.color: control.invalid ? Theme.danger : control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color { ColorAnimation { duration: 120 } }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: Qt.rgba(1, 1, 1, 0.06)
        }
    }
}
