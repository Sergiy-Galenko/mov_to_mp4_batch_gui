import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: control
    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(80, contentItem.implicitWidth + 20)
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    hoverEnabled: true
    font.weight: Font.Medium
    opacity: enabled ? 1 : 0.68

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.down ? Qt.rgba(1, 1, 1, 0.09) : control.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent") : "transparent"
        border.width: 1
        border.color: control.activeFocus ? Theme.focusRing : control.hovered ? Theme.border : "transparent"
        scale: control.down ? 0.988 : control.hovered ? 1.006 : 1

        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on scale { NumberAnimation { duration: 120 } }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? (control.hovered ? Theme.text : Theme.muted) : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.Medium
        font.pixelSize: 13
        elide: Text.ElideRight
        clip: true
    }
}
