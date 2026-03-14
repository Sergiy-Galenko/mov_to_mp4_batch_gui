import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: control
    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(92, contentItem.implicitWidth + 24)
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    hoverEnabled: true
    font.weight: Font.Medium
    opacity: enabled ? 1 : 0.72

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.down ? Theme.hover : control.hovered ? Theme.panelHover : Theme.panelAlt) : Theme.disabledBg
        border.width: 1
        border.color: control.enabled ? (control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border) : Theme.border
        scale: control.down ? 0.986 : control.hovered ? 1.008 : 1

        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on scale { NumberAnimation { duration: 120 } }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.text : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.Medium
        font.pixelSize: 13
        elide: Text.ElideRight
        clip: true
    }
}
