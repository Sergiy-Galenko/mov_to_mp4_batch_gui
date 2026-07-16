import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

ProgressBar {
    id: control
    from: 0
    to: 1
    implicitHeight: 6
    background: Rectangle {
        implicitHeight: 6
        radius: 3
        color: Theme.progressTrack
    }
    contentItem: Item {
        implicitHeight: 6
        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 3
            color: Theme.accentPrimary
            Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        }
    }
}
