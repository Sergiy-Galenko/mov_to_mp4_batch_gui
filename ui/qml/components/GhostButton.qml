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
        radius: Theme.radiusSm
        color: control.enabled ? (control.down ? Theme.overlayPressed : control.hovered ? Theme.overlayHover : Theme.transparent) : Theme.transparent
        border.width: 1
        border.color: control.activeFocus ? Theme.focusRing : control.hovered ? Theme.border : Theme.transparent

        Behavior on color { ColorAnimation { duration: 120 } }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? (control.hovered ? Theme.text : Theme.muted) : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.Medium
        font.pixelSize: Theme.fontSizeSm
        elide: Text.ElideRight
        clip: true
    }
}
