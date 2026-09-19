import QtQuick 2.15
import App 1.0

AppIconButton {
    id: button
    implicitWidth: 44
    implicitHeight: 44
    readonly property bool selected: highlighted || checked || prominent
    readonly property color activeColor: Theme.highContrastMode ? Theme.accent
        : Theme.lightMode ? "#245EB8" : "#7AB4FF"

    background: Rectangle {
        radius: 12
        color: !button.enabled ? Theme.disabledBg
            : button.selected ? (Theme.highContrastMode ? Theme.selectionBackground
                : Qt.rgba(button.activeColor.r, button.activeColor.g, button.activeColor.b, button.down ? 0.26 : 0.16))
            : button.down ? Theme.overlayPressed
            : button.hovered ? Theme.panelHover : Theme.panelSecondary
        border.width: Theme.highContrastMode ? 2 : 1
        border.color: !button.enabled ? Theme.borderMuted
            : button.selected ? button.activeColor
            : button.hovered ? Theme.textDisabled : Theme.borderDefault
        Behavior on color { enabled: !Theme.reducedMotion; ColorAnimation { duration: 100 } }
        Behavior on border.color { enabled: !Theme.reducedMotion; ColorAnimation { duration: 100 } }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: 14
            color: "transparent"
            border.width: 2
            border.color: button.activeColor
            visible: button.enabled && button.visualFocus
        }
    }

    contentItem: Item {
        AppIcon {
            anchors.centerIn: parent
            width: 20
            height: 20
            strokeWidth: 2.1
            name: button.iconName
            iconColor: !button.enabled ? Theme.textDisabled
                : button.selected ? button.activeColor : Theme.textPrimary
        }
    }
}
