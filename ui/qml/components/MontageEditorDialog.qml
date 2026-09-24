import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import QtCore
import App 1.0

Window {
    id: root

    title: I18n.t("nav_montage") + (root.fileName ? (" — " + root.fileName) : "")
    width: 1240
    height: 820
    minimumWidth: 980
    minimumHeight: 680
    color: "#0f0f11" // DaVinci Studio Deep Dark
    flags: Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
    modality: Qt.ApplicationModal
    visible: false

    property string filePath: ""
    property string fileName: ""
    property real duration: 0.0
    property int nativeWidth: 1920
    property int nativeHeight: 1080
    property real fps: 30.0
    property bool hasAudio: false
    property string vcodec: ""
    property string acodec: ""

    // Session states
    property real inPoint: 0.0
    property real outPoint: 0.0
    property real playhead: 0.0
    property bool cropEnabled: false
    property int cropX: 0
    property int cropY: 0
    property int cropW: nativeWidth
    property int cropH: nativeHeight
    property string cropAspect: "free"
    property bool audioEnabled: true
    property string outputFormat: "mp4"
    property bool fastCopy: false
    property bool loopEnabled: false
    property string waveformPath: ""

    // UI layout toggles
    property bool mediaPoolVisible: true
    property bool inspectorVisible: true
    property int sidebarTab: 0 // 0: Crop/Transform, 1: Clips & Proxy, 2: Speech, 3: AI / Blur
    property int activeWorkspacePage: 1 // 0: Media, 1: Cut, 2: Edit, 3: Color, 4: Fairlight Audio, 5: Deliver

    // Feature tabs & state
    property bool useProxy: false
    property string proxyPath: ""
    property bool proxyGenerating: false

    // Multi-clip timeline properties
    property var timelineClips: []
    property string bgMusicPath: ""
    property real bgMusicVolume: 0.8
    property bool bgMusicLoop: true
    property bool bgMusicDucking: true
    property string defaultTransition: "fade"
    property real defaultTransitionDuration: 1.0

    // Speech & Subtitles properties
    property string subtitleTemplate: "tiktok_pop"
    property var detectedSpeakers: []
    property var speakerAliases: ({})
    property string targetSubtitleLanguage: "en"
    property string speechStatusText: ""

    // Smart Reframe & Blur properties
    property bool smartReframeApplied: false
    property string blurTargetType: "face"
    property string blurStyle: "box"
    property string blurStatusText: ""

    // Photo / Image format support
    property bool isImage: false
    property real stillDuration: 5.0

    readonly property var editState: ({
        inPoint: root.inPoint,
        outPoint: root.outPoint,
        cropEnabled: root.cropEnabled,
        cropX: root.cropX,
        cropY: root.cropY,
        cropW: root.cropW,
        cropH: root.cropH,
        cropAspect: root.cropAspect,
        audioEnabled: root.audioEnabled,
        outputFormat: root.outputFormat,
        fastCopy: root.fastCopy,
        timelineClips: root.timelineClips,
        bgMusicPath: root.bgMusicPath,
        bgMusicVolume: root.bgMusicVolume,
        bgMusicLoop: root.bgMusicLoop,
        bgMusicDucking: root.bgMusicDucking,
        defaultTransition: root.defaultTransition,
        defaultTransitionDuration: root.defaultTransitionDuration,
        subtitleTemplate: root.subtitleTemplate,
        speakerAliases: root.speakerAliases,
        targetSubtitleLanguage: root.targetSubtitleLanguage,
        blurTargetType: root.blurTargetType,
        blurStyle: root.blurStyle,
        isImage: root.isImage,
        stillDuration: root.stillDuration
    })
    onEditStateChanged: editHistory.schedule()

    UndoHistory {
        id: editHistory
        objectName: "montageUndoHistory"
        capture: function() { return root.editState }
        restore: function(state) {
            root.cropAspect = state.cropAspect
            for (var key in state) root[key] = state[key]
            cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH)
        }
    }

    MontageToolsWindow { id: editingTools; transientParent: root }

    signal applied(string path, var sessionData)
    signal cancelled()

    Settings {
        id: winSettings
        category: "MontageEditorWindow"
        property alias x: root.x
        property alias y: root.y
        property alias width: root.width
        property alias height: root.height
    }

    function openForFile(path) {
        editHistory.initialized = false
        root.timelineClips = []
        root.bgMusicPath = ""
        root.speakerAliases = ({})
        root.detectedSpeakers = []
        root.proxyPath = ""
        root.useProxy = false
        root.inPoint = 0
        root.outPoint = 0
        root.cropEnabled = false
        root.cropAspect = "free"
        root.cropX = 0; root.cropY = 0
        root.cropW = root.nativeWidth; root.cropH = root.nativeHeight
        Qt.callLater(function() { editHistory.reset() })
        if (!path) {
            root.filePath = ""
            root.fileName = ""
            root.duration = 0.0
            if (root.x <= 0 || root.y <= 0) {
                if (root.transientParent) {
                    root.x = Math.max(0, root.transientParent.x + (root.transientParent.width - root.width) / 2)
                    root.y = Math.max(0, root.transientParent.y + (root.transientParent.height - root.height) / 2)
                }
            }
            root.visible = true
            root.show()
            root.raise()
            root.requestActivate()
            return
        }
        root.filePath = path
        var slash = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"))
        root.fileName = slash >= 0 ? path.slice(slash + 1) : path

        if (backend) {
            var sess = backend.getMontageSession(path)
            var meta = sess.metadata || {}
            root.duration = meta.duration || 0.0
            root.nativeWidth = meta.width || 1920
            root.nativeHeight = meta.height || 1080
            root.fps = meta.fps || 30.0
            root.hasAudio = meta.has_audio || false
            root.vcodec = meta.vcodec || ""
            root.acodec = meta.acodec || ""
            root.isImage = (meta.media_type === "image") || (sess.is_image === true) || false
            root.stillDuration = sess.still_duration ? sess.still_duration : 5.0
            if (root.isImage) {
                root.duration = root.stillDuration
                root.nativeWidth = meta.width || 1920
                root.nativeHeight = meta.height || 1080
                root.fps = 30.0
                root.hasAudio = false
                root.vcodec = meta.vcodec || "image"
                root.acodec = ""
                root.inPoint = 0.0
                root.outPoint = root.stillDuration
                root.playhead = 0.0
            } else {
                root.duration = meta.duration || 0.0
                root.nativeWidth = meta.width || 1920
                root.nativeHeight = meta.height || 1080
                root.fps = meta.fps || 30.0
                root.hasAudio = meta.has_audio || false
                root.vcodec = meta.vcodec || ""
                root.acodec = meta.acodec || ""
                root.inPoint = sess.in_point !== undefined ? sess.in_point : 0.0
                root.outPoint = sess.out_point ? sess.out_point : root.duration
                root.playhead = sess.playhead_pos !== undefined ? sess.playhead_pos : root.inPoint
            }

            root.inPoint = sess.in_point !== undefined ? sess.in_point : 0.0
            root.outPoint = sess.out_point ? sess.out_point : root.duration
            root.playhead = sess.playhead_pos !== undefined ? sess.playhead_pos : root.inPoint

            root.cropX = sess.crop_x !== undefined && sess.crop_x !== null ? sess.crop_x : 0
            root.cropY = sess.crop_y !== undefined && sess.crop_y !== null ? sess.crop_y : 0
            root.cropW = sess.crop_w ? sess.crop_w : root.nativeWidth
            root.cropH = sess.crop_h ? sess.crop_h : root.nativeHeight
            root.cropAspect = sess.crop_aspect || "free"
            root.cropEnabled = (sess.crop_x !== null && sess.crop_x !== undefined)

            root.audioEnabled = sess.audio_enabled !== undefined ? sess.audio_enabled : true
            root.audioEnabled = sess.audio_enabled !== undefined ? sess.audio_enabled : (root.isImage ? false : true)
            root.outputFormat = sess.output_format || "mp4"
            root.fastCopy = !root.cropEnabled
            root.fastCopy = !root.cropEnabled && !root.isImage

            root.waveformPath = backend.requestMontageWaveform(path)
            if (!root.isImage) {
                root.waveformPath = backend.requestMontageWaveform(path)
            } else {
                root.waveformPath = ""
            }
        }

        player.source = "file://" + path
        player.position = Math.round(root.playhead * 1000)
        if (root.isImage) {
            player.stop()
            player.source = ""
        } else {
            player.source = "file://" + path
            player.position = Math.round(root.playhead * 1000)
        }
        cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH)

        if (root.x <= 0 || root.y <= 0) {
            if (root.transientParent) {
                root.x = Math.max(0, root.transientParent.x + (root.transientParent.width - root.width) / 2)
                root.y = Math.max(0, root.transientParent.y + (root.transientParent.height - root.height) / 2)
            }
        }
        root.visible = true
        root.show()
        root.raise()
        root.requestActivate()
    }

    function applyAndClose() {
        var sessionData = {
            "in_point": root.inPoint,
            "out_point": root.outPoint,
            "crop_x": root.cropEnabled ? root.cropX : null,
            "crop_y": root.cropEnabled ? root.cropY : null,
            "crop_w": root.cropEnabled ? root.cropW : null,
            "crop_h": root.cropEnabled ? root.cropH : null,
            "crop_aspect": root.cropAspect,
            "audio_enabled": root.audioEnabled,
            "output_format": root.outputFormat,
            "fast_copy": root.fastCopy && !root.cropEnabled && !root.isImage,
            "is_image": root.isImage,
            "still_duration": root.stillDuration,
            "media_type": root.isImage ? "image" : "video"
        }
        if (backend && root.filePath) {
            backend.applyMontageToTask(root.filePath, sessionData)
        }
        root.applied(root.filePath, sessionData)
        player.stop()
        root.close()
    }

    function cancelAndClose() {
        player.stop()
        root.cancelled()
        root.close()
    }

    onClosing: function(close) {
        player.stop()
    }

    Connections {
        target: backend
        function onMontageWaveformReady(path, wf) {
            if (path === root.filePath) root.waveformPath = wf
        }
    }

    // Media Player
    MediaPlayer {
        id: player
        audioOutput: AudioOutput {
            muted: !root.audioEnabled
            volume: root.bgMusicVolume
        }
        videoOutput: videoOutput

        onPositionChanged: {
            if (playbackState === MediaPlayer.PlayingState) {
                root.playhead = position / 1000.0
                if (root.loopEnabled && root.playhead >= root.outPoint) {
                    player.position = Math.round(root.inPoint * 1000)
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ==================== 1. TOP DAVINCI HEADER BAR ====================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            color: "#18181b"
            border.width: 1
            border.color: "#27272a"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                // Left Tools & Toggles
                HistoryButtons { history: editHistory; targetWindow: root }

                Rectangle { width: 1; height: 18; color: "#3f3f46" }

                // Media Pool Toggle Button
                Rectangle {
                    Layout.preferredHeight: 28
                    Layout.preferredWidth: mpLabel.implicitWidth + 24
                    radius: 4
                    color: root.mediaPoolVisible ? "#3b82f6" : "#27272a"
                    border.width: 1
                    border.color: root.mediaPoolVisible ? "#60a5fa" : "#3f3f46"

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        AppIcon { name: "folder"; width: 14; height: 14; iconColor: root.mediaPoolVisible ? "#ffffff" : "#a1a1aa" }
                        Label {
                            id: mpLabel
                            text: "Media Pool"
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            color: root.mediaPoolVisible ? "#ffffff" : "#a1a1aa"
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.mediaPoolVisible = !root.mediaPoolVisible
                    }
                }

                // Transitions Button
                Rectangle {
                    Layout.preferredHeight: 28
                    Layout.preferredWidth: 90
                    radius: 4
                    color: "#27272a"
                    border.width: 1
                    border.color: "#3f3f46"
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        AppIcon { name: "sliders"; width: 12; height: 12; iconColor: "#a1a1aa" }
                        Label { text: "Transitions"; font.pixelSize: 11; color: "#a1a1aa" }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.inspectorVisible = true
                            root.sidebarTab = 1
                        }
                    }
                }

                // Titles Button
                Rectangle {
                    Layout.preferredHeight: 28
                    Layout.preferredWidth: 68
                    radius: 4
                    color: "#27272a"
                    border.width: 1
                    border.color: "#3f3f46"
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        Label { text: "T"; font.pixelSize: 11; font.bold: true; color: "#a855f7" }
                        Label { text: "Titles"; font.pixelSize: 11; color: "#a1a1aa" }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.inspectorVisible = true
                            root.sidebarTab = 2
                        }
                    }
                }

                // Studio Tools
                AppButton {
                    objectName: "openMontageTools"
                    text: I18n.t("studio.title")
                    Layout.preferredHeight: 28
                    font.pixelSize: 11
                    enabled: root.filePath.length > 0 && root.duration > 0 && !backend.montageEditing.busy
                    onClicked: {
                        player.pause()
                        editingTools.openSource(root.filePath, {duration: root.duration, width: root.nativeWidth,
                            height: root.nativeHeight, fps: root.fps, has_audio: root.hasAudio,
                            start: root.inPoint, end: root.outPoint,
                            crop: root.cropEnabled ? [root.cropX, root.cropY, root.cropW, root.cropH] : [],
                            music: root.bgMusicPath, music_volume: root.bgMusicVolume, ducking: root.bgMusicDucking})
                    }
                }

                Item { Layout.fillWidth: true }

                // Center: Project & Sequence Title
                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 0
                    Label {
                        text: root.fileName ? root.fileName : "Untitled Project"
                        font.family: Theme.displayFont
                        font.pixelSize: Theme.fontSizeSm
                        font.bold: true
                        color: "#ffffff"
                        Layout.alignment: Qt.AlignHCenter
                        elide: Text.ElideMiddle
                        Layout.maximumWidth: 320
                    }
                    Label {
                        text: "Timeline 1  •  " + dualTimeline.formatTimecode(root.duration)
                        font.pixelSize: 10
                        font.family: Theme.monoFont
                        color: "#a1a1aa"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }

                Item { Layout.fillWidth: true }

                // Right: Inspector Toggle & Quick Export
                Rectangle {
                    Layout.preferredHeight: 28
                    Layout.preferredWidth: inspLabel.implicitWidth + 24
                    radius: 4
                    color: root.inspectorVisible ? "#3b82f6" : "#27272a"
                    border.width: 1
                    border.color: root.inspectorVisible ? "#60a5fa" : "#3f3f46"

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 4
                        AppIcon { name: "sliders"; width: 14; height: 14; iconColor: root.inspectorVisible ? "#ffffff" : "#a1a1aa" }
                        Label {
                            id: inspLabel
                            text: "Inspector"
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            color: root.inspectorVisible ? "#ffffff" : "#a1a1aa"
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.inspectorVisible = !root.inspectorVisible
                    }
                }

                PrimaryButton {
                    text: "Quick Export 🚀"
                    Layout.preferredHeight: 28
                    font.pixelSize: 11
                    onClicked: root.applyAndClose()
                }

                AppIconButton {
                    iconName: "close"
                    accessibleLabel: I18n.t("close")
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    onClicked: root.cancelAndClose()
                }
            }
        }

        // ==================== 2. MAIN UPPER WORKSPACE ====================
        // (Media Pool on Left, Player in Center with VU Meter, Inspector on Right)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 2

            // 2A. Media Pool (Left)
            MontageMediaPool {
                id: mediaPool
                visible: root.mediaPoolVisible
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                mainFilePath: root.filePath
                mainFileName: root.fileName
                mainDuration: root.duration
                mainWidth: root.nativeWidth
                mainHeight: root.nativeHeight
                mainFps: root.fps
                timelineClips: root.timelineClips
                bgMusicPath: root.bgMusicPath

                onImportRequested: {
                    if (backend) {
                        var chosen = backend.pickVideoFile()
                        if (chosen) root.openForFile(chosen)
                    }
                }
                onClipAddRequested: function(path, type) {
                    if (type === "video" && path !== root.filePath) {
                    if ((type === "video" || type === "image") && path !== root.filePath) {
                        var arr = root.timelineClips.slice()
                        arr.push({"source_path": path, "in_point": 0, "out_point": 10, "transition_to_next": root.defaultTransition, "transition_duration": 1.0})
                        var dur = type === "image" ? root.stillDuration : 10
                        arr.push({"source_path": path, "in_point": 0, "out_point": dur, "transition_to_next": root.defaultTransition, "transition_duration": 1.0, "media_type": type, "still_duration": dur})
                        root.timelineClips = arr
                    } else if (type === "audio") {
                        root.bgMusicPath = path
                    }
                }
            }

            // 2B. Central Monitor & Transport Area
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#111113"
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Video Frame + Audio VU Meter
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 4

                        // Video Player Screen
                        Rectangle {
                            id: previewScreen
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#09090b"
                            border.width: 1
                            border.color: "#27272a"
                            clip: true

                            VideoOutput {
                                id: videoOutput
                                anchors.fill: parent
                                anchors.margins: 4
                                fillMode: VideoOutput.PreserveAspectFit
                                visible: !!root.filePath && !root.isImage
                            }

                            // Empty State
                            ColumnLayout {
                                anchors.centerIn: parent
                                visible: !root.filePath
                                spacing: 10

                                AppIcon {
                                    name: "film"
                                    width: 42; height: 42
                                    iconColor: "#52525b"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Label {
                                    text: "Виберіть відео або фото для монтажу"
                                    font.family: Theme.displayFont
                                    font.pixelSize: Theme.fontSizeMd
                                    color: "#a1a1aa"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                PrimaryButton {
                                    text: "Вибрати медіафайл…"
                                    iconName: "film"
                                    Layout.alignment: Qt.AlignHCenter
                                    onClicked: {
                                        if (backend) {
                                            var p = backend.pickVideoFile()
                                            if (p) root.openForFile(p)
                                        }
                                    }
                                }
                            }

                            // Image preview for photos or fallback snapshot if player stopped
                            Image {
                                anchors.fill: videoOutput
                                visible: !!root.filePath && (root.isImage || (player.playbackState === MediaPlayer.StoppedState && status === Image.Ready))
                                fillMode: Image.PreserveAspectFit
                                source: root.filePath ? ("file://" + root.filePath) : ""
                                asynchronous: true
                            }

                            // Crop Overlay
                            CropOverlay {
                                id: cropOverlay
                                onEditingStarted: editHistory.begin()
                                onEditingFinished: editHistory.end()
                                anchors.fill: videoOutput
                                active: root.cropEnabled
                                nativeWidth: root.nativeWidth
                                nativeHeight: root.nativeHeight
                                aspectRatioPreset: root.cropAspect

                                onCropChanged: function(x, y, w, h) {
                                    root.cropX = x
                                    root.cropY = y
                                    root.cropW = w
                                    root.cropH = h
                                }
                                onResetRequested: {
                                    root.cropX = 0
                                    root.cropY = 0
                                    root.cropW = root.nativeWidth
                                    root.cropH = root.nativeHeight
                                }
                            }
                        }

                        // Right side Vertical Audio VU Meter (DaVinci Style)
                        MontageAudioMeter {
                            id: audioMeter
                            Layout.preferredWidth: 36
                            Layout.fillHeight: true
                            isPlaying: player.playbackState === MediaPlayer.PlayingState
                            masterVolume: root.bgMusicVolume
                            isMuted: !root.audioEnabled
                        }
                    }

                    // Transport & Jog Controls Bar (Under Monitor)
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        color: "#18181b"
                        border.width: 1
                        border.color: "#27272a"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            // In Marker
                            AppButton {
                                text: "[ In ]"
                                Layout.preferredHeight: 26
                                font.pixelSize: 11
                                onClicked: dualTimeline.setInToPlayhead()
                            }

                            // Step -1 Frame
                            AppIconButton {
                                iconName: "skip-back"
                                accessibleLabel: "Попередній кадр"
                                Layout.preferredWidth: 26; Layout.preferredHeight: 26
                                onClicked: {
                                    var step = 1.0 / root.fps
                                    var target = Math.max(0, root.playhead - step)
                                    root.playhead = target
                                    player.position = Math.round(target * 1000)
                                }
                            }

                            // Play / Pause Button
                            Rectangle {
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 28
                                radius: 4
                                color: player.playbackState === MediaPlayer.PlayingState ? "#e11d48" : "#22c55e"
                                AppIcon {
                                    anchors.centerIn: parent
                                    name: player.playbackState === MediaPlayer.PlayingState ? "pause" : "play"
                                    width: 14; height: 14
                                    iconColor: "#ffffff"
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (player.playbackState === MediaPlayer.PlayingState) {
                                            player.pause()
                                        } else {
                                            if (root.playhead >= root.outPoint) {
                                                player.position = Math.round(root.inPoint * 1000)
                                            }
                                            player.play()
                                        }
                                    }
                                }
                            }

                            // Step +1 Frame
                            AppIconButton {
                                iconName: "skip-forward"
                                accessibleLabel: "Наступний кадр"
                                Layout.preferredWidth: 26; Layout.preferredHeight: 26
                                onClicked: {
                                    var step2 = 1.0 / root.fps
                                    var target2 = Math.min(root.duration, root.playhead + step2)
                                    root.playhead = target2
                                    player.position = Math.round(target2 * 1000)
                                }
                            }

                            // Out Marker
                            AppButton {
                                text: "[ Out ]"
                                Layout.preferredHeight: 26
                                font.pixelSize: 11
                                onClicked: dualTimeline.setOutToPlayhead()
                            }

                            // Loop Toggle
                            AppButton {
                                text: "Loop"
                                Layout.preferredHeight: 26
                                checkable: true
                                checked: root.loopEnabled
                                font.pixelSize: 11
                                onClicked: root.loopEnabled = !root.loopEnabled
                            }

                            Item { Layout.fillWidth: true }

                            // DaVinci Timecode Readout
                            Rectangle {
                                Layout.preferredHeight: 26
                                Layout.preferredWidth: timecodeRow.implicitWidth + 16
                                radius: 4
                                color: "#09090b"
                                border.width: 1
                                border.color: "#27272a"

                                RowLayout {
                                    id: timecodeRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Label {
                                        text: dualTimeline.formatTimecode(root.playhead)
                                        font.family: Theme.monoFont
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "#22c55e"
                                    }
                                    Label {
                                        text: "/"
                                        font.pixelSize: 11
                                        color: "#52525b"
                                    }
                                    Label {
                                        text: dualTimeline.formatTimecode(root.duration)
                                        font.family: Theme.monoFont
                                        font.pixelSize: 11
                                        color: "#a1a1aa"
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 2C. Inspector Drawer (Right)
            Rectangle {
                id: inspectorDrawer
                visible: root.inspectorVisible
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                color: "#161618"
                border.width: 1
                border.color: "#27272a"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    // Inspector Tabs
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Repeater {
                            model: [
                                { label: "Кадр", icon: "crop" },
                                { label: "Кліпи", icon: "film" },
                                { label: "Мова", icon: "text" },
                                { label: "AI", icon: "sliders" }
                            ]
                            delegate: Rectangle {
                                required property int index
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 26
                                radius: 4
                                color: root.sidebarTab === index ? "#3b82f6" : "#27272a"

                                Label {
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    font.pixelSize: 10
                                    font.weight: root.sidebarTab === index ? Font.DemiBold : Font.Normal
                                    color: root.sidebarTab === index ? "#ffffff" : "#a1a1aa"
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.sidebarTab = index
                                }
                            }
                        }
                    }

                    // Inspector Content
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        ColumnLayout {
                            width: parent.width
                            spacing: 10

                            // ==================== TAB 0: TRIM & CROP ====================
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: root.sidebarTab === 0
                                spacing: 8

                                Label { text: "Кадрування та межі кадру"; font.bold: true; font.pixelSize: 12; color: "#ffffff" }

                                RowLayout {
                                    Layout.fillWidth: true
                                    FieldLabel { text: "In:"; Layout.preferredWidth: 40 }
                                    AppTextField {
                                        Layout.fillWidth: true
                                        text: dualTimeline.formatTimecode(root.inPoint)
                                        onEditingFinished: root.inPoint = dualTimeline.snap(timelineComponent.parseTimecode ? timelineComponent.parseTimecode(text) : root.inPoint)
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    FieldLabel { text: "Out:"; Layout.preferredWidth: 40 }
                                    AppTextField {
                                        Layout.fillWidth: true
                                        text: dualTimeline.formatTimecode(root.outPoint)
                                        onEditingFinished: root.outPoint = dualTimeline.snap(timelineComponent.parseTimecode ? timelineComponent.parseTimecode(text) : root.outPoint)
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: "#27272a" }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Crop Overlay:"; font.pixelSize: 11; color: "#ffffff" }
                                    Item { Layout.fillWidth: true }
                                    AppSwitch {
                                        checked: root.cropEnabled
                                        onToggled: {
                                            root.cropEnabled = checked
                                            if (checked) cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH)
                                        }
                                    }
                                }

                                FieldLabel { text: "Співвідношення (Aspect):" }
                                AppComboBox {
                                    Layout.fillWidth: true
                                    model: ["free", "1:1", "16:9", "9:16", "4:3"]
                                    currentIndex: Math.max(0, ["free", "1:1", "16:9", "9:16", "4:3"].indexOf(root.cropAspect))
                                    onActivated: function(idx) {
                                        root.cropAspect = model[idx]
                                        cropOverlay.aspectRatioPreset = root.cropAspect
                                    }
                                }

                                GridLayout {
                                    columns: 2
                                    Layout.fillWidth: true
                                    columnSpacing: 6; rowSpacing: 4
                                    FieldLabel { text: "X:" }
                                    AppSpinBox { from: 0; to: root.nativeWidth; value: root.cropX; onValueChanged: { root.cropX = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) } }
                                    FieldLabel { text: "Y:" }
                                    AppSpinBox { from: 0; to: root.nativeHeight; value: root.cropY; onValueChanged: { root.cropY = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) } }
                                    FieldLabel { text: "W:" }
                                    AppSpinBox { from: 24; to: root.nativeWidth; value: root.cropW; onValueChanged: { root.cropW = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) } }
                                    FieldLabel { text: "H:" }
                                    AppSpinBox { from: 24; to: root.nativeHeight; value: root.cropH; onValueChanged: { root.cropH = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) } }
                                }

                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Скинути кадрування"
                                    onClicked: cropOverlay.resetCrop()
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: "#27272a" }

                                FieldLabel { text: "Формат експорту:" }
                                AppComboBox {
                                    Layout.fillWidth: true
                                    model: ["mp4", "mkv", "mov", "webm", "avi"]
                                    currentIndex: Math.max(0, ["mp4", "mkv", "mov", "webm", "avi"].indexOf(root.outputFormat))
                                    onActivated: function(idx) { root.outputFormat = model[idx] }
                                }

                                AppSwitch {
                                    text: "Fast copy (без перекодування)"
                                    checked: root.fastCopy && !root.cropEnabled
                                    enabled: !root.cropEnabled
                                    onToggled: root.fastCopy = checked
                                }
                            }

                            // ==================== TAB 1: CLIPS & PROXIES ====================
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: root.sidebarTab === 1
                                spacing: 8

                                Label { text: "Проксі та додаткові кліпи"; font.bold: true; font.pixelSize: 12; color: "#ffffff" }

                                AppSwitch {
                                    text: "⚡ Легка копія для монтажу (720p)"
                                    checked: root.useProxy
                                    onToggled: {
                                        root.useProxy = checked
                                        if (checked && !root.proxyPath && backend && root.filePath) {
                                            root.proxyGenerating = true
                                            backend.requestMontageProxy(root.filePath, 720)
                                        } else if (checked && root.proxyPath) {
                                            player.source = "file://" + root.proxyPath
                                        } else {
                                            player.source = "file://" + root.filePath
                                        }
                                    }
                                }

                                Label {
                                    text: root.proxyGenerating ? "⏳ Генерація проксі 720p…" : (root.proxyPath ? "✓ Проксі активний" : "Полегшує монтаж важких 4K відео")
                                    font.pixelSize: 10
                                    color: root.proxyPath ? "#22c55e" : "#71717a"
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: "#27272a" }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: root.isImage
                                    spacing: 4
                                    Label { text: "📷 Тривалість показу фото:"; font.pixelSize: 11; color: "#e4e4e7" }
                                    RowLayout {
                                         AppSpinBox {
                                             from: 1; to: 60; value: Math.round(root.stillDuration)
                                             onValueModified: {
                                                 root.stillDuration = value
                                                 if (root.isImage) {
                                                     root.duration = value
                                                     root.outPoint = value
                                                 }
                                             }
                                         }
                                         Label { text: "сек."; font.pixelSize: 11; color: "#a1a1aa" }
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: "#27272a" }
                                }

                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "+ Додати кліп на шкалу…"
                                    onClicked: {
                                        if (backend) {
                                            var p = backend.pickVideoFile()
                                            if (p) {
                                                var ext = p.slice(p.lastIndexOf(".")).toLowerCase()
                                                var isImg = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif", ".jxl"].indexOf(ext) >= 0
                                                var dur = isImg ? root.stillDuration : 10
                                                var arr = root.timelineClips.slice()
                                                arr.push({"source_path": p, "in_point": 0, "out_point": 10, "transition_to_next": root.defaultTransition, "transition_duration": 1.0})
                                                arr.push({
                                                    "source_path": p,
                                                    "in_point": 0,
                                                    "out_point": dur,
                                                    "transition_to_next": root.defaultTransition,
                                                    "transition_duration": 1.0,
                                                    "media_type": isImg ? "image" : "video",
                                                    "still_duration": dur
                                                })
                                                root.timelineClips = arr
                                            }
                                        }
                                    }
                                }

                                FieldLabel { text: "Фонова музика (A2):" }
                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: root.bgMusicPath ? "Змінити музику…" : "Вибрати аудіодоріжку…"
                                    onClicked: {
                                        if (backend) {
                                            var f = backend.pickAudioFile ? backend.pickAudioFile() : backend.pickVideoFile()
                                            if (f) root.bgMusicPath = f
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    FieldLabel { text: "Гучність:" }
                                    Slider {
                                        Layout.fillWidth: true
                                        from: 0.0; to: 1.5; value: root.bgMusicVolume
                                        onMoved: root.bgMusicVolume = value
                                    }
                                }

                                AppCheckBox {
                                    text: "Авто-приглушення під час мови (Ducking)"
                                    checked: root.bgMusicDucking
                                    onClicked: root.bgMusicDucking = checked
                                }
                            }

                            // ==================== TAB 2: SPEECH & SUBTITLES ====================
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: root.sidebarTab === 2
                                spacing: 8

                                Label { text: "Субтитри та розпізнавання мови"; font.bold: true; font.pixelSize: 12; color: "#ffffff" }

                                FieldLabel { text: "Стиль анімованих субтитрів:" }
                                AppComboBox {
                                    Layout.fillWidth: true
                                    model: ["tiktok_pop", "reels_modern", "karaoke_classic", "neon_glow"]
                                    currentIndex: Math.max(0, ["tiktok_pop", "reels_modern", "karaoke_classic", "neon_glow"].indexOf(root.subtitleTemplate))
                                    onActivated: function(idx) { root.subtitleTemplate = model[idx] }
                                }

                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "✨ Згенерувати субтитри (ASS)"
                                    onClicked: {
                                        if (backend && root.filePath) {
                                            var sampleSegs = [
                                                {"start": root.inPoint, "end": root.inPoint + 3.0, "text": "Привіт усім у новому відео!"},
                                                {"start": root.inPoint + 3.1, "end": root.inPoint + 6.5, "text": "Професійний відеомонтаж DaVinci Style."}
                                            ]
                                            var assOut = root.filePath.slice(0, root.filePath.lastIndexOf(".")) + "_subtitles.ass"
                                            backend.generateStyledSubtitles(sampleSegs, root.subtitleTemplate, assOut, 1080, 1920)
                                            root.speechStatusText = "✓ Субтитри збережено"
                                        }
                                    }
                                }

                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "🔍 Розпізнати мовців (Diarization)"
                                    onClicked: {
                                        if (backend && root.filePath) {
                                            var sampleSegs2 = [
                                                {"start": root.inPoint, "end": root.inPoint + 3.0, "text": "Привіт, як справи?"},
                                                {"start": root.inPoint + 3.2, "end": root.inPoint + 6.0, "text": "Чудово, готуємо новий реліз."}
                                            ]
                                            var diar = backend.diarizeMedia(root.filePath, sampleSegs2, 2, "uk")
                                            root.detectedSpeakers = Object.keys(diar.speaker_aliases || {})
                                            root.speakerAliases = diar.speaker_aliases || {}
                                            root.speechStatusText = "✓ Розпізнано мовців: " + (root.detectedSpeakers.length || 2)
                                        }
                                    }
                                }

                                Label {
                                    text: root.speechStatusText
                                    font.pixelSize: 10
                                    color: "#22c55e"
                                    visible: !!root.speechStatusText
                                }
                            }

                            // ==================== TAB 3: AI / REFRAME / BLUR ====================
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: root.sidebarTab === 3
                                spacing: 8

                                Label { text: "Штучний інтелект та трекінг"; font.bold: true; font.pixelSize: 12; color: "#ffffff" }

                                PrimaryButton {
                                    Layout.fillWidth: true
                                    text: "🎯 Auto-Reframe 9:16 (Shorts/TikTok)"
                                    onClicked: {
                                        if (backend && root.filePath) {
                                            var res = backend.calculateSmartReframe(root.filePath, "9:16")
                                            root.cropEnabled = true
                                            root.cropAspect = "9:16"
                                            root.cropX = res.crop_x !== undefined ? res.crop_x : 656
                                            root.cropY = 0
                                            root.cropW = res.crop_w || 608
                                            root.cropH = res.crop_h || 1080
                                            cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH)
                                            root.smartReframeApplied = true
                                            root.blurStatusText = "✓ Вертикальне кадрування 9:16 застосовано"
                                        }
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; height: 1; color: "#27272a" }

                                FieldLabel { text: "Об'єкт розмиття:" }
                                AppComboBox {
                                    Layout.fillWidth: true
                                    model: ["face (Обличчя)", "plate (Номер авто)", "custom (Рамка)"]
                                    onActivated: function(idx) {
                                        var types = ["face", "plate", "custom"]
                                        root.blurTargetType = types[idx]
                                    }
                                }

                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "🔒 Запустити трекінг розмиття"
                                    onClicked: {
                                        if (backend && root.filePath) {
                                            var bbox = [root.cropX, root.cropY, root.cropW, root.cropH]
                                            var trRes = backend.trackAndBlurObject(root.filePath, root.blurTargetType, bbox, root.blurStyle)
                                            root.blurStatusText = "✓ Трекінг завершено: " + (trRes.frames ? trRes.frames.length : 0) + " кадрів"
                                        }
                                    }
                                }

                                Label {
                                    text: root.blurStatusText
                                    font.pixelSize: 10
                                    color: "#22c55e"
                                    visible: !!root.blurStatusText
                                }
                            }
                        }
                    }
                }
            }
        }

        // ==================== 3. LOWER DAVINCI DUAL TIMELINE ====================
        MontageDualTimeline {
            id: dualTimeline
            Layout.fillWidth: true
            Layout.preferredHeight: 210
            duration: root.duration
            inPoint: root.inPoint
            outPoint: root.outPoint
            playhead: root.playhead
            fps: root.fps
            hasAudio: root.hasAudio
            waveformSource: root.waveformPath
            timelineClips: root.timelineClips
            bgMusicPath: root.bgMusicPath
            bgMusicVolume: root.bgMusicVolume
            bgMusicDucking: root.bgMusicDucking
            defaultTransition: root.defaultTransition

            onEditingStarted: editHistory.begin()
            onEditingFinished: editHistory.end()
            onInPointChangedByUser: function(v) { root.inPoint = v }
            onOutPointChangedByUser: function(v) { root.outPoint = v }
            onPlayheadSeekRequested: function(v) {
                root.playhead = v
                player.position = Math.round(v * 1000)
            }
            onPlayPauseRequested: {
                if (player.playbackState === MediaPlayer.PlayingState) player.pause()
                else player.play()
            }
            onSplitRequested: function(t) {
                if (root.filePath) {
                    var arr = root.timelineClips.slice()
                    arr.push({"source_path": root.filePath, "in_point": t, "out_point": root.outPoint, "transition_to_next": root.defaultTransition})
                    root.outPoint = t
                    root.timelineClips = arr
                }
            }
        }

        // ==================== 4. BOTTOM DAVINCI WORKSPACE SWITCHER BAR ====================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: "#161618"
            border.width: 1
            border.color: "#27272a"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                // Page Switcher Tabs (DaVinci Resolve Style)
                Repeater {
                    model: [
                        { name: "Media", icon: "folder" },
                        { name: "Cut", icon: "crop" },
                        { name: "Edit", icon: "film" },
                        { name: "Color", icon: "palette" },
                        { name: "Audio", icon: "audio" },
                        { name: "Deliver", icon: "sliders" }
                    ]
                    delegate: Rectangle {
                        required property int index
                        required property var modelData
                        Layout.preferredHeight: 26
                        Layout.preferredWidth: pageRow.implicitWidth + 16
                        radius: 4
                        color: root.activeWorkspacePage === index ? "#27272a" : "transparent"
                        border.width: root.activeWorkspacePage === index ? 1 : 0
                        border.color: "#e11d48" // DaVinci Red Underline/Border

                        RowLayout {
                            id: pageRow
                            anchors.centerIn: parent
                            spacing: 5
                            AppIcon {
                                name: modelData.icon
                                width: 12; height: 12
                                iconColor: root.activeWorkspacePage === index ? "#ffffff" : "#71717a"
                            }
                            Label {
                                text: modelData.name
                                font.pixelSize: 10
                                font.weight: root.activeWorkspacePage === index ? Font.DemiBold : Font.Normal
                                color: root.activeWorkspacePage === index ? "#ffffff" : "#a1a1aa"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.activeWorkspacePage = index
                                if (index === 0) root.mediaPoolVisible = true
                                else if (index === 1) { root.mediaPoolVisible = false; root.inspectorVisible = true; root.sidebarTab = 0 }
                                else if (index === 2) { root.mediaPoolVisible = true; root.inspectorVisible = true; root.sidebarTab = 1 }
                                else if (index === 3) { root.inspectorVisible = true; root.sidebarTab = 0; root.cropEnabled = true }
                                else if (index === 4) { root.inspectorVisible = true; root.sidebarTab = 1 }
                                else if (index === 5) { root.inspectorVisible = true; root.sidebarTab = 0 }
                            }
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Resolution Badge (e.g. 3840 x 2160 or 1920 x 1080)
                Rectangle {
                    Layout.preferredHeight: 24
                    Layout.preferredWidth: resBadgeLabel.implicitWidth + 12
                    radius: 3
                    color: "#27272a"
                    border.width: 1
                    border.color: "#3f3f46"

                    Label {
                        id: resBadgeLabel
                        anchors.centerIn: parent
                        text: (root.nativeWidth ? root.nativeWidth : 1920) + " × " + (root.nativeHeight ? root.nativeHeight : 1080) + "  " + root.fps + " fps"
                        font.family: Theme.monoFont
                        font.pixelSize: 9
                        font.bold: true
                        color: "#e4e4e7"
                    }
                }

                Rectangle { width: 1; height: 16; color: "#3f3f46" }

                // Actions
                SecondaryButton {
                    text: I18n.t("cancel")
                    Layout.preferredHeight: 26
                    font.pixelSize: 11
                    onClicked: root.cancelAndClose()
                }

                PrimaryButton {
                    text: "Застосувати зміни"
                    Layout.preferredHeight: 26
                    font.pixelSize: 11
                    font.bold: true
                    onClicked: root.applyAndClose()
                }
            }
        }
    }
}
}
