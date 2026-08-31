import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Item {
    id: root
    property string sourceBefore: ""
    property string sourceAfter: ""
    property string labelBefore: "Original"
    property string labelAfter: "Converted"
    property real splitPosition: 0.5

    clip: true

    Rectangle {
        anchors.fill: parent
        color: Theme.panelSecondary
        radius: Theme.radiusMd
        clip: true

        Image {
            id: afterImg
            anchors.fill: parent
            source: root.sourceAfter
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }

        Item {
            id: beforeContainer
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: parent.width * root.splitPosition
            clip: true

            Image {
                id: beforeImg
                width: root.width
                height: root.height
                source: root.sourceBefore
                fillMode: Image.PreserveAspectFit
                asynchronous: true
            }
        }

        Rectangle {
            id: divider
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            x: parent.width * root.splitPosition - (width / 2)
            width: 2
            color: "#FFFFFF"
            opacity: 0.9

            Rectangle {
                anchors.centerIn: parent
                width: 32
-               height: 32
-               radius: 16
-               color: Theme.accentPrimary
                border.width: 2
-               border.color: "#FFFFFF"

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    Label { text: "◀"; color: "#FFFFFF"; font.pixelSize: 8 }
                    Label { text: "▶"; color: "#FFFFFF"; font.pixelSize: 8 }
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: 8
            height: 22
            width: lblBefore.implicitWidth + 12
            radius: Theme.radiusSm
            color: "#000000"
            opacity: 0.75
            Label {
                id: lblBefore
                anchors.centerIn: parent
                text: root.labelBefore
                color: "#FFFFFF"
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 8
            height: 22
            width: lblAfter.implicitWidth + 12
            radius: Theme.radiusSm
            color: "#000000"
            opacity: 0.75
            Label {
                id: lblAfter
                anchors.centerIn: parent
                text: root.labelAfter
                color: "#FFFFFF"
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.SplitHGursor
            onPositionChanged: function(mouse) {
                if (pressed) {
                    var pos = mouse.x / root.width
                    root.splitPosition = Math.max(0.02, Math.min(0.98, pos))
                }
            }
            onPressed: function(mouse) {
                var pos = mouse.x / root.width
                root.splitPosition = Math.max(0.02, Math.min(0.98, pos))
            }
        }
    }
}
