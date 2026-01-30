import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Button {
    id: control
    font.weight: Font.Medium
    background: Rectangle {
        radius: 10
        color: control.down ? Theme.hover : "transparent"
        border.color: "transparent"
    }
    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.accent : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
