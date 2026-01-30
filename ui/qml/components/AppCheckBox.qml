import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

CheckBox {
    id: control
    spacing: Theme.space1

    indicator: Rectangle {
        width: 16
        height: 16
        radius: 4
        color: control.checked ? Theme.accent : Theme.input
        border.color: Theme.border
        Rectangle {
            width: 8
            height: 8
            radius: 2
            anchors.centerIn: parent
            color: "#FFFFFF"
            visible: control.checked
        }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.text : Theme.disabledText
        verticalAlignment: Text.AlignVCenter
    }
}
