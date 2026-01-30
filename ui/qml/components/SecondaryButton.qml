import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Button {
    id: control
    font.weight: Font.Medium
    background: Rectangle {
        radius: 10
        color: control.enabled ? (control.down ? Theme.hover : Theme.panel) : Theme.disabledBg
        border.color: Theme.border
    }
    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.text : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
