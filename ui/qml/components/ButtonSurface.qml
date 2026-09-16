import QtQuick 2.15
import App 1.0

Item {
    id: surface
    required property var control
    property string variant: "secondary"
    readonly property bool primary: variant === "primary"
    readonly property bool danger: variant === "danger"
    readonly property bool quiet: variant === "ghost" || variant === "toolbar"
    readonly property bool interactive: control && control.enabled
    readonly property bool pressed: interactive && control.down
    readonly property bool hovered: interactive && control.hovered
    readonly property bool selected: interactive && (control.checked || control.highlighted)
    readonly property color fillColor: !interactive ? (quiet ? Theme.transparent : Theme.disabledBg)
        : danger ? (pressed ? Qt.darker(Theme.dangerSoft, 1.12) : Theme.dangerSoft)
        : pressed ? (primary ? Theme.accentPressed : Theme.overlayPressed)
        : selected ? (primary ? Theme.accent : Theme.selectionBackground)
        : hovered ? (primary ? Theme.accentHover : Theme.panelHover)
        : primary ? Theme.accent : quiet ? Theme.transparent : Theme.panelSecondary

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 1
        anchors.bottomMargin: -1
        radius: Theme.radiusButton
        color: "#18000000"
        visible: Theme.isMac && surface.interactive && !surface.quiet && !surface.pressed
    }
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusButton
        color: surface.fillColor
        border.width: surface.quiet && !surface.selected ? 0 : 1
        border.color: !surface.interactive ? Theme.borderMuted : surface.primary ? Qt.lighter(Theme.accent, Theme.isMac ? 1.12 : 1.0)
            : surface.selected ? Theme.accent
            : Theme.lightMode ? Qt.darker(Theme.panelSecondary, 1.12) : Qt.lighter(Theme.panelSecondary, 1.18)
        Behavior on color { ColorAnimation { duration: 100 } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, Theme.radiusButton - 1)
            visible: Theme.isMac && surface.interactive && !surface.quiet && !surface.pressed
            gradient: Gradient {
                GradientStop { position: 0; color: "#0DFFFFFF" }
                GradientStop { position: 1; color: "#00FFFFFF" }
            }
        }
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.margins: 1
            height: 1
            color: "#26000000"
            visible: Theme.isWindows && !surface.quiet
        }
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: Theme.radiusButton + 3
        color: Theme.transparent
        border.width: Theme.isMac ? 3 : 2
        border.color: Theme.focusRing
        opacity: surface.interactive && surface.control.visualFocus ? 0.85 : 0
        Behavior on opacity { NumberAnimation { duration: 80 } }
    }
}
