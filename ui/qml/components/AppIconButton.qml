import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Button {
    id: control
    property string iconName: "more"
    property string accessibleLabel: ""
    property bool prominent: false
    implicitWidth: 34
    implicitHeight: 34
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: accessibleLabel
    ToolTip.visible: hovered && accessibleLabel.length > 0
    ToolTip.delay: 650
    ToolTip.text: accessibleLabel

    background: Rectangle {
        radius: Theme.radiusSm
        color: !control.enabled ? Theme.transparent : control.down ? Theme.overlayPressed : control.hovered ? Theme.overlayHover : Theme.transparent
        border.width: control.activeFocus ? 2 : (control.prominent ? 1 : 0)
        border.color: control.activeFocus ? Theme.focusRing : Theme.borderDefault
    }

    contentItem: AppIcon {
        name: control.iconName
        iconColor: !control.enabled ? Theme.textDisabled : control.hovered ? Theme.textPrimary : Theme.textSecondary
        anchors.centerIn: parent
        width: 18
        height: 18
    }
}
