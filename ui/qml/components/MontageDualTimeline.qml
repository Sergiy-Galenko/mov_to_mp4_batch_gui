import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root

    property real duration: 0.0
    property real inPoint: 0.0
    property real outPoint: duration > 0 ? duration : 0.0
    property real playhead: 0.0
    property real fps: 30.0
    property real zoom: 1.0
    property string waveformSource: ""
    property bool hasAudio: true

    property var timelineClips: []
    property string bgMusicPath: ""
    property real bgMusicVolume: 0.8
    property bool bgMusicDucking: true
    property string defaultTransition: "fade"
    property real defaultTransitionDuration: 1.0

    property int activeTool: 0 // 0: Select, 1: Blade/Cut, 2: Trim
    property bool snappingEnabled: true

    // Track states
    property bool v2Visible: true
    property bool v2Locked: false
    property bool v1Visible: true
    property bool v1Locked: false
    property bool a1Muted: false
    property bool a1Locked: false
    property bool a2Muted: false
    property bool a2Locked: false

    signal inPointChangedByUser(real val)
    signal outPointChangedByUser(real val)
    signal playheadSeekRequested(real val)
    signal playPauseRequested()
    signal splitRequested(real time)
    signal editingStarted()
    signal editingFinished()

    readonly property real effectiveDuration: duration > 0 ? duration : 1.0
    readonly property real frameStep: fps > 0 ? (1.0 / fps) : (1.0 / 30.0)

    color: "#121214"
    radius: Theme.radiusMd
    border.width: 1
    border.color: "#27272a"
    clip: true

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

    function snap(val) {
        if (!snappingEnabled) return Math.max(0, Math.min(root.effectiveDuration, val))
        if (root.frameStep > 0) {
            val = Math.round(val / root.frameStep) * root.frameStep
        }
        // Magnetic snap to In or Out points within 5 frames
        var snapThresh = root.frameStep * 5
        if (Math.abs(val - root.inPoint) < snapThresh) val = root.inPoint
        if (Math.abs(val - root.outPoint) < snapThresh) val = root.outPoint
        return Math.max(0, Math.min(root.effectiveDuration, val))
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

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ==================== 1. UPPER OVERVIEW TIMELINE (DaVinci Mini-Map) ====================
        Rectangle {
            id: overviewBar
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: "#18181b"
            border.width: 1
            border.color: "#27272a"

            // Tracks Mini-blocks container
            Item {
                id: overviewContent
                anchors.fill: parent
                anchors.margins: 4

                // Background In/Out active range dimming
                Rectangle {
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    x: 0
                    width: parent.width * (root.inPoint / root.effectiveDuration)
                    color: "#66000000"
                }
                Rectangle {
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    x: parent.width * (root.outPoint / root.effectiveDuration)
                    width: parent.width - x
                    color: "#66000000"
                }

                // Mini V2 Titles Track
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: 2
                    height: 5
                    color: "transparent"
                    Rectangle {
                        x: parent.width * 0.1
                        width: parent.width * 0.25
                        height: parent.height
                        radius: 1
                        color: "#a855f7"
                    }
                    Rectangle {
                        x: parent.width * 0.6
                        width: parent.width * 0.2
                        height: parent.height
                        radius: 1
                        color: "#a855f7"
                    }
                }

                // Mini V1 Video Track
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: 9
                    height: 8
                    color: "transparent"

                    // Main clip block
                    Rectangle {
                        x: parent.width * (root.inPoint / root.effectiveDuration)
                        width: Math.max(4, parent.width * ((root.outPoint - root.inPoint) / root.effectiveDuration))
                        height: parent.height
                        radius: 2
                        color: "#3b82f6" // DaVinci Blue
                        border.width: 1
                        border.color: "#60a5fa"
                    }

                    // Additional timeline clips
                    Repeater {
                        model: root.timelineClips
                        Rectangle {
                            required property var modelData
                            required property int index
                            x: overviewContent.width * (0.4 + index * 0.18)
                            width: Math.max(4, overviewContent.width * 0.16)
                            height: parent.height
                            radius: 2
                            color: "#f97316"
                            border.width: 1
                            border.color: "#fb923c"
                        }
                    }
                }

                // Mini A1 Audio Track
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: 19
                    height: 5
                    color: "transparent"
                    Rectangle {
                        x: parent.width * (root.inPoint / root.effectiveDuration)
                        width: Math.max(4, parent.width * ((root.outPoint - root.inPoint) / root.effectiveDuration))
                        height: parent.height
                        radius: 1
                        color: "#10b981" // DaVinci Green
                    }
                }

                // Mini A2 Music Track
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    y: 26
                    height: 4
                    visible: !!root.bgMusicPath
                    color: "transparent"
                    Rectangle {
                        x: 0
                        width: parent.width
                        height: parent.height
                        radius: 1
                        color: "#06b6d4" // Cyan
                    }
                }

                // Overview Playhead (Red Scrubber Line)
                Rectangle {
                    id: overviewPlayhead
                    x: Math.max(0, Math.min(parent.width - 2, parent.width * (root.playhead / root.effectiveDuration) - 1))
                    width: 2
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    color: "#ef4444"
                    z: 10

                    // Top triangular marker
                    Rectangle {
                        width: 8; height: 6
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        color: "#ef4444"
                        rotation: 45
                    }
                }

                // Overview scrub mouse area
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.LeftButton
                    onPressed: function(mouse) {
                        root.editingStarted()
                        var ratio = Math.max(0.0, Math.min(1.0, mouse.x / width))
                        root.playheadSeekRequested(root.snap(ratio * root.effectiveDuration))
                    }
                    onPositionChanged: function(mouse) {
                        var ratio = Math.max(0.0, Math.min(1.0, mouse.x / width))
                        root.playheadSeekRequested(root.snap(ratio * root.effectiveDuration))
                    }
                    onReleased: root.editingFinished()
                }
            }
        }

        // ==================== 2. TIMELINE ACTION TOOLBAR ====================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: "#18181b"
            border.width: 1
            border.color: "#27272a"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                // Selection Tool
                AppIconButton {
                    iconName: "navigationForward"
                    accessibleLabel: "Інструмент вибору (Selection Tool)"
                    Layout.preferredWidth: 26; Layout.preferredHeight: 26
                    prominent: root.activeTool === 0
                    onClicked: root.activeTool = 0
                }

                // Blade / Split Tool
                AppIconButton {
                    iconName: "crop"
                    accessibleLabel: "Лезо / Розрізання (Blade Tool)"
                    Layout.preferredWidth: 26; Layout.preferredHeight: 26
                    prominent: root.activeTool === 1
                    onClicked: {
                        root.activeTool = 1
                        root.splitRequested(root.playhead)
                    }
                }

                // Snapping Magnet Tool
                AppIconButton {
                    iconName: "sliders"
                    accessibleLabel: "Прив'язка до кадрів (Snapping Magnet)"
                    Layout.preferredWidth: 26; Layout.preferredHeight: 26
                    prominent: root.snappingEnabled
                    onClicked: root.snappingEnabled = !root.snappingEnabled
                }

                Rectangle { width: 1; height: 16; color: "#3f3f46" }

                // In / Out Marker Buttons
                AppButton {
                    text: "[ In ]"
                    Layout.preferredHeight: 24
                    font.pixelSize: 11
                    onClicked: root.setInToPlayhead()
                }
                AppButton {
                    text: "[ Out ]"
                    Layout.preferredHeight: 24
                    font.pixelSize: 11
                    onClicked: root.setOutToPlayhead()
                }

                Rectangle { width: 1; height: 16; color: "#3f3f46" }

                // Quick Split Button
                AppButton {
                    text: "✂ Split"
                    Layout.preferredHeight: 24
                    font.pixelSize: 11
                    onClicked: root.splitRequested(root.playhead)
                }

                // Transition Picker Dropdown
                Label { text: "Перехід:"; font.pixelSize: 11; color: "#a1a1aa" }
                AppComboBox {
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 24
                    model: ["fade", "wipeleft", "dissolve", "circlecrop"]
                    currentIndex: Math.max(0, ["fade", "wipeleft", "dissolve", "circlecrop"].indexOf(root.defaultTransition))
                    onActivated: function(idx) { root.defaultTransition = model[idx] }
                }

                Item { Layout.fillWidth: true }

                // Zoom Slider
                Label { text: "Zoom:"; font.pixelSize: 10; color: "#71717a" }
                Slider {
                    id: zoomSlider
                    Layout.preferredWidth: 100
                    from: 1.0; to: 4.0; value: root.zoom
                    onMoved: root.zoom = value
                }
            }
        }

        // ==================== 3. DETAILED MULTI-TRACK TIMELINE ====================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Left Track Control Headers (DaVinci Track Headers)
            Rectangle {
                Layout.preferredWidth: 96
                Layout.fillHeight: true
                color: "#161618"
                border.width: 1
                border.color: "#27272a"
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 2

                    // Timecode Ruler spacer
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 22
                        color: "#1e1e22"
                        Label {
                            anchors.centerIn: parent
                            text: "TRACKS"
                            font.pixelSize: 9
                            font.bold: true
                            color: "#71717a"
                        }
                    }

                    // V2 Header (Titles)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        color: "#1a1a1d"
                        border.width: 1
                        border.color: "#27272a"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 4
                            Rectangle { width: 3; height: 16; color: "#a855f7"; radius: 1 }
                            Label { text: "V2 Titles"; font.pixelSize: 10; font.bold: true; color: "#ffffff"; Layout.fillWidth: true }
                            AppIconButton {
                                iconName: root.v2Locked ? "lock" : "more"
                                Layout.preferredWidth: 18; Layout.preferredHeight: 18
                                onClicked: root.v2Locked = !root.v2Locked
                            }
                        }
                    }

                    // V1 Header (Main Video)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 46
                        color: "#1a1a1d"
                        border.width: 1
                        border.color: "#27272a"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 4
                            Rectangle { width: 3; height: 24; color: "#3b82f6"; radius: 1 }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Label { text: "V1 Video"; font.pixelSize: 10; font.bold: true; color: "#ffffff" }
                                Label { text: root.fps + " fps"; font.pixelSize: 8; color: "#71717a" }
                            }
                            AppIconButton {
                                iconName: root.v1Locked ? "lock" : "more"
                                Layout.preferredWidth: 18; Layout.preferredHeight: 18
                                onClicked: root.v1Locked = !root.v1Locked
                            }
                        }
                    }

                    // A1 Header (Audio)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        color: "#1a1a1d"
                        border.width: 1
                        border.color: "#27272a"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 4
                            Rectangle { width: 3; height: 16; color: "#10b981"; radius: 1 }
                            Label { text: "A1 Audio"; font.pixelSize: 10; font.bold: true; color: "#ffffff"; Layout.fillWidth: true }
                            AppIconButton {
                                iconName: "audio"
                                Layout.preferredWidth: 18; Layout.preferredHeight: 18
                                prominent: !root.a1Muted
                                onClicked: root.a1Muted = !root.a1Muted
                            }
                        }
                    }

                    // A2 Header (Music)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        color: "#1a1a1d"
                        border.width: 1
                        border.color: "#27272a"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 4
                            Rectangle { width: 3; height: 16; color: "#06b6d4"; radius: 1 }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Label { text: "A2 Music"; font.pixelSize: 10; font.bold: true; color: "#ffffff" }
                                Label { text: root.bgMusicDucking ? "Ducking" : ""; font.pixelSize: 7; color: "#06b6d4"; visible: root.bgMusicDucking }
                            }
                            AppIconButton {
                                iconName: "audio"
                                Layout.preferredWidth: 18; Layout.preferredHeight: 18
                                prominent: !root.a2Muted
                                onClicked: root.a2Muted = !root.a2Muted
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // Right Timeline Lanes with Ruler, Clips, Waveforms and Playhead
            Flickable {
                id: lanesFlickable
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: Math.max(width, width * root.zoom)
                contentHeight: lanesColumn.implicitHeight
                boundsBehavior: Flickable.StopAtBounds

                Item {
                    id: lanesCanvas
                    width: lanesFlickable.contentWidth
                    height: lanesFlickable.contentHeight

                    ColumnLayout {
                        id: lanesColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        spacing: 2

                        // Timecode Ruler
                        Rectangle {
                            id: rulerArea
                            Layout.fillWidth: true
                            Layout.preferredHeight: 22
                            color: "#1a1a1d"
                            border.width: 1
                            border.color: "#27272a"

                            Repeater {
                                model: Math.max(1, Math.floor(root.effectiveDuration / (root.zoom > 2 ? 1 : root.zoom > 1.4 ? 2 : 5)) + 1)
                                delegate: Item {
                                    required property int index
                                    readonly property real secStep: (root.zoom > 2 ? 1 : root.zoom > 1.4 ? 2 : 5)
                                    readonly property real sec: index * secStep
                                    x: (sec / root.effectiveDuration) * rulerArea.width
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: 1

                                    Rectangle {
                                        width: 1; height: 6
                                        anchors.top: parent.top
                                        color: "#52525b"
                                    }

                                    Label {
                                        x: 3; y: 1
                                        text: root.formatTimecode(sec).slice(3, 8)
                                        font.pixelSize: 8
                                        font.family: Theme.monoFont
                                        color: "#71717a"
                                    }
                                }
                            }
                        }

                        // V2 Titles Lane
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 32
                            color: "#18181b"
                            border.width: 1
                            border.color: "#27272a"

                            Rectangle {
                                x: parent.width * 0.1
                                width: parent.width * 0.25
                                height: parent.height - 4
                                y: 2
                                radius: 3
                                color: "#581c87"
                                border.width: 1
                                border.color: "#a855f7"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    spacing: 4
                                    Rectangle {
                                        width: 14; height: 14; radius: 2; color: "#a855f7"
                                        Label { anchors.centerIn: parent; text: "T"; font.pixelSize: 9; font.bold: true; color: "#ffffff" }
                                    }
                                    Label { text: "Нижня плашка (Lower Third)"; font.pixelSize: 10; color: "#f3e8ff"; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                            }
                        }

                        // V1 Main Video Lane
                        Rectangle {
                            id: v1Lane
                            Layout.fillWidth: true
                            Layout.preferredHeight: 46
                            color: "#18181b"
                            border.width: 1
                            border.color: "#27272a"

                            // Active trimmed main video clip
                            Rectangle {
                                id: mainVideoClip
                                x: parent.width * (root.inPoint / root.effectiveDuration)
                                width: Math.max(12, parent.width * ((root.outPoint - root.inPoint) / root.effectiveDuration))
                                height: parent.height - 4
                                y: 2
                                radius: 4
                                color: "#1e3a8a" // DaVinci Clip Dark Blue
                                border.width: 1
                                border.color: "#3b82f6"

                                // Simulated filmstrip frames
                                Row {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    spacing: 2
                                    clip: true
                                    opacity: 0.35
                                    Repeater {
                                        model: Math.max(1, Math.floor(mainVideoClip.width / 50))
                                        Rectangle {
                                            width: 46; height: mainVideoClip.height - 4
                                            color: "#1e293b"
                                            radius: 2
                                            AppIcon { anchors.centerIn: parent; name: "film"; width: 14; height: 14; iconColor: "#60a5fa" }
                                        }
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    spacing: 6
                                    AppIcon { name: "film"; Layout.preferredWidth: 14; Layout.preferredHeight: 14; iconColor: "#93c5fd" }
                                    Label {
                                        text: "Основне відео (" + root.formatTimecode(root.outPoint - root.inPoint) + ")"
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                        color: "#ffffff"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }

                            // Transition badge between clips if any
                            Rectangle {
                                visible: root.timelineClips.length > 0
                                x: mainVideoClip.x + mainVideoClip.width - 12
                                width: 24
                                height: parent.height - 8
                                y: 4
                                radius: 2
                                color: "#d97706"
                                border.width: 1
                                border.color: "#f59e0b"
                                Label {
                                    anchors.centerIn: parent
                                    text: "⧖"
                                    font.pixelSize: 10
                                    color: "#ffffff"
                                }
                            }
                        }

                        // A1 Audio Lane
                        Rectangle {
                            id: a1Lane
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34
                            color: "#18181b"
                            border.width: 1
                            border.color: "#27272a"

                            Rectangle {
                                x: parent.width * (root.inPoint / root.effectiveDuration)
                                width: Math.max(12, parent.width * ((root.outPoint - root.inPoint) / root.effectiveDuration))
                                height: parent.height - 4
                                y: 2
                                radius: 3
                                color: "#064e3b" // Dark Green
                                border.width: 1
                                border.color: "#10b981"

                                // Waveform stylized bars
                                Row {
                                    anchors.fill: parent
                                    anchors.margins: 3
                                    spacing: 2
                                    clip: true
                                    Repeater {
                                        model: Math.max(1, Math.floor(parent.width / 4))
                                        Rectangle {
                                            required property int index
                                            width: 2
                                            height: Math.max(3, Math.sin(index * 0.35) * 12 + 13)
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: "#34d399"
                                        }
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    Label { text: "🔊 Original Audio"; font.pixelSize: 9; color: "#ecfdf5"; font.weight: Font.Medium }
                                }
                            }
                        }

                        // A2 Background Music Lane
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34
                            color: "#18181b"
                            border.width: 1
                            border.color: "#27272a"
                            visible: !!root.bgMusicPath

                            Rectangle {
                                x: 0
                                width: parent.width
                                height: parent.height - 4
                                y: 2
                                radius: 3
                                color: "#164e63" // Dark Cyan
                                border.width: 1
                                border.color: "#06b6d4"

                                Row {
                                    anchors.fill: parent
                                    anchors.margins: 3
                                    spacing: 2
                                    clip: true
                                    Repeater {
                                        model: Math.max(1, Math.floor(parent.width / 4))
                                        Rectangle {
                                            required property int index
                                            width: 2
                                            height: Math.max(4, Math.cos(index * 0.28) * 11 + 12)
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: "#22d3ee"
                                        }
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    Label {
                                        text: "🎵 Background Music (" + Math.round(root.bgMusicVolume * 100) + "%)"
                                        font.pixelSize: 9
                                        color: "#cffafe"
                                        font.weight: Font.Medium
                                    }
                                }
                            }
                        }
                    }

                    // Synchronized Red Playhead (spanning the entire detailed timeline)
                    Rectangle {
                        id: detailedPlayhead
                        x: Math.max(0, Math.min(parent.width - 2, parent.width * (root.playhead / root.effectiveDuration) - 1))
                        width: 2
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        color: "#ef4444"
                        z: 20

                        // Top Scrubber Handle
                        Rectangle {
                            width: 12; height: 10
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            color: "#ef4444"
                            radius: 2
                        }
                    }

                    // Main Timeline Interactive Scrub MouseArea
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: root.activeTool === 1 ? Qt.CrossCursor : Qt.ArrowCursor
                        acceptedButtons: Qt.LeftButton
                        onPressed: function(mouse) {
                            root.editingStarted()
                            var ratio = Math.max(0.0, Math.min(1.0, mouse.x / width))
                            var target = root.snap(ratio * root.effectiveDuration)
                            root.playheadSeekRequested(target)
                            if (root.activeTool === 1) {
                                root.splitRequested(target)
                            }
                        }
                        onPositionChanged: function(mouse) {
                            var ratio = Math.max(0.0, Math.min(1.0, mouse.x / width))
                            root.playheadSeekRequested(root.snap(ratio * root.effectiveDuration))
                        }
                        onReleased: root.editingFinished()
                    }
                }
            }
        }
    }
}

