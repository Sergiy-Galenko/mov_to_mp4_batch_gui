import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

CheckBox {
    id: control
    spacing: Theme.space1
    hoverEnabled: true
    implicitHeight: Math.max(26, label.implicitHeight + 4)
    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0

    indicator: Rectangle {
        x: 0
        y: Math.round((control.availableHeight - height) / 2)
        width: Theme.checkboxSize
        height: Theme.checkboxSize
        radius: 6
        color: control.checked ? Theme.accent : control.hovered ? Theme.inputHover : Theme.input
        border.width: 1
        border.color: control.checked ? Theme.accent2 : (control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border)

        Rectangle {
            width: 9
            height: 9
            radius: 2
            anchors.centerIn: parent
            color: "#FFFFFF"
            visible: control.checked
        }

        Behavior on color { ColorAnimation { duration: 120 } }
    }

    contentItem: Label {
        id: label
        text: control.text
        color: control.enabled ? Theme.text : Theme.disabledText
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing + 2
        rightPadding: 0
        topPadding: 0
        bottomPadding: 0
        font.pixelSize: 13
        wrapMode: Text.WordWrap
    }
}
