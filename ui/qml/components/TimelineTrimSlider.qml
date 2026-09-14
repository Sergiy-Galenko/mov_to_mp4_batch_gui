import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Item {
    id: root
    implicitWidth: 280
    implicitHeight: 52

    property real totalDuration: 0.0
    property real trimStart: 0.0
    property real trimEnd: 0.0

    signal trimModified(real start, real end)

    readonly property real effectiveEnd: trimEnd > 0 && trimEnd <= totalDuration ? trimEnd : totalDuration
    readonly property real effectiveDuration: totalDuration > 0 ? totalDuration : 100.0

    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) seconds = 0
        var s = Math.floor(seconds)
        var hrs = Math.floor(s / 3600)
        var mins = Math.floor((s % 3600) / 60)
        var secs = s % 60
        if (hrs > 0) {
            return (hrs < 10 ? "0" : "") + hrs + ":" + (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs
        }
        return (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        // Time labels above timeline
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "In: " + formatTime(root.trimStart)
                color: Theme.accentPrimary
                font.pixelSize: Theme.fontMeta
                font.family: Theme.monoFont
                font.weight: Font.DemiBold
            }
            Item { Layout.fillWidth: true }
            Label {
                text: "Тривалість: " + formatTime(Math.max(0, root.effectiveEnd - root.trimStart))
                color: Theme.textMuted
                font.pixelSize: Theme.fontMeta
                font.family: Theme.monoFont
            }
            Item { Layout.fillWidth: true }
            Label {
                text: "Out: " + formatTime(root.effectiveEnd)
                color: Theme.accentPrimary
                font.pixelSize: Theme.fontMeta
                font.family: Theme.monoFont
                font.weight: Font.DemiBold
            }
        }

        // Interactive Timeline Track
        Item {
            id: trackContainer
            Layout.fillWidth: true
            Layout.preferredHeight: 28

            readonly property real handleWidth: 14
            readonly property real availableTrackWidth: Math.max(1, width - handleWidth)

            // Base track bar
            Rectangle {
                id: baseTrack
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                height: 8
                radius: 4
                color: Theme.panelSecondary
                border.width: 1
                border.color: Theme.borderMuted
            }

            // Active selected span
            Rectangle {
                id: activeSpan
                anchors.verticalCenter: parent.verticalCenter
                height: 8
                x: leftHandle.x + (leftHandle.width / 2)
                width: Math.max(0, (rightHandle.x + (rightHandle.width / 2)) - x)
                radius: 3
                color: Theme.accentPrimary
                opacity: 0.85
            }

            // In Handle (Start point)
            Rectangle {
                id: leftHandle
                width: 14
                height: 24
                radius: 3
                color: inDragArea.containsPress ? Theme.accentPressed : (inDragArea.containsMouse ? Theme.accentHover : Theme.accent)
                border.width: 1
                border.color: Theme.accentPrimary
                anchors.verticalCenter: parent.verticalCenter
                x: Math.min(
                    Math.max(0, (root.trimStart / root.effectiveDuration) * trackContainer.availableTrackWidth),
                    Math.max(0, (root.effectiveEnd / root.effectiveDuration) * trackContainer.availableTrackWidth - width)
                )

                // Grip lines inside handle
                Column {
                    anchors.centerIn: parent
                    spacing: 2
                    Repeater {
                        model: 3
                        Rectangle { width: 6; height: 1; color: Theme.textOnAccent }
                    }
                }

                MouseArea {
                    id: inDragArea
                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    cursorShape: Qt.SizeHorCursor
                    drag.target: leftHandle
                    drag.axis: Drag.XAxis
                    drag.minimumX: 0
                    drag.maximumX: rightHandle.x - leftHandle.width

                    onPositionChanged: {
                        if (drag.active) {
                            var pct = leftHandle.x / trackContainer.availableTrackWidth
                            var newStart = Math.max(0, Math.round(pct * root.effectiveDuration))
                            root.trimStart = newStart
                            root.trimModified(newStart, root.trimEnd)
                        }
                    }
                }
            }

            // Out Handle (End point)
            Rectangle {
                id: rightHandle
                width: 14
                height: 24
                radius: 3
                color: outDragArea.containsPress ? Theme.accentPressed : (outDragArea.containsMouse ? Theme.accentHover : Theme.accent)
                border.width: 1
                border.color: Theme.accentPrimary
                anchors.verticalCenter: parent.verticalCenter
                x: Math.max(
                    leftHandle.x + leftHandle.width,
                    Math.min(
                        trackContainer.availableTrackWidth,
                        (root.effectiveEnd / root.effectiveDuration) * trackContainer.availableTrackWidth
                    )
                )

                // Grip lines inside handle
                Column {
                    anchors.centerIn: parent
                    spacing: 2
                    Repeater {
                        model: 3
                        Rectangle { width: 6; height: 1; color: Theme.textOnAccent }
                    }
                }

                MouseArea {
                    id: outDragArea
                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    cursorShape: Qt.SizeHorCursor
                    drag.target: rightHandle
                    drag.axis: Drag.XAxis
                    drag.minimumX: leftHandle.x + leftHandle.width
                    drag.maximumX: trackContainer.availableTrackWidth

                    onPositionChanged: {
                        if (drag.active) {
                            var pct = rightHandle.x / trackContainer.availableTrackWidth
                            var newEnd = Math.round(pct * root.effectiveDuration)
                            root.trimEnd = newEnd
                            root.trimModified(root.trimStart, newEnd)
                        }
                    }
                }
            }
        }
    }
}
