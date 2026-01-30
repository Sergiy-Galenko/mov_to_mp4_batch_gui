import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

SpinBox {
    id: control
    font.pixelSize: 13
    implicitHeight: 36
    leftPadding: 10
    rightPadding: 28
    Layout.fillWidth: true

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

        onEditingFinished: {
            control.value = control.valueFromText(text, control.locale)
        }

        Binding {
            target: input
            property: "text"
            value: control.textFromValue(control.value, control.locale)
            when: !input.activeFocus
        }
    }

    background: Rectangle {
        radius: 10
        color: control.enabled ? Theme.input : Theme.disabledBg
        border.color: Theme.border
    }
}
