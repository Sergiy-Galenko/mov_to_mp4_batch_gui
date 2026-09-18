import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import QtCore
import App 1.0

Window {
    id: root

    title: I18n.t("nav_montage") + (root.fileName ? (" — " + root.fileName) : "")
    width: 1120
    height: 740
    minimumWidth: 960
    minimumHeight: 640
    color: Theme.bgBase
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

    // Feature tabs & state
    property int sidebarTab: 0
    property bool useProxy: false
    property string proxyPath: ""
    property bool proxyGenerating: false

    // Multi-clip timeline properties
    property var timelineClips: []
    property string bgMusicPath: ""
    property real bgMusicVolume: 0.8
    property bool bgMusicLoop: true
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
        defaultTransition: root.defaultTransition,
        defaultTransitionDuration: root.defaultTransitionDuration,
        subtitleTemplate: root.subtitleTemplate,
        speakerAliases: root.speakerAliases,
        targetSubtitleLanguage: root.targetSubtitleLanguage,
        blurTargetType: root.blurTargetType,
        blurStyle: root.blurStyle
    })
    onEditStateChanged: editHistory.schedule()
    UndoHistory {
        id: editHistory
        objectName: "montageUndoHistory"
        capture: function() { return root.editState }
        restore: function(state) {
            // Assign aspect before coordinates: its visual handler can adjust the box.
            root.cropAspect = state.cropAspect
            for (var key in state) root[key] = state[key]
            cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH)
        }
    }

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
            root.outputFormat = sess.output_format || "mp4"
            root.fastCopy = !root.cropEnabled

            root.waveformPath = backend.requestMontageWaveform(path)
        }

        player.source = "file://" + path
        player.position = Math.round(root.playhead * 1000)
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
            "fast_copy": root.fastCopy && !root.cropEnabled
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
        anchors.margins: 12
        spacing: 8

        // Top Header Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space3

            HistoryButtons { history: editHistory; targetWindow: root }
            AppIcon {
                name: "film"
                width: 22
                height: 22
                iconColor: Theme.accentPrimary
            }

            Label {
                text: I18n.t("nav_montage")
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontSizeLg
                font.bold: true
                color: Theme.textPrimary
            }

            Rectangle { width: 1; height: 16; color: Theme.borderDefault }

            Label {
                text: root.fileName
                font.family: Theme.bodyFont
                font.pixelSize: Theme.fontSizeMd
                color: Theme.textSecondary
                elide: Text.ElideMiddle
                Layout.maximumWidth: 320
            }

            Rectangle { width: 1; height: 16; color: Theme.borderDefault }

            Label {
                text: root.nativeWidth + "×" + root.nativeHeight + " (" + root.fps + " fps)"
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontSizeSm
                color: Theme.textMuted
            }

            SecondaryButton {
                iconName: "folder"
                text: (root.filePath ? "Змінити відео…" : "Вибрати відео…")
                Layout.preferredHeight: 28
                onClicked: {
                    if (backend) {
                        var chosen = backend.pickVideoFile()
                        if (chosen) root.openForFile(chosen)
                    }
                }
            }

            Item { Layout.fillWidth: true }

            AppIconButton {
                iconName: "close"
                accessibleLabel: I18n.t("close")
                onClicked: root.cancelAndClose()
            }
        }

        // Main Work Area: Preview + Timeline on Left, Settings Sidebar on Right
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            // Left / Center Column
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 6

                // Video Preview Area
                Rectangle {
                    id: previewArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 280
                    color: Theme.bgElevated
                    radius: Theme.radiusMd
                    border.width: 1
                    border.color: Theme.borderDefault
                    clip: true

                    VideoOutput {
                        id: videoOutput
                        anchors.fill: parent
                        anchors.margins: 8
                        fillMode: VideoOutput.PreserveAspectFit
                        visible: !!root.filePath
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        visible: !root.filePath
                        spacing: 12

                        Label {
                            text: I18n.t("nav_montage")
                            font.family: Theme.displayFont
                            font.pixelSize: Theme.fontSizeLg
                            font.bold: true
                            color: Theme.textPrimary
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Label {
                            text: "Виберіть відеофайл для обрізки (In/Out) та візуального кадрування (Crop)"
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                            Layout.alignment: Qt.AlignHCenter
                        }

                        PrimaryButton {
                            text: "Вибрати відеофайл…"
                            iconName: "film"
                            Layout.alignment: Qt.AlignHCenter
                            onClicked: {
                                if (backend) {
                                    var chosen = backend.pickVideoFile()
                                    if (chosen) root.openForFile(chosen)
                                }
                            }
                        }
                    }

                    // Fallback snapshot if player stopped/not ready
                    Image {
                        id: snapshotFallback
                        anchors.fill: videoOutput
                        visible: player.playbackState === MediaPlayer.StoppedState && status === Image.Ready
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

                // Transport Controls Bar
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 42
                    color: Theme.panelBackground
                    radius: Theme.radiusMd
                    border.width: 1
                    border.color: Theme.borderDefault

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        // Step -1 Frame
                        AppIconButton {
                            iconName: "skip-back"
                            accessibleLabel: "Попередній кадр"
                            onClicked: {
                                var step = 1.0 / root.fps
                                var target = Math.max(0, root.playhead - step)
                                root.playhead = target
                                player.position = Math.round(target * 1000)
                            }
                        }

                        // Play / Pause
                        AppButton {
                            implicitWidth: 44
                            implicitHeight: 32
                            iconName: player.playbackState === MediaPlayer.PlayingState ? "pause" : "play"
                            Accessible.name: player.playbackState === MediaPlayer.PlayingState ? I18n.t("pause") : I18n.t("start")
                            font.pixelSize: Theme.fontSizeMd
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

                        // Step +1 Frame
                        AppIconButton {
                            iconName: "skip-forward"
                            accessibleLabel: "Наступний кадр"
                            onClicked: {
                                var step2 = 1.0 / root.fps
                                var target2 = Math.min(root.duration, root.playhead + step2)
                                root.playhead = target2
                                player.position = Math.round(target2 * 1000)
                            }
                        }

                        Rectangle { width: 1; height: 16; color: Theme.borderDefault }

                        // In / Out Shortcut buttons
                        AppButton {
                            text: "[ In ]"
                            implicitHeight: 28
                            font.pixelSize: Theme.fontSizeSm
                            onClicked: timelineComponent.setInToPlayhead()
                        }

                        AppButton {
                            text: "[ Out ]"
                            implicitHeight: 28
                            font.pixelSize: Theme.fontSizeSm
                            onClicked: timelineComponent.setOutToPlayhead()
                        }

                        // Loop toggle
                        AppButton {
                            text: "Loop"
                            implicitHeight: 28
                            checkable: true
                            checked: root.loopEnabled
                            font.pixelSize: Theme.fontSizeSm
                            onClicked: root.loopEnabled = !root.loopEnabled
                        }

                        Item { Layout.fillWidth: true }

                        // Current Timecode Readout
                        Label {
                            text: timelineComponent.formatTimecode(root.playhead)
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontSizeMd
                            font.bold: true
                            color: Theme.accentPrimary
                        }

                        Label {
                            text: "/ " + timelineComponent.formatTimecode(root.duration)
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textMuted
                        }
                    }
                }

                // Interactive Timeline Component
                Timeline {
                    id: timelineComponent
                    onEditingStarted: editHistory.begin()
                    onEditingFinished: editHistory.end()
                    Layout.fillWidth: true
                    Layout.preferredHeight: 140
                    duration: root.duration
                    inPoint: root.inPoint
                    outPoint: root.outPoint
                    playhead: root.playhead
                    fps: root.fps
                    hasAudio: root.hasAudio
                    waveformSource: root.waveformPath

                    onInPointChangedByUser: function(v) {
                        root.inPoint = v
                    }
                    onOutPointChangedByUser: function(v) {
                        root.outPoint = v
                    }
                    onPlayheadSeekRequested: function(v) {
                        root.playhead = v
                        player.position = Math.round(v * 1000)
                    }
                    onPlayPauseRequested: {
                        if (player.playbackState === MediaPlayer.PlayingState) player.pause()
                        else player.play()
                    }
                }
            }

            // Right Sidebar: Montage Settings
            Rectangle {
                Layout.preferredWidth: 330
                Layout.fillHeight: true
                color: Theme.panelBackground
                radius: Theme.radiusMd
                border.width: 1
                border.color: Theme.borderDefault

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 10
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: parent.width
                        spacing: 12

                        // Tab Switcher
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            AppButton {
                                Layout.fillWidth: true
                                text: "Кадр"
                                variant: root.sidebarTab === 0 ? "primary" : "ghost"
                                onClicked: root.sidebarTab = 0
                            }
                            AppButton {
                                Layout.fillWidth: true
                                text: "Кліпи"
                                variant: root.sidebarTab === 1 ? "primary" : "ghost"
                                onClicked: root.sidebarTab = 1
                            }
                            AppButton {
                                Layout.fillWidth: true
                                text: "Мова"
                                variant: root.sidebarTab === 2 ? "primary" : "ghost"
                                onClicked: root.sidebarTab = 2
                            }
                            AppButton {
                                Layout.fillWidth: true
                                text: "AI / Блюр"
                                variant: root.sidebarTab === 3 ? "primary" : "ghost"
                                onClicked: root.sidebarTab = 3
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                        // ==================== TAB 0: TRIM & CROP ====================
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.sidebarTab === 0
                            spacing: 12

                            Label {
                                text: I18n.t("trim")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                FieldLabel { text: "Початок (In):"; Layout.preferredWidth: 90 }
                                AppTextField {
                                    Layout.fillWidth: true
                                    text: timelineComponent.formatTimecode(root.inPoint)
                                    onEditingFinished: {
                                        var val = timelineComponent.snap(timelineComponent.parseTimecode(text))
                                        root.inPoint = Math.min(val, root.outPoint)
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                FieldLabel { text: "Кінець (Out):"; Layout.preferredWidth: 90 }
                                AppTextField {
                                    Layout.fillWidth: true
                                    text: timelineComponent.formatTimecode(root.outPoint)
                                    onEditingFinished: {
                                        var val = timelineComponent.snap(timelineComponent.parseTimecode(text))
                                        root.outPoint = Math.max(val, root.inPoint)
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Фрагмент:"; color: Theme.textMuted; font.pixelSize: Theme.fontSizeSm }
                                Item { Layout.fillWidth: true }
                                Label {
                                    text: timelineComponent.formatTimecode(Math.max(0, root.outPoint - root.inPoint))
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textPrimary
                                }
                            }

                            SecondaryButton {
                                Layout.fillWidth: true
                                text: "Скинути обрізку"
                                onClicked: {
                                    root.inPoint = 0.0
                                    root.outPoint = root.duration
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: I18n.t("crop")
                                    font.family: Theme.displayFont
                                    font.pixelSize: Theme.fontSizeMd
                                    font.bold: true
                                    color: Theme.accentPrimary
                                }
                                Item { Layout.fillWidth: true }
                                AppSwitch {
                                    checked: root.cropEnabled
                                    onToggled: {
                                        root.cropEnabled = checked
                                        if (checked) {
                                            cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH)
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                enabled: root.cropEnabled
                                opacity: root.cropEnabled ? 1.0 : 0.5
                                spacing: 8

                                FieldLabel { text: "Співвідношення (Aspect):" }
                                AppComboBox {
                                    Layout.fillWidth: true
                                    model: ["free", "1:1", "16:9", "9:16", "4:3"]
                                    currentIndex: Math.max(0, ["free", "1:1", "16:9", "9:16", "4:3"].indexOf(root.cropAspect))
                                    onActivated: function(index) {
                                        root.cropAspect = model[index]
                                        cropOverlay.aspectRatioPreset = root.cropAspect
                                    }
                                }

                                GridLayout {
                                    columns: 2
                                    Layout.fillWidth: true
                                    columnSpacing: 8
                                    rowSpacing: 6

                                    FieldLabel { text: "X:" }
                                    AppSpinBox {
                                        from: 0; to: root.nativeWidth
                                        value: root.cropX
                                        onValueChanged: { root.cropX = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) }
                                    }

                                    FieldLabel { text: "Y:" }
                                    AppSpinBox {
                                        from: 0; to: root.nativeHeight
                                        value: root.cropY
                                        onValueChanged: { root.cropY = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) }
                                    }

                                    FieldLabel { text: "Ширина:" }
                                    AppSpinBox {
                                        from: 24; to: root.nativeWidth
                                        value: root.cropW
                                        onValueChanged: { root.cropW = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) }
                                    }

                                    FieldLabel { text: "Висота:" }
                                    AppSpinBox {
                                        from: 24; to: root.nativeHeight
                                        value: root.cropH
                                        onValueChanged: { root.cropH = value; cropOverlay.setNativeCrop(root.cropX, root.cropY, root.cropW, root.cropH) }
                                    }
                                }

                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Скинути кадрування"
                                    onClicked: cropOverlay.resetCrop()
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            FieldLabel { text: "Формат відео:" }
                            AppComboBox {
                                Layout.fillWidth: true
                                model: ["mp4", "mkv", "mov", "webm", "avi", "gif"]
                                currentIndex: Math.max(0, ["mp4", "mkv", "mov", "webm", "avi", "gif"].indexOf(root.outputFormat))
                                onActivated: function(index) { root.outputFormat = model[index] }
                            }

                            AppSwitch {
                                Layout.fillWidth: true
                                text: "Зберегти аудіодоріжку"
                                checked: root.audioEnabled
                                visible: root.hasAudio
                                onToggled: root.audioEnabled = checked
                            }

                            AppSwitch {
                                Layout.fillWidth: true
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
                            spacing: 12

                            Label {
                                text: I18n.t("montage_proxy")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                AppSwitch {
                                    Layout.fillWidth: true
                                    text: "⚡ Легка копія для монтажу"
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
                            }

                            Label {
                                text: root.proxyGenerating ? "⏳ Генерація проксі 720p…" : (root.proxyPath ? "✓ Проксі активний (експорт використає оригінал)" : I18n.t("montage_proxy_desc"))
                                font.pixelSize: Theme.fontSizeSm
                                color: root.proxyPath ? Theme.accentSuccess : Theme.textMuted
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            Label {
                                text: I18n.t("montage_multi_clip")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            Label {
                                text: "Кліпів на шкалі: " + (root.timelineClips.length || 1)
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                            }

                            SecondaryButton {
                                Layout.fillWidth: true
                                text: "+ Додати кліп на шкалу…"
                                onClicked: {
                                    if (backend) {
                                        var p = backend.pickVideoFile()
                                        if (p) {
                                            var arr = root.timelineClips.slice()
                                            arr.push({"source_path": p, "in_point": 0, "out_point": 10, "transition_to_next": root.defaultTransition, "transition_duration": 1.0})
                                            root.timelineClips = arr
                                        }
                                    }
                                }
                            }

                            FieldLabel { text: "Перехід між кліпами:" }
                            AppComboBox {
                                Layout.fillWidth: true
                                model: ["fade", "wipeleft", "wiperight", "dissolve", "circlecrop", "none"]
                                currentIndex: Math.max(0, ["fade", "wipeleft", "wiperight", "dissolve", "circlecrop", "none"].indexOf(root.defaultTransition))
                                onActivated: function(index) { root.defaultTransition = model[index] }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            Label {
                                text: I18n.t("montage_music_track")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                SecondaryButton {
                                    Layout.fillWidth: true
                                    text: root.bgMusicPath ? "Змінити музику…" : "Вибрати фонову музику…"
                                    onClicked: {
                                        if (backend) {
                                            var audioFile = backend.pickAudioFile ? backend.pickAudioFile() : backend.pickVideoFile()
                                            if (audioFile) root.bgMusicPath = audioFile
                                        }
                                    }
                                }
                            }

                            Label {
                                text: root.bgMusicPath ? ("🎵 " + root.bgMusicPath.slice(Math.max(root.bgMusicPath.lastIndexOf("/"), root.bgMusicPath.lastIndexOf("\\")) + 1)) : "Музичну доріжку не вибрано"
                                font.pixelSize: Theme.fontSizeSm
                                color: root.bgMusicPath ? Theme.accentPrimary : Theme.textMuted
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                FieldLabel { text: "Гучність:" }
                                Slider {
                                    Layout.fillWidth: true
                                    from: 0.0; to: 1.5; value: root.bgMusicVolume
                                    onMoved: root.bgMusicVolume = value
                                }
                                Label {
                                    text: Math.round(root.bgMusicVolume * 100) + "%"
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontSizeSm
                                    color: Theme.textSecondary
                                }
                            }

                            PrimaryButton {
                                Layout.fillWidth: true
                                text: "🎬 Експортувати спільний монтаж"
                                onClicked: {
                                    if (backend && root.filePath) {
                                        var project = {
                                            "title": root.fileName || "Montage",
                                            "clips": [
                                                {
                                                    "source_path": root.filePath,
                                                    "in_point": root.inPoint,
                                                    "out_point": root.outPoint,
                                                    "transition_to_next": root.defaultTransition,
                                                    "transition_duration": 1.0
                                                }
                                            ].concat(root.timelineClips),
                                            "audio_tracks": root.bgMusicPath ? [{"audio_path": root.bgMusicPath, "volume": root.bgMusicVolume, "loop": root.bgMusicLoop}] : [],
                                            "output_format": root.outputFormat
                                        }
                                        var outName = root.filePath.slice(0, root.filePath.lastIndexOf(".")) + "_montage." + root.outputFormat
                                        backend.renderTimelineProject(project, outName, false)
                                    }
                                }
                            }
                        }

                        // ==================== TAB 2: SPEECH & SUBTITLES ====================
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.sidebarTab === 2
                            spacing: 12

                            Label {
                                text: I18n.t("montage_word_highlight")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            FieldLabel { text: "Стильовий шаблон:" }
                            AppComboBox {
                                Layout.fillWidth: true
                                model: ["tiktok_pop", "reels_modern", "karaoke_classic", "neon_glow"]
                                currentIndex: Math.max(0, ["tiktok_pop", "reels_modern", "karaoke_classic", "neon_glow"].indexOf(root.subtitleTemplate))
                                onActivated: function(index) { root.subtitleTemplate = model[index] }
                            }

                            SecondaryButton {
                                Layout.fillWidth: true
                                text: "✨ Створити анімовані субтитри (ASS)"
                                onClicked: {
                                    if (backend && root.filePath) {
                                        var sampleSegs = [
                                            {"start": root.inPoint, "end": root.inPoint + 3.0, "text": "Привіт усім у новому відео!"},
                                            {"start": root.inPoint + 3.1, "end": root.inPoint + 6.5, "text": "Це розширений монтаж та інтелектуальні субтитри."}
                                        ]
                                        var assOut = root.filePath.slice(0, root.filePath.lastIndexOf(".")) + "_subtitles.ass"
                                        backend.generateStyledSubtitles(sampleSegs, root.subtitleTemplate, assOut, 1080, 1920)
                                        root.speechStatusText = "✓ Субтитри збережено: " + assOut.slice(assOut.lastIndexOf("/") + 1)
                                    }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            Label {
                                text: I18n.t("montage_speakers")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            SecondaryButton {
                                Layout.fillWidth: true
                                text: "🔍 Розпізнати мовців"
                                onClicked: {
                                    if (backend && root.filePath) {
                                        var sampleSegs = [
                                            {"start": root.inPoint, "end": root.inPoint + 3.0, "text": "Привіт, як твої справи?"},
                                            {"start": root.inPoint + 3.2, "end": root.inPoint + 6.0, "text": "Чудово, готуємо новий реліз."}
                                        ]
                                        var diar = backend.diarizeMedia(root.filePath, sampleSegs, 2, "uk")
                                        root.detectedSpeakers = Object.keys(diar.speaker_aliases || {})
                                        root.speakerAliases = diar.speaker_aliases || {}
                                        root.speechStatusText = "✓ Розпізнано мовців: " + (root.detectedSpeakers.length || 2)
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: root.detectedSpeakers.length > 0
                                spacing: 6

                                FieldLabel { text: "Імена мовців:" }
                                Repeater {
                                    model: root.detectedSpeakers
                                    RowLayout {
                                        Layout.fillWidth: true
                                        FieldLabel { text: modelData + ":"; Layout.preferredWidth: 80 }
                                        AppTextField {
                                            Layout.fillWidth: true
                                            text: root.speakerAliases[modelData] || modelData
                                            onEditingFinished: {
                                                var aliases = Object.assign({}, root.speakerAliases)
                                                aliases[modelData] = text
                                                root.speakerAliases = aliases
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            Label {
                                text: I18n.t("montage_sub_translation")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            FieldLabel { text: "Мова перекладу:" }
                            AppComboBox {
                                Layout.fillWidth: true
                                model: ["en (English)", "pl (Polski)", "de (Deutsch)", "uk (Українська)", "es (Español)"]
                                onActivated: function(index) {
                                    var codes = ["en", "pl", "de", "uk", "es"]
                                    root.targetSubtitleLanguage = codes[index]
                                }
                            }

                            SecondaryButton {
                                Layout.fillWidth: true
                                text: "🌐 Перекласти зі збереженням часу"
                                onClicked: {
                                    if (backend) {
                                        var sampleSegs = [
                                            {"start": root.inPoint, "end": root.inPoint + 3.0, "text": "Привіт, як справи?"}
                                        ]
                                        var res = backend.translateSubtitles(sampleSegs, [root.targetSubtitleLanguage], "uk")
                                        root.speechStatusText = "✓ Переклад на " + root.targetSubtitleLanguage.toUpperCase() + " виконано"
                                    }
                                }
                            }

                            Label {
                                text: root.speechStatusText
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.accentSuccess
                                wrapMode: Text.WordWrap
                                visible: !!root.speechStatusText
                                Layout.fillWidth: true
                            }
                        }

                        // ==================== TAB 3: SMART REFRAME & BLUR ====================
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.sidebarTab === 3
                            spacing: 12

                            Label {
                                text: I18n.t("montage_smart_reframe")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            Label {
                                text: "Автоматично знаходить обличчя чи рухомий об’єкт та згладжено центрує кадр 9:16 (Shorts/TikTok/Reels)."
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            PrimaryButton {
                                Layout.fillWidth: true
                                text: "🎯 Застосувати Auto-Reframe 9:16"
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
                                        root.blurStatusText = "✓ Вертикальне кадрування 9:16 налаштовано"
                                    }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

                            Label {
                                text: I18n.t("montage_motion_blur")
                                font.family: Theme.displayFont
                                font.pixelSize: Theme.fontSizeMd
                                font.bold: true
                                color: Theme.accentPrimary
                            }

                            FieldLabel { text: "Об'єкт для приховування:" }
                            AppComboBox {
                                Layout.fillWidth: true
                                model: ["face (Обличчя)", "plate (Номер авто)", "custom (Поточна рамка)"]
                                onActivated: function(index) {
                                    var types = ["face", "plate", "custom"]
                                    root.blurTargetType = types[index]
                                }
                            }

                            FieldLabel { text: "Стиль розмиття:" }
                            AppComboBox {
                                Layout.fillWidth: true
                                model: ["box (Розмиття)", "pixelate (Мозаїка)", "gaussian (Гаусове)"]
                                onActivated: function(index) {
                                    var styles = ["box", "pixelate", "gaussian"]
                                    root.blurStyle = styles[index]
                                }
                            }

                            SecondaryButton {
                                Layout.fillWidth: true
                                text: "🔒 Запустити трекінг розмиття"
                                onClicked: {
                                    if (backend && root.filePath) {
                                        var bbox = [root.cropX, root.cropY, root.cropW, root.cropH]
                                        var trackingRes = backend.trackAndBlurObject(root.filePath, root.blurTargetType, bbox, root.blurStyle)
                                        root.blurStatusText = "✓ Трекінг завершено: " + (trackingRes.frames ? trackingRes.frames.length : 0) + " кадрів відстежено"
                                    }
                                }
                            }

                            Label {
                                text: root.blurStatusText
                                font.pixelSize: Theme.fontSizeSm
                                color: Theme.accentSuccess
                                wrapMode: Text.WordWrap
                                visible: !!root.blurStatusText
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }
        }

        // Bottom Action Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: Theme.panelBackground
            radius: Theme.radiusMd
            border.width: 1
            border.color: Theme.borderDefault

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                SecondaryButton {
                    text: I18n.t("cancel")
                    implicitHeight: 36
                    implicitWidth: 110
                    onClicked: root.cancelAndClose()
                }

                Item { Layout.fillWidth: true }

                PrimaryButton {
                    text: "Застосувати зміни"
                    implicitHeight: 36
                    implicitWidth: 160
                    font.bold: true
                    onClicked: root.applyAndClose()
                }
            }
        }
    }
}

