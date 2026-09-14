import QtQuick 2.15
import App 1.0

Rectangle {
    implicitWidth: 32
    implicitHeight: 32
    radius: Math.min(width, height) * 0.2
    color: Theme.accent
    AppIcon {
        anchors.centerIn: parent
        width: parent.width * 0.68
        height: parent.height * 0.68
        name: "film"
        iconColor: Theme.textOnAccent
    }
}
