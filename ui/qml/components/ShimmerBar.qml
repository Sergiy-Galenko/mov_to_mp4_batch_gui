import QtQuick 2.15
import App 1.0

Item {
    id: root
    property real value: 0
    property bool active: false
    property bool highLoadMode: false
    property real shimmerPhase: 0
    property color fillColor: Theme.accentPrimary
    property color trackColor: "#0F131B"

    implicitHeight: 10
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.trackColor
        border.width: 1
        border.color: Theme.bgBorder
    }

    Rectangle {
        id: fill
        x: 0
        y: 0
        width: Math.max(height, parent.width * Math.max(0, Math.min(root.value, 1)))
        height: parent.height
        radius: height / 2
        color: root.fillColor
        opacity: root.enabled ? 1 : 0.7

        Behavior on width {
            enabled: !root.highLoadMode
            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
        }
    }

    Rectangle {
        id: shimmer
        visible: root.active && !root.highLoadMode && fill.width > 12
        x: -width + (fill.width + width * 2) * root.shimmerPhase
        y: 0
        width: Math.max(48, root.width * 0.34)
        height: parent.height
        radius: height / 2
        clip: true
        opacity: 0.9
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.0) }
            GradientStop { position: 0.5; color: Qt.rgba(1, 1, 1, 0.08) }
            GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.0) }
        }
    }
}
