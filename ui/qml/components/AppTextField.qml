import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

TextField {
    id: control
    font.pixelSize: 13
    color: Theme.text
    padding: 10
    implicitHeight: 36
    Layout.fillWidth: true
    placeholderTextColor: Theme.muted
    selectionColor: Theme.accent
    selectedTextColor: "#FFFFFF"

    background: Rectangle {
        radius: 10
        color: control.enabled ? Theme.input : Theme.disabledBg
        border.color: Theme.border
    }
}
