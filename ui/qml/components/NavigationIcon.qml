import QtQuick 2.15
import App 1.0

Rectangle {
    id: root
    property string name: "settings"
    property color tint: Theme.accent
    property int glyphSize: 18
    implicitWidth: 28
    implicitHeight: 28
    radius: Theme.isMac ? 7 : 5
    color: tint
    border.width: Theme.isMac ? 1 : 0
    border.color: Qt.lighter(tint, 1.15)
    gradient: Gradient {
        GradientStop { position: 0; color: Qt.lighter(root.tint, 1.12) }
        GradientStop { position: 1; color: root.tint }
    }
    AppIcon {
        anchors.centerIn: parent
        width: root.glyphSize; height: root.glyphSize
        name: root.name
        iconColor: "white"
        strokeWidth: 1.75
    }
}
