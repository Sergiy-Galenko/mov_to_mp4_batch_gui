import QtQuick 2.15
import App 1.0

Item {
    id: root
    property color dotColor: Theme.accentSuccess
    property bool running: true

    width: 14
    height: 14

    Rectangle {
        id: halo
        anchors.centerIn: parent
        width: 8
        height: 8
        radius: 4
        color: root.dotColor
        opacity: 0.45
    }

    Rectangle {
        id: dot
        anchors.centerIn: parent
        width: 8
        height: 8
        radius: 4
        color: root.dotColor
    }

    SequentialAnimation {
        running: root.running
        loops: Animation.Infinite
        ParallelAnimation {
            NumberAnimation { target: halo; property: "scale"; from: 1.0; to: 1.35; duration: 700; easing.type: Easing.OutCubic }
            NumberAnimation { target: halo; property: "opacity"; from: 0.7; to: 0.18; duration: 700; easing.type: Easing.OutCubic }
        }
        ParallelAnimation {
            NumberAnimation { target: halo; property: "scale"; from: 1.35; to: 1.0; duration: 700; easing.type: Easing.InCubic }
            NumberAnimation { target: halo; property: "opacity"; from: 0.18; to: 0.7; duration: 700; easing.type: Easing.InCubic }
        }
    }
}
