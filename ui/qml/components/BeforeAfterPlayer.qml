import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import App 1.0

ColumnLayout {
    id: root
    property url beforeSource
    property url afterSource
    property real split: 0.5
    property bool muted: false
    readonly property bool ready: before.hasVideo && after.hasVideo
    readonly property real driftMs: Math.abs(before.position - after.position)
    function stop() { before.pause(); after.pause(); seek(0) }
    function seek(ms) { before.position = ms; after.position = ms }
    function togglePlayback() {
        if (after.playbackState === MediaPlayer.PlayingState) { before.pause(); after.pause() }
        else { before.position = after.position; before.play(); after.play() }
    }
    onVisibleChanged: if (!visible) stop()
    MediaPlayer {
        id: before
        objectName: "comparisonBeforePlayer"
        source: root.beforeSource
        videoOutput: beforeOutput
        audioOutput: AudioOutput { muted: true }
        onMediaStatusChanged: if (mediaStatus === MediaPlayer.LoadedMedia) pause()
    }
    MediaPlayer {
        id: after
        objectName: "comparisonAfterPlayer"
        source: root.afterSource
        videoOutput: afterOutput
        audioOutput: AudioOutput { muted: root.muted }
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.LoadedMedia) pause()
            else if (mediaStatus === MediaPlayer.EndOfMedia) root.stop()
        }
    }
    Timer {
        interval: 80; repeat: true
        running: root.visible && after.playbackState === MediaPlayer.PlayingState
        onTriggered: {
            if (root.driftMs > 80) before.position = after.position
            if (before.playbackState !== MediaPlayer.PlayingState) before.play()
        }
    }
    Rectangle {
        id: view
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.minimumHeight: 180
        color: "#101010"
        VideoOutput { id: beforeOutput; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
        Item {
            id: afterMask
            x: view.width * root.split
            width: view.width - x; height: view.height; clip: true
            VideoOutput { id: afterOutput; x: -afterMask.x; width: view.width; height: view.height; fillMode: VideoOutput.PreserveAspectFit }
        }
        Label { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 12; text: I18n.t("studio.before"); color: "white" }
        Label { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12; text: I18n.t("studio.after"); color: "white" }
        Rectangle {
            objectName: "comparisonDivider"
            x: view.width * root.split - 1; width: 2; height: parent.height
            color: "white"
            Rectangle {
                anchors.centerIn: parent; width: 30; height: 42; radius: 12
                color: Theme.panelBackground; border.color: "white"
                Label { anchors.centerIn: parent; text: "↔"; color: "white" }
            }
            MouseArea {
                anchors.fill: parent; anchors.leftMargin: -15; anchors.rightMargin: -15
                cursorShape: Qt.SizeHorCursor
                preventStealing: true
                onPositionChanged: function(mouse) {
                    if (pressed) root.split = Math.max(0.02, Math.min(0.98, mapToItem(view, mouse.x, mouse.y).x / view.width))
                }
            }
        }
    }
    RowLayout {
        AppButton {
            text: after.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
            Accessible.name: I18n.t("studio.play")
            enabled: root.ready
            onClicked: root.togglePlayback()
        }
        Slider {
            Layout.fillWidth: true; from: 0; to: Math.max(1, after.duration)
            value: after.position; enabled: root.ready
            onMoved: root.seek(value)
            Accessible.name: I18n.t("studio.seek")
        }
        Label { text: (after.position / 1000).toFixed(1) + " / " + (after.duration / 1000).toFixed(1) + " s"; color: Theme.textSecondary }
    }
    Label {
        Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.accentWarn
        text: before.errorString || after.errorString
        visible: text.length > 0
    }
}
