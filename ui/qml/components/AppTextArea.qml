import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

TextArea {
    id: control
    font.pixelSize: 13
    color: Theme.text
    padding: 12
    Layout.fillWidth: true
    selectionColor: Theme.accent
    selectedTextColor: "#FFFFFF"

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? Theme.input : Theme.disabledBg
        border.width: 1
        border.color: control.activeFocus ? Theme.borderStrong : Theme.border
    }
}
