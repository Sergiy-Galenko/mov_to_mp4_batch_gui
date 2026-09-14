import QtQuick 2.15
import App 1.0

Item {
    id: surface
    required property var control
    property string variant: "secondary"
    readonly property bool primary: variant === "primary"
    readonly property bool quiet: variant === "ghost"
    readonly property bool interactive: control && control.enabled
    readonly property bool pressed: interactive && control.down
    readonly property bool hovered: interactive && control.hovered
    readonly property bool selected: interactive && (control.checked || control.highlighted)
    readonly property color fillColor: !interactive ? (quiet ? Theme.transparent : Theme.disabledBg)
        : pressed ? (primary ? Theme.accentPressed : Theme.overlayPressed)
        : selected ? (primary ? Theme.accent : Theme.selectionBackground)
        : hovered ? (primary ? Theme.accentHover : Theme.overlayHover)
        : primary ? Theme.accent : quiet ? Theme.transparent : Theme.panelSecondary

    scale: pressed ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 2
        anchors.bottomMargin: -2
        radius: Theme.radiusButton
        color: Theme.modalScrim
        opacity: surface.interactive && !surface.quiet && !surface.pressed ? 0.22 : 0
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusButton
        color: surface.fillColor
        border.width: 1
        border.color: !surface.interactive ? (surface.quiet ? Theme.transparent : Theme.borderMuted)
            : surface.primary ? Theme.accentHover
            : surface.hovered || surface.selected ? Theme.borderDefault
            : surface.quiet ? Theme.transparent : Theme.borderMuted
        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on border.color { ColorAnimation { duration: 120 } }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, Theme.radiusButton - 1)
            visible: surface.interactive && !surface.quiet && !surface.pressed
            gradient: Gradient {
                GradientStop { position: 0; color: Qt.rgba(Theme.textPrimary.r, Theme.textPrimary.g, Theme.textPrimary.b, 0.06) }
                GradientStop { position: 0.6; color: Theme.transparent }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: Theme.radiusButton + 3
        color: Theme.transparent
        border.width: 2
        border.color: Theme.focusRing
        opacity: surface.interactive && surface.control.visualFocus ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 80 } }
    }
}
