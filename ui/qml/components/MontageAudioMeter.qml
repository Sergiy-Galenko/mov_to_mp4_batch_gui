import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property bool isPlaying: false
    property real masterVolume: 1.0
    property bool isMuted: false

    implicitWidth: 38
    implicitHeight: 220
    color: "#121214"
    radius: 4
    border.width: 1
    border.color: "#27272a"
    clip: true

    property real levelL: 0.0
    property real levelR: 0.0
    property real peakL: 0.0
    property real peakR: 0.0

    Timer {
        interval: 40
        running: root.isPlaying && !root.isMuted
        repeat: true
        onTriggered: {
            // Realistic dynamic VU meter animation while playing
            var base = 0.55 * root.masterVolume
            var jitterL = (Math.random() * 0.35) * root.masterVolume
            var jitterR = (Math.random() * 0.35) * root.masterVolume
            var targetL = Math.min(1.0, Math.max(0.05, base + jitterL))
            var targetR = Math.min(1.0, Math.max(0.05, base + jitterR))

            root.levelL = root.levelL * 0.4 + targetL * 0.6
            root.levelR = root.levelR * 0.4 + targetR * 0.6

            if (root.levelL > root.peakL) root.peakL = root.levelL
            else root.peakL = Math.max(0.0, root.peakL - 0.015)

            if (root.levelR > root.peakR) root.peakR = root.levelR
            else root.peakR = Math.max(0.0, root.peakR - 0.015)
        }
    }

    onIsPlayingChanged: {
        if (!isPlaying || isMuted) {
            decayTimer.start()
        }
    }

    Timer {
        id: decayTimer
        interval: 30
        repeat: true
        running: !root.isPlaying || root.isMuted
        onTriggered: {
            root.levelL = Math.max(0.0, root.levelL * 0.8 - 0.02)
            root.levelR = Math.max(0.0, root.levelR * 0.8 - 0.02)
            root.peakL = Math.max(0.0, root.peakL * 0.85 - 0.02)
            root.peakR = Math.max(0.0, root.peakR * 0.85 - 0.02)
            if (root.levelL <= 0.01 && root.levelR <= 0.01 && root.peakL <= 0.01 && root.peakR <= 0.01) {
                root.levelL = 0
                root.levelR = 0
                root.peakL = 0
                root.peakR = 0
                decayTimer.stop()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2

        // dB Scale labels
        Column {
            Layout.preferredWidth: 14
            Layout.fillHeight: true
            spacing: (parent.height - 42) / 6

            Label { text: "0"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#ef4444" }
            Label { text: "-6"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#eab308" }
            Label { text: "-12"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#eab308" }
            Label { text: "-18"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#22c55e" }
            Label { text: "-24"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#22c55e" }
            Label { text: "-36"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#71717a" }
            Label { text: "-48"; font.pixelSize: 8; font.family: Theme.monoFont; color: "#52525b" }
        }

        // Left Channel Bar
        Rectangle {
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            color: "#18181b"
            radius: 2
            clip: true

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height * root.levelL
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#ef4444" }
                    GradientStop { position: 0.15; color: "#f97316" }
                    GradientStop { position: 0.35; color: "#eab308" }
                    GradientStop { position: 0.65; color: "#22c55e" }
                    GradientStop { position: 1.0; color: "#15803d" }
                }
            }

            // Peak Hold line
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Math.max(0, parent.height * root.peakL - 2)
                height: 2
                color: root.peakL > 0.85 ? "#ef4444" : root.peakL > 0.65 ? "#eab308" : "#22c55e"
                visible: root.peakL > 0.05
            }
        }

        // Right Channel Bar
        Rectangle {
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            color: "#18181b"
            radius: 2
            clip: true

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height * root.levelR
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#ef4444" }
                    GradientStop { position: 0.15; color: "#f97316" }
                    GradientStop { position: 0.35; color: "#eab308" }
                    GradientStop { position: 0.65; color: "#22c55e" }
                    GradientStop { position: 1.0; color: "#15803d" }
                }
            }

            // Peak Hold line
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Math.max(0, parent.height * root.peakR - 2)
                height: 2
                color: root.peakR > 0.85 ? "#ef4444" : root.peakR > 0.65 ? "#eab308" : "#22c55e"
                visible: root.peakR > 0.05
            }
        }
    }
}

