import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import App 1.0
import "../components"
Rectangle {
    id: root
    property var editor
    property bool playing: false
    property bool safeArea: false
    property bool guides: false
    property real zoomFactor: 1
    property real volume: 1
    property string proxyPath: ""
    property int quality: 0
    property bool proxyBusy: false
    property string playbackError: ""
    readonly property real sourcePosition: editor.isImage ? editor.playhead - editor.previewEntry.start : player.position / 1000
    readonly property string sourcePath: proxyPath || editor.filePath
    color: EditorTheme.background; clip: true
    function pause() { playing = false; player.pause() }
    function togglePlayback() {
        if (!editor.duration) return
        if (playing) pause()
        else { if (editor.playhead >= editor.duration - 1/editor.fps) editor.seek(0); playing = true; if (!editor.isImage) player.play() }
    }
    function seekSource() { if (!editor.isImage) player.position = Math.round(((editor.previewClip.in_point || 0) + editor.playhead - editor.previewEntry.start) * 1000) }
    function syncCrop() { cropOverlay.setNativeCrop(editor.cropX, editor.cropY, editor.cropW, editor.cropH) }
    function nextFrame(delta) { pause(); editor.seek(editor.playhead + delta / editor.fps) }
    function advance(value) {
        if (value >= editor.duration - 0.001) { if (editor.loopEnabled) editor.seek(0); else { pause(); editor.playhead = editor.duration } }
        else editor.playhead = Math.min(editor.duration, value)
    }
    function requestQuality() {
        proxyPath = ""; proxyBusy = false
        if (quality > 0 && editor.filePath && !editor.isImage) {
            var height = Math.max(180, Math.round((editor.previewClip.height || 1080) / (quality === 1 ? 2 : 4)))
            var result = backend.requestMontageProxy(editor.filePath, height)
            if (result) proxyPath = result; else proxyBusy = true
        }
    }
    Connections {
        target: editor
        function onFilePathChanged() { root.playbackError = ""; root.requestQuality(); Qt.callLater(root.seekSource) }
        function onPreviewClipChanged() { Qt.callLater(root.seekSource) }
    }
    Connections {
        target: backend
        function onMontageProxyReady(path, proxy) { if (root.quality > 0 && path === editor.filePath) { root.proxyPath = proxy; root.proxyBusy = false; root.seekSource() } }
    }
    MediaPlayer {
        id: player; objectName: "editorMediaPlayer"
        source: root.sourcePath && !editor.isImage ? editor.project.fileUrl(root.sourcePath) : ""
        videoOutput: video
        audioOutput: AudioOutput { volume: root.volume; muted: !editor.audioEnabled || !!editor.doc.tracks.audio_muted }
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.LoadedMedia) { root.seekSource(); if (root.playing) play() }
            if (mediaStatus === MediaPlayer.EndOfMedia && root.playing) root.advance(editor.previewEntry.end + .001)
        }
        onPositionChanged: {
            if (!root.playing || playbackState !== MediaPlayer.PlayingState) return
            var positionInClip = position / 1000 - (editor.previewClip.in_point || 0)
            var next = editor.previewEntry.start + positionInClip
            if (position / 1000 >= editor.previewClip.out_point - .01) next = editor.previewEntry.end + .001
            root.advance(next)
        }
        onErrorOccurred: function(error, errorString) { root.playbackError = errorString; root.pause() }
    }
    Timer { interval: 33; repeat: true; running: root.playing && editor.isImage; onTriggered: root.advance(editor.playhead + .033) }
    ColumnLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillWidth: true; implicitHeight: EditorTheme.controlHeight + 12; color: EditorTheme.panel
            RowLayout {
                anchors.fill: parent; anchors.margins: 6; spacing: 4
                Label { Layout.fillWidth: true; text: editor.fileName || I18n.t("editor.viewer"); color: EditorTheme.secondary; elide: Text.ElideMiddle; font.pixelSize: EditorTheme.smallSize }
                EditorCombo { model: ["Fit", "100%", "200%"]; implicitWidth: 78; onActivated: root.zoomFactor = currentIndex === 0 ? 1 : currentIndex === 1 ? 1.5 : 2 }
                EditorButton { iconName: "crop"; iconOnly: true; text: I18n.t("editor.crop_overlay"); checked: editor.cropOverlayVisible; enabled: editor.selected.kind === "video"; onClicked: editor.cropOverlayVisible = !editor.cropOverlayVisible }
                EditorButton { iconName: "grid"; iconOnly: true; text: I18n.t("editor.guides"); checked: root.guides; onClicked: root.guides = !root.guides }
                EditorButton { iconName: "safe-area"; iconOnly: true; text: I18n.t("editor.safe_area"); checked: root.safeArea; onClicked: root.safeArea = !root.safeArea }
                EditorButton { iconName: "expand"; iconOnly: true; text: I18n.t("editor.maximize_viewer"); checked: editor.viewerMaximized; onClicked: editor.viewerMaximized = !editor.viewerMaximized }
            }
        }
        Item {
            id: stage; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 100; clip: true
            Rectangle { anchors.fill: parent; color: "#090b0e" }
            Item {
                id: frame
                anchors.centerIn: parent
                readonly property real ratio: (editor.previewClip.width || 1920) / (editor.previewClip.height || 1080)
                width: Math.min(stage.width - 24, (stage.height - 24) * ratio) * root.zoomFactor
                height: width / ratio
                onWidthChanged: Qt.callLater(root.syncCrop)
                VideoOutput { id: video; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit; visible: !!editor.filePath && !editor.isImage }
                Image { anchors.fill: parent; source: editor.isImage ? editor.project.fileUrl(editor.filePath) : ""; visible: editor.isImage; fillMode: Image.PreserveAspectFit; asynchronous: true }
                Repeater {
                    model: editor.doc.tracks.titles_visible !== false ? editor.doc.titles : []
                    Label {
                        required property var modelData
                        visible: editor.playhead >= modelData.start && editor.playhead < modelData.end
                        text: modelData.text; textFormat: Text.PlainText; font.family: modelData.font; font.pixelSize: Math.max(8, modelData.size * frame.width / editor.doc.project_settings.width); font.bold: modelData.bold
                        color: modelData.color; opacity: modelData.opacity; style: Text.Outline; styleColor: "black"
                        width: Math.min(implicitWidth, frame.width * .9); wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                        x: frame.width * modelData.x - width / 2; y: frame.height * modelData.y - height
                        background: Rectangle { visible: modelData.background; color: "#b0000000" }
                    }
                }
                Label {
                    anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: parent.height * .05
                    width: parent.width * .9; color: "white"; style: Text.Outline; styleColor: "black"; textFormat: Text.PlainText
                    horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap; font.pixelSize: Math.max(12, 42 * frame.width / editor.doc.project_settings.width)
                    text: { var cue = editor.doc.subtitles.find(function(c) { return c.start <= editor.playhead && c.end > editor.playhead }); return cue ? cue.text : "" }
                }
                Rectangle { anchors.fill: parent; anchors.margins: parent.width * .05; visible: root.safeArea; color: "transparent"; border.color: "#8099aacc" }
                Repeater { model: root.guides ? 2 : 0; Rectangle { required property int index; x: frame.width*(index+1)/3; width: 1; height: frame.height; color: "#7099aacc" } }
                Repeater { model: root.guides ? 2 : 0; Rectangle { required property int index; y: frame.height*(index+1)/3; height: 1; width: frame.width; color: "#7099aacc" } }
                CropOverlay {
                    id: cropOverlay; active: editor.cropOverlayVisible && editor.selected.kind === "video" && editor.selected.id === editor.previewClip.id
                    nativeWidth: editor.nativeWidth; nativeHeight: editor.nativeHeight; aspectRatioPreset: editor.cropAspect
                    onEditingStarted: editor.history.begin()
                    onEditingFinished: editor.history.end()
                    onCropChanged: function(x, y, w, h) { editor.setCrop(x, y, w, h) }
                    onResetRequested: editor.resetCrop()
                }
            }
            ColumnLayout {
                anchors.centerIn: parent; width: Math.min(420, parent.width - 32); visible: !editor.filePath; spacing: 12
                AppIcon { name: "film"; Layout.preferredWidth: 48; Layout.preferredHeight: 48; Layout.alignment: Qt.AlignHCenter; iconColor: EditorTheme.muted }
                Label { Layout.fillWidth: true; text: I18n.t("editor.first_edit"); color: EditorTheme.text; font.pixelSize: EditorTheme.fontSize + 5; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                Label { Layout.fillWidth: true; text: I18n.t("editor.viewer_empty"); color: EditorTheme.secondary; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                EditorButton { text: I18n.t("editor.import_media"); primary: true; iconName: "add"; Layout.alignment: Qt.AlignHCenter; onClicked: editor.project.chooseMedia() }
            }
            Label { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 8; color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize; text: root.proxyBusy ? I18n.t("editor.proxy_building") : I18n.t("editor.source_preview"); visible: !!editor.filePath }
            Label { anchors.centerIn: parent; width: parent.width - 32; visible: root.playbackError.length > 0; text: root.playbackError; wrapMode: Text.Wrap; color: EditorTheme.danger }
            DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.hasUrls) { editor.project.importMedia(drop.urls.map(function(url) { return String(url) }), true); drop.acceptProposedAction() } } }
        }
        Rectangle {
            Layout.fillWidth: true; implicitHeight: transport.implicitHeight + 16; color: EditorTheme.panel
            ColumnLayout {
                id: transport; anchors.fill: parent; anchors.margins: 8; spacing: 6
                RowLayout {
                    Layout.fillWidth: true; spacing: 4
                    Item { Layout.fillWidth: true }
                    EditorButton { iconName: "skip-back"; iconOnly: true; text: I18n.t("editor.go_start"); onClicked: { root.pause(); editor.seek(0) } }
                    EditorButton { iconName: "back"; iconOnly: true; text: I18n.t("editor.previous_frame"); onClicked: root.nextFrame(-1) }
                    EditorButton { iconName: root.playing ? "pause" : "play"; iconOnly: true; primary: true; text: I18n.t("studio.play"); enabled: editor.duration > 0; onClicked: root.togglePlayback() }
                    EditorButton { iconName: "chevron-right"; iconOnly: true; text: I18n.t("editor.next_frame"); onClicked: root.nextFrame(1) }
                    EditorButton { iconName: "skip-forward"; iconOnly: true; text: I18n.t("editor.go_end"); onClicked: { root.pause(); editor.seek(editor.duration) } }
                    EditorButton { iconName: "refresh"; iconOnly: true; text: I18n.t("editor.loop"); checked: editor.loopEnabled; onClicked: editor.loopEnabled = !editor.loopEnabled }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 6
                    Label { text: editor.timecode(editor.playhead); color: EditorTheme.text; font.family: Theme.monoFont; font.pixelSize: EditorTheme.smallSize }
                    Slider { Layout.fillWidth: true; from: 0; to: Math.max(1, editor.duration); value: editor.playhead; onMoved: { root.pause(); editor.seek(value) } }
                    EditorCombo { model: ["Full", "1/2", "1/4"]; implicitWidth: 72; enabled: !!editor.filePath && !editor.isImage; onActivated: { root.quality = currentIndex; root.requestQuality() } }
                    Slider { visible: root.width > 550; Layout.preferredWidth: 65; from: 0; to: 1; value: root.volume; onMoved: root.volume = value; ToolTip.visible: hovered; ToolTip.text: I18n.t("editor.volume") }
                }
            }
        }
    }
}
