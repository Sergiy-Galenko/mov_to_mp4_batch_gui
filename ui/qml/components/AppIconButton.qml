import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Button {
    id: iconButton
    property string iconName: "more"
    property string accessibleLabel: ""
    property bool prominent: false
    implicitWidth: Theme.buttonHeight
    implicitHeight: Theme.buttonHeight
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: accessibleLabel
    ToolTip.visible: hovered && accessibleLabel.length > 0
    ToolTip.delay: 650
    ToolTip.text: accessibleLabel

    background: ButtonSurface { control: iconButton; variant: iconButton.prominent || iconButton.checked ? "secondary" : "ghost" }

    contentItem: AppIcon {
        name: iconButton.iconName
        iconColor: !iconButton.enabled ? Theme.textDisabled : iconButton.hovered || iconButton.checked ? Theme.textPrimary : Theme.textSecondary
        anchors.centerIn: parent
        width: 18
        height: 18
    }
}
