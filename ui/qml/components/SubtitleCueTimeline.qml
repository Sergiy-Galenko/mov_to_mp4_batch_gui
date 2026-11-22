import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ColumnLayout {
    id: root
    property var cues: []
    property var scenes: []
    property var selectedCue: ({start: 0, end: 0})
    property real duration: 1
    property real position: 0
    property real pixelsPerSecond: 30
    signal seekRequested(real seconds)
    signal rangeChanged(real start, real end)
    signal editingStarted()
    signal editingFinished()
    Layout.minimumHeight: 105
    onCuesChanged: drawing.requestPaint()
    onScenesChanged: drawing.requestPaint()
    onSelectedCueChanged: drawing.requestPaint()
    RowLayout {
        Label { text: I18n.t("studio.timing"); color: Theme.textSecondary }
        Slider { Layout.fillWidth: true; from: 4; to: 160; value: root.pixelsPerSecond; onMoved: root.pixelsPerSecond = value }
        Label { text: root.position.toFixed(2) + " s"; color: Theme.textSecondary }
    }
    Flickable {
        id: track
        objectName: "subtitleTimeline"
        Layout.fillWidth: true; Layout.preferredHeight: 66
        clip: true
        contentWidth: Math.max(width, root.duration * root.pixelsPerSecond)
        contentHeight: height
        onContentXChanged: drawing.requestPaint()
        onContentWidthChanged: drawing.requestPaint()
        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
        Canvas {
            id: drawing
            x: track.contentX; width: track.width; height: track.height
            onWidthChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.fillStyle = Theme.panelSecondary
                ctx.fillRect(0, 0, width, height)
                var ratio = track.contentWidth / Math.max(root.duration, 0.001)
                for (var i = 0; i < root.cues.length; i++) {
                    var cue = root.cues[i]
                    var left = cue.start * ratio - track.contentX
                    var extent = Math.max(2, (cue.end - cue.start) * ratio)
                    if (left + extent < 0 || left > width) continue
                    ctx.fillStyle = cue.id === root.selectedCue.id ? Theme.accent : Theme.textMuted
                    ctx.fillRect(left, 12, extent, 25)
                }
                ctx.fillStyle = Theme.accentWarn
                for (var j = 0; j < root.scenes.length; j++) {
                    var point = root.scenes[j].start * ratio - track.contentX
                    if (point >= 0 && point < width) ctx.fillRect(point, 0, 2, 46)
                }
            }
            MouseArea {
                anchors.fill: parent
                onClicked: function(mouse) { root.seekRequested((mouse.x + track.contentX) / track.contentWidth * root.duration) }
            }
        }
        Rectangle { x: root.position / Math.max(root.duration, 0.001) * track.contentWidth; width: 2; height: 48; color: Theme.textPrimary }
        InOutMarker {
            objectName: "subtitleStartHandle"
            visible: !!root.selectedCue.id
            height: 46; trackWidth: track.contentWidth; totalDuration: root.duration
            timeValue: root.selectedCue.start || 0; maxBound: Math.max(0, root.selectedCue.end - 0.04)
            frameStep: 0.01
            onValueChangedByUser: function(value) { root.rangeChanged(value, root.selectedCue.end) }
            onEditingStarted: root.editingStarted()
            onEditingFinished: root.editingFinished()
        }
        InOutMarker {
            objectName: "subtitleEndHandle"
            visible: !!root.selectedCue.id
            height: 46; trackWidth: track.contentWidth; totalDuration: root.duration
            timeValue: root.selectedCue.end || 0; minBound: root.selectedCue.start + 0.04
            isOut: true; frameStep: 0.01
            onValueChangedByUser: function(value) { root.rangeChanged(root.selectedCue.start, value) }
            onEditingStarted: root.editingStarted()
            onEditingFinished: root.editingFinished()
        }
    }
}
