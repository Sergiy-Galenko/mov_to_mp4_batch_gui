import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import App 1.0

Window {
    id: root
    objectName: "montageToolsWindow"
    title: I18n.t("studio.title")
    width: 1180; height: 800; minimumWidth: 960; minimumHeight: 660
    color: Theme.bgBase; modality: Qt.ApplicationModal
    visible: false
    property string sourcePath: ""
    property var options: ({duration: 0, width: 1920, height: 1080, has_audio: false})
    property var document: defaults()
    property string selectedId: ""
    property int page: 0
    property string message: ""
    property string beforeUrl: ""
    property string afterUrl: ""
    readonly property var service: backend ? backend.montageEditing : null
    readonly property bool busy: service ? service.busy : false
    readonly property var selectedCue: document.cues.find(function(cue) { return cue.id === root.selectedId }) || ({start: 0, end: 0, text: ""})
    readonly property real position: sourcePlayer.position / 1000
    readonly property string transcript: document.words.map(function(word) { return word.word.trim() }).join(" ")

    function defaults() { return {cues: [], words: [], removed: [], scenes: [], music: "", music_volume: 0.3,
        ducking: true, duck_ratio: 8, duck_release_ms: 450, burn_subtitles: false} }
    function update(values) { document = Object.assign({}, document, values) }
    function openSource(path, settings) {
        if (!path || busy) return
        editHistory.initialized = false
        sourcePath = path
        options = settings
        document = Object.assign(defaults(), {music: settings.music || "", music_volume: settings.music_volume === undefined ? 0.3 : settings.music_volume, ducking: settings.ducking !== false}, service.loadDocument(path))
        selectedId = document.cues.length ? document.cues[0].id : ""
        sourcePlayer.source = service.fileUrl(path)
        message = ""; beforeUrl = ""; afterUrl = ""
        show(); raise(); requestActivate()
        Qt.callLater(function() { editHistory.reset() })
    }
    function edit(operation, args) {
        var result = service.editCues(document.cues, operation, args)
        if (result.ok) { update({cues: result.cues}); message = "" }
        else message = result.error
    }
    function cutSelection() {
        var start = transcriptEditor.selectionStart, end = transcriptEditor.selectionEnd
        var offset = 0, first = -1, last = -1
        for (var i = 0; i < document.words.length; i++) {
            var length = document.words[i].word.trim().length
            if (offset < end && offset + length > start) { if (first < 0) first = i; last = i }
            offset += length + 1
        }
        var result = service.cutWords(document.words, first, last)
        if (!result.ok) { message = result.error; return }
        editHistory.begin()
        update({removed: document.removed.concat([result.range])})
        editHistory.end()
        message = I18n.t("studio.cut_added") + " " + result.range[0].toFixed(2) + "–" + result.range[1].toFixed(2) + " s"
    }
    function seek(seconds) { sourcePlayer.position = Math.round(seconds * 1000) }
    function save() { if (sourcePath && service && editHistory.initialized) service.saveDocument(sourcePath, document) }
    onDocumentChanged: {
        editHistory.schedule()
        if (editHistory.initialized) saveTimer.restart()
    }
    onPageChanged: { sourcePlayer.pause(); comparison.stop() }
    onClosing: {
        saveTimer.stop(); save()
        sourcePlayer.stop(); sourcePlayer.source = ""
        comparison.stop(); beforeUrl = ""; afterUrl = ""
        if (service) { service.cancel(); service.clearPreviews() }
    }
    Timer { id: saveTimer; interval: 400; onTriggered: root.save() }
    UndoHistory {
        id: editHistory
        objectName: "studioUndoHistory"
        capture: function() { return root.document }
        restore: function(state) { root.document = state }
    }
    MediaPlayer {
        id: sourcePlayer
        objectName: "studioSourcePlayer"
        videoOutput: sourceVideo
        audioOutput: AudioOutput {}
        onMediaStatusChanged: if (mediaStatus === MediaPlayer.LoadedMedia) pause()
        onErrorOccurred: function(error, errorString) { root.message = errorString }
    }
    Connections {
        target: root.service
        function onCompleted(result) {
            if (!root.visible) { root.service.clearPreviews(); return }
            if (result.source !== root.sourcePath) return
            if (result.kind === "transcript") {
                editHistory.begin()
                root.update({cues: result.cues, words: result.words, removed: []})
                root.selectedId = result.cues.length ? result.cues[0].id : ""
                editHistory.end()
                root.message = result.model + " · " + result.device.toUpperCase()
            } else if (result.kind === "scenes") {
                editHistory.begin(); root.update({scenes: result.scenes}); editHistory.end()
            } else if (result.kind === "preview") {
                root.beforeUrl = result.before; root.afterUrl = result.after; root.page = 2
            } else if (result.kind === "export") {
                root.message = I18n.t("studio.exported") + " " + result.path
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 10
        RowLayout {
            HistoryButtons { history: editHistory; targetWindow: root; enabled: !root.busy }
            Label { Layout.fillWidth: true; text: root.title; color: Theme.textPrimary; font.pixelSize: Theme.fontHeading; elide: Text.ElideRight }
            AppButton {
                text: I18n.t("studio.export_subtitles"); enabled: !root.busy && root.document.cues.length > 0
                onClicked: if (root.service.exportSubtitles(root.sourcePath, root.document, root.options)) root.message = I18n.t("studio.exported")
            }
            AppButton { text: I18n.t("studio.export_video"); enabled: !root.busy; onClicked: root.service.exportVideo(root.sourcePath, root.document, root.options) }
        }
        TabBar {
            Layout.fillWidth: true
            currentIndex: root.page
            onCurrentIndexChanged: root.page = currentIndex
            Repeater {
                model: ["studio.subtitles", "studio.text_edit", "studio.compare", "studio.music", "studio.scenes"]
                TabButton {
                    required property string modelData
                    text: I18n.t(modelData)
                    contentItem: Label { text: parent.text; color: parent.checked ? Theme.textOnAccent : Theme.textPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle { color: parent.checked ? Theme.accent : Theme.panelSecondary; radius: Theme.radiusSm }
                }
            }
        }
        RowLayout {
            visible: root.page !== 2
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "#101010"
                    VideoOutput { id: sourceVideo; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
                    Label {
                        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - 32; anchors.bottomMargin: 18
                        text: { var cue = root.document.cues.find(function(c) { return c.start <= root.position && c.end > root.position }); return cue ? cue.text : "" }
                        textFormat: Text.PlainText; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                        color: "white"; style: Text.Outline; styleColor: "black"; font.pixelSize: 20
                    }
                }
                RowLayout {
                    AppButton {
                        text: sourcePlayer.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
                        Accessible.name: I18n.t("studio.play")
                        onClicked: sourcePlayer.playbackState === MediaPlayer.PlayingState ? sourcePlayer.pause() : sourcePlayer.play()
                    }
                    Slider { Layout.fillWidth: true; from: 0; to: Math.max(1, root.options.duration); value: root.position; onMoved: root.seek(value) }
                    Label { text: root.position.toFixed(2) + " s"; color: Theme.textSecondary }
                }
            }
            StackLayout {
                Layout.preferredWidth: 430; Layout.fillHeight: true
                currentIndex: root.page > 2 ? root.page - 1 : root.page
                enabled: !root.busy
                // Subtitles
                ColumnLayout {
                    RowLayout {
                        AppButton {
                            text: I18n.t("studio.import")
                            onClicked: {
                                var path = root.service.chooseFile("subtitles")
                                if (!path) return
                                var result = root.service.importSubtitles(path)
                                if (result.ok) { editHistory.begin(); root.update({cues: result.cues}); root.selectedId = result.cues[0].id; editHistory.end() }
                                else root.message = result.error
                            }
                        }
                        AppButton { text: "Whisper"; onClicked: root.service.transcribe(root.sourcePath) }
                        AppButton { text: "+"; Accessible.name: I18n.t("studio.add_cue"); onClicked: root.edit("add", {start: root.position, end: Math.min(root.options.duration, root.position + 2), text: "…", duration: root.options.duration}) }
                    }
                    Label { Layout.fillWidth: true; text: I18n.t("studio.alignment_hint"); wrapMode: Text.Wrap; color: Theme.textMuted; font.pixelSize: Theme.fontSmall }
                    ListView {
                        objectName: "subtitleCuesList"
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 90
                        clip: true; model: root.document.cues; spacing: 4
                        ScrollBar.vertical: ScrollBar {}
                        delegate: ItemDelegate {
                            required property var modelData
                            width: ListView.view.width; height: 60
                            highlighted: modelData.id === root.selectedId
                            onClicked: { root.selectedId = modelData.id; root.seek(modelData.start) }
                            contentItem: Column {
                                Label { text: modelData.start.toFixed(2) + " → " + modelData.end.toFixed(2) + " s"; color: Theme.textSecondary }
                                Label { width: parent.width; text: modelData.text; textFormat: Text.PlainText; elide: Text.ElideRight; color: Theme.textPrimary }
                            }
                            background: Rectangle { color: parent.highlighted ? Theme.selectionBackground : Theme.panelSecondary; radius: Theme.radiusSm }
                        }
                    }
                    TextArea {
                        id: captionText
                        objectName: "subtitleTextEditor"
                        Layout.fillWidth: true; Layout.preferredHeight: 85
                        enabled: !!root.selectedCue.id
                        text: root.selectedCue.text; textFormat: TextEdit.PlainText
                        wrapMode: TextEdit.Wrap; selectByMouse: true; color: Theme.textPrimary
                        background: Rectangle { color: Theme.input; radius: Theme.radiusSm }
                        onTextChanged: if (activeFocus && root.selectedCue.id && text !== root.selectedCue.text) root.edit("update", {id: root.selectedId, values: {text: text}})
                    }
                    RowLayout {
                        AppTextField { Layout.fillWidth: true; text: root.selectedCue.start.toFixed(3); enabled: !!root.selectedCue.id; onEditingFinished: root.edit("update", {id: root.selectedId, values: {start: Number(text.replace(",", "."))}, duration: root.options.duration}) }
                        Label { text: "→"; color: Theme.textSecondary }
                        AppTextField { Layout.fillWidth: true; text: root.selectedCue.end.toFixed(3); enabled: !!root.selectedCue.id; onEditingFinished: root.edit("update", {id: root.selectedId, values: {end: Number(text.replace(",", "."))}, duration: root.options.duration}) }
                    }
                    RowLayout {
                        AppButton { text: I18n.t("studio.split"); enabled: !!root.selectedCue.id; onClicked: root.edit("split", {id: root.selectedId, at: root.position, cursor: captionText.cursorPosition}) }
                        AppButton { text: I18n.t("studio.merge"); enabled: !!root.selectedCue.id; onClicked: root.edit("merge", {id: root.selectedId}) }
                        AppButton { text: "−"; Accessible.name: I18n.t("studio.delete_cue"); enabled: !!root.selectedCue.id; onClicked: root.edit("delete", {id: root.selectedId}) }
                    }
                    Label { Layout.fillWidth: true; text: I18n.t("studio.split_hint"); wrapMode: Text.Wrap; color: Theme.textMuted; font.pixelSize: Theme.fontSmall }
                    AppCheckBox { text: I18n.t("studio.burn"); checked: root.document.burn_subtitles; onClicked: root.update({burn_subtitles: checked}) }
                }
                // Text-based cuts
                ColumnLayout {
                    Label { Layout.fillWidth: true; text: I18n.t("studio.text_hint"); wrapMode: Text.Wrap; color: Theme.textSecondary }
                    AppButton { text: I18n.t("studio.transcribe"); onClicked: root.service.transcribe(root.sourcePath) }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        TextArea {
                            id: transcriptEditor
                            objectName: "timedTranscript"
                            width: parent.width; text: root.transcript; color: Theme.textPrimary
                            wrapMode: TextEdit.Wrap; textFormat: TextEdit.PlainText
                            readOnly: true; selectByMouse: true; persistentSelection: true
                        }
                    }
                    AppButton { text: I18n.t("studio.cut_words"); enabled: transcriptEditor.selectionEnd > transcriptEditor.selectionStart; onClicked: root.cutSelection() }
                    Label { text: I18n.t("studio.cuts") + ": " + root.document.removed.length; color: Theme.textSecondary }
                    AppButton { text: I18n.t("studio.restore_cuts"); enabled: root.document.removed.length > 0; onClicked: root.update({removed: []}) }
                }
                // Background music
                ColumnLayout {
                    AppButton { text: I18n.t("studio.choose_music"); onClicked: { var path = root.service.chooseFile("music"); if (path) root.update({music: path}) } }
                    Label { Layout.fillWidth: true; text: root.document.music; color: Theme.textSecondary; elide: Text.ElideMiddle }
                    AppButton { text: I18n.t("studio.remove_music"); enabled: !!root.document.music; onClicked: root.update({music: ""}) }
                    Label { text: I18n.t("studio.volume") + " " + Math.round(root.document.music_volume * 100) + "%"; color: Theme.textPrimary }
                    Slider { Layout.fillWidth: true; from: 0; to: 1; value: root.document.music_volume; onMoved: root.update({music_volume: value}) }
                    AppCheckBox { text: I18n.t("studio.ducking"); checked: root.document.ducking; onClicked: root.update({ducking: checked}) }
                    Label { Layout.fillWidth: true; text: I18n.t("studio.duck_hint"); wrapMode: Text.Wrap; color: Theme.textSecondary }
                    RowLayout {
                        Label { text: I18n.t("studio.duck_strength"); color: Theme.textSecondary }
                        AppSpinBox { from: 2; to: 20; value: root.document.duck_ratio; onValueModified: root.update({duck_ratio: value}) }
                    }
                    RowLayout {
                        Label { text: I18n.t("studio.release"); color: Theme.textSecondary }
                        AppSpinBox { from: 50; to: 3000; stepSize: 50; value: root.document.duck_release_ms; onValueModified: root.update({duck_release_ms: value}) }
                    }
                    Item { Layout.fillHeight: true }
                }
                // Scene boundaries
                ColumnLayout {
                    Label { Layout.fillWidth: true; text: I18n.t("studio.scene_hint"); wrapMode: Text.Wrap; color: Theme.textSecondary }
                    RowLayout {
                        AppSpinBox { id: sceneThreshold; from: 5; to: 90; value: 35 }
                        AppButton { text: I18n.t("studio.detect"); onClicked: root.service.detectScenes(root.sourcePath, root.options.duration, sceneThreshold.value / 100) }
                    }
                    ListView {
                        objectName: "detectedScenesList"
                        Layout.fillWidth: true; Layout.fillHeight: true; model: root.document.scenes; clip: true
                        ScrollBar.vertical: ScrollBar {}
                        delegate: RowLayout {
                            required property var modelData
                            required property int index
                            width: ListView.view.width
                            AppCheckBox {
                                checked: modelData.selected
                                onClicked: { var scenes = root.document.scenes.slice(); scenes[index] = Object.assign({}, modelData, {selected: checked}); root.update({scenes: scenes}) }
                            }
                            AppButton { Layout.fillWidth: true; text: (index + 1) + " · " + modelData.start.toFixed(2) + "–" + modelData.end.toFixed(2) + " s"; onClicked: root.seek(modelData.start) }
                        }
                    }
                    AppButton { text: I18n.t("studio.export_scenes"); enabled: root.document.scenes.some(function(scene) { return scene.selected }); onClicked: root.service.exportScenes(root.sourcePath, root.document.scenes, root.options) }
                }
            }
        }
        ColumnLayout {
            visible: root.page === 2
            Layout.fillWidth: true; Layout.fillHeight: true
            RowLayout {
                AppButton {
                    text: I18n.t("studio.make_preview"); enabled: !root.busy
                    onClicked: { comparison.stop(); root.beforeUrl = ""; root.afterUrl = ""; root.service.clearPreviews(); root.service.preview(root.sourcePath, root.document, root.options, root.position) }
                }
                Label { Layout.fillWidth: true; text: I18n.t("studio.preview_hint"); wrapMode: Text.Wrap; color: Theme.textSecondary }
            }
            BeforeAfterPlayer { id: comparison; objectName: "studioComparison"; Layout.fillWidth: true; Layout.fillHeight: true; beforeSource: root.beforeUrl; afterSource: root.afterUrl }
        }
        SubtitleCueTimeline {
            visible: root.page !== 2
            Layout.fillWidth: true
            cues: root.document.cues; scenes: root.document.scenes; selectedCue: root.selectedCue
            duration: Math.max(0.1, root.options.duration); position: root.position
            enabled: !root.busy
            onSeekRequested: function(seconds) { root.seek(seconds) }
            onRangeChanged: function(start, end) { root.edit("update", {id: root.selectedId, values: {start: start, end: end}, duration: root.options.duration}) }
            onEditingStarted: editHistory.begin()
            onEditingFinished: editHistory.end()
        }
        RowLayout {
            visible: root.busy; Layout.fillWidth: true
            BusyIndicator { running: root.busy; Layout.preferredWidth: 26; Layout.preferredHeight: 26 }
            Label { text: root.service ? I18n.t("setup." + root.service.stage) : ""; color: Theme.textSecondary }
            ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: root.service ? root.service.progress : 0; indeterminate: root.service && root.service.stage === "recognizing" }
            AppButton { text: I18n.t("cancel"); onClicked: root.service.cancel() }
        }
        Label {
            Layout.fillWidth: true; maximumLineCount: 3; elide: Text.ElideRight; wrapMode: Text.Wrap
            color: root.service && root.service.error ? Theme.accentWarn : Theme.textSecondary
            text: root.service && root.service.error ? root.service.error : root.message
            visible: text.length > 0
        }
    }
}
