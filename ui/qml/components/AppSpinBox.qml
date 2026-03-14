import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

SpinBox {
    id: control
    property int stepperWidth: 34

    font.pixelSize: 13
    implicitHeight: Theme.inputHeight
    leftPadding: 13
    rightPadding: stepperWidth + 12
    editable: true
    Layout.fillWidth: true
    hoverEnabled: true

    contentItem: TextInput {
        id: input
        text: ""
        color: control.enabled ? Theme.text : Theme.disabledText
        selectionColor: Theme.accent
        selectedTextColor: "#FFFFFF"
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        readOnly: !control.editable
        selectByMouse: true
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        validator: control.validator
        leftPadding: 0
        rightPadding: control.stepperWidth + 4

        onEditingFinished: control.value = control.valueFromText(text, control.locale)

        Binding {
            target: input
            property: "text"
            value: control.textFromValue(control.value, control.locale)
            when: !input.activeFocus
        }
    }

    up.indicator: Rectangle {
        x: control.width - width - 6
        y: 6
        width: control.stepperWidth
        height: Math.floor((control.availableHeight - 8) / 2)
        radius: 9
        color: control.up.pressed ? Theme.hover : control.up.hovered ? Theme.panelHover : Theme.panelAlt
        border.width: 1
        border.color: control.up.hovered ? Theme.borderStrong : Theme.border

        Label {
            anchors.centerIn: parent
            text: "+"
            color: Theme.text
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
    }

    down.indicator: Rectangle {
        x: control.width - width - 6
        y: control.height - height - 6
        width: control.stepperWidth
        height: Math.floor((control.availableHeight - 8) / 2)
        radius: 9
        color: control.down.pressed ? Theme.hover : control.down.hovered ? Theme.panelHover : Theme.panelAlt
        border.width: 1
        border.color: control.down.hovered ? Theme.borderStrong : Theme.border

        Label {
            anchors.centerIn: parent
            text: "-"
            color: Theme.text
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
    }

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.inputHover : Theme.input) : Theme.disabledBg
        border.width: 1
        border.color: control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
