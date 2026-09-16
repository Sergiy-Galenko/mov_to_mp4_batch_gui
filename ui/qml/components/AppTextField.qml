import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

TextField {
    id: control
    property bool invalid: false
    property bool search: false
    font.pixelSize: Theme.fontSizeSm
    color: Theme.text
    implicitHeight: Theme.inputHeight
    leftPadding: search ? 30 : 10
    rightPadding: 10
    topPadding: 0
    bottomPadding: 0
    Layout.fillWidth: true
    placeholderTextColor: Theme.subtleText
    selectionColor: Theme.accent
    selectedTextColor: Theme.textOnAccent
    verticalAlignment: TextInput.AlignVCenter
    selectByMouse: true
    Accessible.name: placeholderText
    clip: true
    hoverEnabled: true

    background: Rectangle {
        radius: control.search && Theme.isMac ? height / 2 : Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.inputHover : Theme.input) : Theme.disabledBg
        border.width: 1
        border.color: control.invalid ? Theme.danger : control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color { ColorAnimation { duration: 120 } }

        AppIcon {
            visible: control.search
            name: "search"
            width: 16; height: 16
            anchors.left: parent.left; anchors.leftMargin: 9
            anchors.verticalCenter: parent.verticalCenter
            iconColor: Theme.textSecondary
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: parent.radius + 2
            color: "transparent"
            border.width: 2
            border.color: Theme.focusRing
            visible: control.activeFocus
            opacity: 0.65
        }
    }
}
