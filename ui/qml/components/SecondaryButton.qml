import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: control
    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(88, contentItem.implicitWidth + 20)
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    hoverEnabled: true
    font.weight: Font.Medium

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.panelAlt : Theme.panel) : Theme.disabledBg
        border.width: 1
        border.color: control.enabled ? (control.hovered ? Theme.borderStrong : Theme.border) : Theme.border
        scale: control.down ? 0.99 : 1

        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on scale { NumberAnimation { duration: 120 } }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.text : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.Medium
        font.pixelSize: 12
        elide: Text.ElideRight
        clip: true
    }
}
