import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: button
    property string variant: "secondary"
    property string iconName: ""
    property int iconSize: Theme.isMac ? 15 : 16
    readonly property color foregroundColor: !enabled ? Theme.textDisabled
        : variant === "danger" ? Theme.statusError
        : variant === "primary" ? Theme.textOnAccent
        : variant === "ghost" && !hovered && !checked && !highlighted ? Theme.textSecondary : Theme.textPrimary

    implicitHeight: Math.max(Theme.buttonHeight, contentItem.implicitHeight + (Theme.isMac ? 10 : 12))
    implicitWidth: Math.max(64, contentItem.implicitWidth + leftPadding + rightPadding)
    leftPadding: 12
    rightPadding: 12
    topPadding: 5
    bottomPadding: 5
    Layout.minimumWidth: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.family: Theme.bodyFont
    font.pixelSize: Theme.fontSizeSm
    font.weight: variant === "primary" ? Font.DemiBold : Font.Normal
    Accessible.name: text
    ToolTip.visible: hovered && text.length > 0 && contentItem.implicitWidth > availableWidth
    ToolTip.delay: 650
    ToolTip.text: text

    background: ButtonSurface { control: button; variant: button.variant }

    contentItem: Item {
        implicitWidth: buttonLabel.implicitWidth + (buttonIcon.visible ? button.iconSize + 8 : 0)
        implicitHeight: Math.max(buttonLabel.implicitHeight, buttonIcon.visible ? button.iconSize : 0)
        Row {
            id: contentRow
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.implicitWidth)
            height: parent.height
            spacing: 8
            transform: Translate { y: !Theme.isMac && button.down ? 1 : 0 }
            AppIcon {
                id: buttonIcon
                name: button.iconName
                visible: button.iconName.length > 0
                width: button.iconSize
                height: button.iconSize
                anchors.verticalCenter: parent.verticalCenter
                iconColor: button.foregroundColor
            }
            Label {
                id: buttonLabel
                text: button.text
                width: Math.max(0, contentRow.width - (buttonIcon.visible ? button.iconSize + contentRow.spacing : 0))
                height: parent.height
                font: button.font
                color: button.foregroundColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                clip: true
            }
        }
    }
}
