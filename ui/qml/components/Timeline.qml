import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Item {
    id: root

    property real duration: 0.0
    property real inPoint: 0.0
    property real outPoint: duration > 0 ? duration : 0.0
    property real playhead: 0.0
    property real fps: 30.0
    property real zoom: 1.0
    property string waveformSource: ""
    property bool hasAudio: false
    property var thumbnailStrip: []
    property int selectedMarker: 0 // 0 = none, 1 = In, 2 = Out

    signal inPointChangedByUser(real val)
    signal outPointChangedByUser(real val)
    signal playheadSeekRequested(real val)
    signal playPauseRequested()
    signal editingStarted()
    signal editingFinished()

    readonly property real frameStep: fps > 0 ? (1.0 / fps) : (1.0 / 30.0)
    readonly property real effectiveDuration: duration > 0 ? duration : 1.0

    function formatTimecode(seconds) {
        if (isNaN(seconds) || seconds < 0) seconds = 0
        var s = Math.floor(seconds)
        var ms = Math.floor((seconds - s) * 1000)
        var hrs = Math.floor(s / 3600)
        var mins = Math.floor((s % 3600) / 60)
        var secs = s % 60
        var pad = function(n, z) {
            z = z || 2
            return ("00" + n).slice(-z)
        }
        return pad(hrs) + ":" + pad(mins) + ":" + pad(secs) + "." + ("00" + ms).slice(-3)
    }

    function setInToPlayhead() {
        var snapped = snap(playhead)
        var val = Math.min(snapped, outPoint)
        root.inPointChangedByUser(val)
    }

    function setOutToPlayhead() {
        var snapped = snap(playhead)
        var val = Math.max(snapped, inPoint)
        root.outPointChangedByUser(val)
    }

    function snap(val) {
        if (root.frameStep > 0) {
            val = Math.round(val / root.frameStep) * root.frameStep
        }
        return Math.max(0, Math.min(root.effectiveDuration, val))
    }

    focus: true

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_I) {
            setInToPlayhead()
            event.accepted = true
        } else if (event.key === Qt.Key_O) {
            setOutToPlayhead()
            event.accepted = true
        } else if (event.key === Qt.Key_Space) {
            root.playPauseRequested()
            event.accepted = true
        } else if (event.key === Qt.Key_Left) {
            var step = (event.modifiers & Qt.ShiftModifier) ? (root.frameStep * 10) : root.frameStep
            if (root.selectedMarker === 1) {
                root.inPointChangedByUser(Math.max(0, root.inPoint - step))
            } else if (root.selectedMarker === 2) {
                root.outPointChangedByUser(Math.max(root.inPoint, root.outPoint - step))
            } else {
                root.playheadSeekRequested(Math.max(0, root.playhead - step))
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Right) {
            var step2 = (event.modifiers & Qt.ShiftModifier) ? (root.frameStep * 10) : root.frameStep
            if (root.selectedMarker === 1) {
                root.inPointChangedByUser(Math.min(root.outPoint, root.inPoint + step2))
            } else if (root.selectedMarker === 2) {
                root.outPointChangedByUser(Math.min(root.effectiveDuration, root.outPoint + step2))
            } else {
                root.playheadSeekRequested(Math.min(root.effectiveDuration, root.playhead + step2))
            }
            event.accepted = true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        // Top Toolbar: Zoom controls & Readouts
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space3

            Label {
                text: "IN: " + formatTimecode(root.inPoint)
                color: Theme.accentPrimary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontSizeSm
                font.bold: true
            }

            Rectangle { width: 1; height: 14; color: Theme.borderDefault }

            Label {
                text: "OUT: " + formatTimecode(root.outPoint)
                color: Theme.accentSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontSizeSm
                font.bold: true
            }

            Rectangle { width: 1; height: 14; color: Theme.borderDefault }

            Label {
                text: "Ділянка: " + formatTimecode(Math.max(0, root.outPoint - root.inPoint))
                color: Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontSizeSm
            }

            Item { Layout.fillWidth: true }

            Label {
                text: "Zoom:"
                color: Theme.textMuted
                font.pixelSize: Theme.fontSizeXs
            }

            AppIconButton {
                iconName: "minus"
                accessibleLabel: "Zoom Out"
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                enabled: root.zoom > 1.0
                onClicked: root.zoom = Math.max(1.0, root.zoom - 0.5)
            }

            Slider {
                id: zoomSlider
                Layout.preferredWidth: 100
                from: 1.0
                to: 8.0
                value: root.zoom
                stepSize: 0.2
                onMoved: root.zoom = value
            }

            AppIconButton {
                iconName: "plus"
                accessibleLabel: "Zoom In"
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                enabled: root.zoom < 8.0
                onClicked: root.zoom = Math.min(8.0, root.zoom + 0.5)
            }
        }

        // Timeline Scroll Area
        ScrollView {
            id: timelineScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: root.zoom > 1.0 ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
            ScrollBar.vertical.policy: ScrollBar.AlwaysOff

            Item {
                id: trackContent
                width: Math.max(timelineScroll.width, timelineScroll.width * root.zoom)
                height: timelineScroll.height

                // 1. Time Ruler (Top Bar)
                Rectangle {
                    id: timeRuler
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 20
                    color: Theme.panelSecondary
                    border.width: 1
                    border.color: Theme.borderDefault

                    Canvas {
                        id: rulerCanvas
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            ctx.strokeStyle = Theme.borderDefault
                            ctx.fillStyle = Theme.textMuted
                            ctx.font = "9px " + Theme.monoFont

                            var dur = root.effectiveDuration
                            if (dur <= 0) return

                            var numDivisions = Math.max(4, Math.round(10 * root.zoom))
                            var interval = dur / numDivisions

                            for (var i = 0; i <= numDivisions; i++) {
                                var t = i * interval
                                var x = (t / dur) * width
                                ctx.beginPath()
                                ctx.moveTo(x, height - 6)
                                ctx.lineTo(x, height)
                                ctx.stroke()

                                if (i < numDivisions) {
                                    var mins = Math.floor(t / 60)
                                    var secs = Math.floor(t % 60)
                                    var label = (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs
                                    ctx.fillText(label, x + 3, height - 8)
                                }
                            }
                        }
                    }

                    Connections {
                        target: root
                        function onZoomChanged() { rulerCanvas.requestPaint() }
                        function onDurationChanged() { rulerCanvas.requestPaint() }
                        function onWidthChanged() { rulerCanvas.requestPaint() }
                    }
                }

                // 2. Video Track Area
                Rectangle {
                    id: videoTrack
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: timeRuler.bottom
                    anchors.topMargin: 2
                    height: root.hasAudio ? 36 : 48
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle
                    clip: true

                    // Filmstrip thumbnail strip if available
                    Row {
                        anchors.fill: parent
                        visible: root.thumbnailStrip && root.thumbnailStrip.length > 0
                        spacing: 1

                        Repeater {
                            model: root.thumbnailStrip
                            Image {
                                width: Math.max(48, trackContent.width / Math.max(1, root.thumbnailStrip.length))
                                height: videoTrack.height
                                fillMode: Image.PreserveAspectCrop
                                source: modelData ? ("file://" + modelData) : ""
                                asynchronous: true
                            }
                        }
                    }

                    // Fallback track pattern if thumbnails not yet generated
                    Row {
                        anchors.fill: parent
                        visible: !root.thumbnailStrip || root.thumbnailStrip.length === 0
                        spacing: 8
                        Repeater {
                            model: Math.max(1, Math.round(trackContent.width / 60))
                            Rectangle {
                                width: 52
                                height: videoTrack.height - 4
                                y: 2
                                radius: 2
                                color: Theme.panelSecondary
                                border.width: 1
                                border.color: Theme.borderMuted
                                AppIcon {
                                    anchors.centerIn: parent
                                    name: "film"
                                    iconColor: Theme.textMuted
                                    width: 16
                                    height: 16
                                }
                            }
                        }
                    }
                }

                // 3. Audio Waveform Track Area
                Rectangle {
                    id: audioTrack
                    visible: root.hasAudio
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: videoTrack.bottom
                    anchors.topMargin: 2
                    height: 36
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle
                    clip: true

                    Image {
                        id: waveformImage
                        anchors.fill: parent
                        source: root.waveformSource.length > 0 ? ("file://" + root.waveformSource) : ""
                        fillMode: Image.Stretch
                        asynchronous: true
                        smooth: true
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: waveformImage.status !== Image.Ready
                        text: I18n.t("waveform_loading")
                        color: Theme.textMuted
                        font.pixelSize: Theme.fontSizeXs
                    }
                }

                // 4. In/Out Active Highlighted Range
                Rectangle {
                    id: inOutSpan
                    anchors.top: timeRuler.bottom
                    anchors.bottom: root.hasAudio ? audioTrack.bottom : videoTrack.bottom
                    x: (root.inPoint / root.effectiveDuration) * trackContent.width
                    width: Math.max(2, ((root.outPoint - root.inPoint) / root.effectiveDuration) * trackContent.width)
                    color: Qt.rgba(Theme.accentPrimary.r, Theme.accentPrimary.g, Theme.accentPrimary.b, 0.22)
                    border.width: 1
                    border.color: Qt.rgba(Theme.accentPrimary.r, Theme.accentPrimary.g, Theme.accentPrimary.b, 0.6)
                    z: 5
                }

                // 5. In Marker
                InOutMarker {
                    onEditingStarted: root.editingStarted()
                    onEditingFinished: root.editingFinished()
                    id: inMarker
                    isOut: false
                    timeValue: root.inPoint
                    totalDuration: root.effectiveDuration
                    trackWidth: trackContent.width
                    frameStep: root.frameStep
                    minBound: 0.0
                    maxBound: root.outPoint
                    isSelected: root.selectedMarker === 1
                    anchors.top: timeRuler.top
                    anchors.bottom: root.hasAudio ? audioTrack.bottom : videoTrack.bottom
                    z: 20

                    onSelected: {
                        root.selectedMarker = 1
                        root.forceActiveFocus()
                    }
                    onValueChangedByUser: function(v) {
                        root.inPointChangedByUser(v)
                    }
                }

                // 6. Out Marker
                InOutMarker {
                    onEditingStarted: root.editingStarted()
                    onEditingFinished: root.editingFinished()
                    id: outMarker
                    isOut: true
                    timeValue: root.outPoint
                    totalDuration: root.effectiveDuration
                    trackWidth: trackContent.width
                    frameStep: root.frameStep
                    minBound: root.inPoint
                    maxBound: root.effectiveDuration
                    isSelected: root.selectedMarker === 2
                    anchors.top: timeRuler.top
                    anchors.bottom: root.hasAudio ? audioTrack.bottom : videoTrack.bottom
                    z: 20

                    onSelected: {
                        root.selectedMarker = 2
                        root.forceActiveFocus()
                    }
                    onValueChangedByUser: function(v) {
                        root.outPointChangedByUser(v)
                    }
                }

                // 7. Playhead
                Item {
                    id: playheadItem
                    anchors.top: timeRuler.top
                    anchors.bottom: root.hasAudio ? audioTrack.bottom : videoTrack.bottom
                    width: 12
                    x: Math.round((root.playhead / root.effectiveDuration) * trackContent.width) - 6
                    z: 30

                    Rectangle {
                        id: playheadHead
                        width: 12
                        height: 12
                        anchors.top: parent.top
                        color: Theme.accentWarn
                        radius: 2
                    }

                    Rectangle {
                        anchors.top: playheadHead.bottom
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 2
                        color: Theme.accentWarn
                    }
                }

                // Click / Scrub across track to seek playhead
                MouseArea {
                    id: trackScrubArea
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: root.hasAudio ? audioTrack.bottom : videoTrack.bottom
                    z: 1 // below markers and playhead
                    cursorShape: Qt.PointingHandCursor

                    function updatePlayhead(mouseX) {
                        if (trackContent.width > 0 && root.effectiveDuration > 0) {
                            var ratio = Math.max(0, Math.min(1, mouseX / trackContent.width))
                            var target = root.snap(ratio * root.effectiveDuration)
                            root.playheadSeekRequested(target)
                        }
                    }

                    onPressed: function(mouse) {
                        root.selectedMarker = 0
                        root.forceActiveFocus()
                        updatePlayhead(mouse.x)
                    }

                    onPositionChanged: function(mouse) {
                        if (pressed) updatePlayhead(mouse.x)
                    }
                }
            }
        }
    }
}

