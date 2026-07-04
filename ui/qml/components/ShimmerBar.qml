import QtQuick 2.15
import App 1.0

Item {
    id: root
    property real value: 0
    property bool active: false
    property bool highLoadMode: false
    property real shimmerPhase: 0
    property color fillColor: Theme.accentPrimary
    property color trackColor: Theme.progressTrack

    implicitHeight: 10
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.trackColor
        border.width: 1
        border.color: Theme.borderSubtle
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
        id: marker
        visible: root.active && !root.highLoadMode && fill.width > 12
        x: Math.min(fill.width - width, Math.max(0, (fill.width - width) * root.shimmerPhase))
        y: 1
        width: Math.min(42, Math.max(12, fill.width * 0.22))
        height: parent.height - 2
        radius: height / 2
        clip: true
        color: Theme.progressHighlight
        opacity: 0.38
    }
}
