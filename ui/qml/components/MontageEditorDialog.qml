import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCore
import App 1.0
import "../editor"

Window {
    id: root
    title: displayProjectName + (project && project.dirty ? " *" : "") + " — " + I18n.t("nav_montage")
    width: 1440; height: 900
    minimumWidth: 980; minimumHeight: 680
    color: EditorTheme.background
    flags: Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
    visible: false
    readonly property var project: backend ? backend.editorProject : null
    readonly property var render: backend ? backend.editorRender : null
    readonly property var doc: project ? project.data : ({project_name: "", project_settings: {width: 1920, height: 1080, fps: 30}, timeline: {clips: [], audio_tracks: []}, media: [], titles: [], subtitles: [], tracks: {}, export_settings: {}, editing_documents: {}})
    readonly property string displayProjectName: !doc.project_name || doc.project_name === "Untitled Project" ? I18n.t("editor.untitled") : doc.project_name
    readonly property var selected: project ? project.selected : ({})
    property bool syncing: false
    property bool allowClose: false
    property string pendingAction: ""
    property string pendingPath: ""
    property bool mediaPoolVisible: true
    property bool inspectorVisible: true
    readonly property bool compactLayout: width < 1180
    property bool compactInspectorMode: false
    property bool viewerMaximized: false
    property int activeWorkspacePage: 2
    property string activeWorkspace: "edit"
    property int libraryPage: 0
    property int inspectorTab: 0
    property real playhead: 0
    property real timelineZoom: 1
    property bool snappingEnabled: true
    property bool bladeTool: false
    property bool loopEnabled: false
    property string waveformPath: ""
    property bool cropOverlayVisible: false
    property string message: ""
    property var clipboardClip: null
    readonly property var history: editHistory
    readonly property bool textEditing: activeFocusItem && (typeof activeFocusItem.selectAll === "function")
    readonly property var timelineClips: doc.timeline.clips
    readonly property var clipLayout: {
        var result = [], start = 0
        for (var i = 0; i < timelineClips.length; i++) {
            var c = timelineClips[i]
            var length = Math.max(0.001, c.out_point - c.in_point)
            result.push({id: c.id, index: i, start: start, end: start + length, duration: length, clip: c})
            var overlap = i + 1 < timelineClips.length && c.transition_to_next !== "none"
                ? Math.min(c.transition_duration || 0.5, (timelineClips[i + 1].out_point - timelineClips[i + 1].in_point) / 2, 5) : 0
            start += length - overlap
        }
        return result
    }
    readonly property real duration: clipLayout.length ? clipLayout[clipLayout.length - 1].end : 0
    readonly property var previewEntry: {
        for (var i = clipLayout.length - 1; i >= 0; i--) if (playhead >= clipLayout[i].start) return clipLayout[i]
        return clipLayout.length ? clipLayout[0] : ({start: 0, clip: {}})
    }
    readonly property var previewClip: previewEntry.clip
    readonly property string filePath: previewClip.source_path || ""
    readonly property string fileName: previewClip.name || ""
    readonly property int nativeWidth: selected.width || doc.project_settings.width
    readonly property int nativeHeight: selected.height || doc.project_settings.height
    readonly property real fps: doc.project_settings.fps
    readonly property bool hasAudio: !!previewClip.has_audio
    readonly property bool isImage: previewClip.media_type === "image"
    property real inPoint: 0
    property real outPoint: 0
    property bool cropEnabled: false
    property int cropX: 0
    property int cropY: 0
    property int cropW: 1920
    property int cropH: 1080
    property string cropAspect: "free"
    property bool audioEnabled: true
    readonly property string outputFormat: doc.export_settings.format || "mp4"
    readonly property bool fastCopy: !!doc.export_settings.fast_copy
    readonly property var editState: ({document: doc, empty: timelineClips.length ? {} : {inPoint: inPoint, outPoint: outPoint, cropEnabled: cropEnabled, cropX: cropX, cropY: cropY, cropW: cropW, cropH: cropH, cropAspect: cropAspect}})
    onEditStateChanged: editHistory.schedule()
    onInPointChanged: if (!syncing && selected.kind === "video") project.editSelected({in_point: inPoint})
    onOutPointChanged: if (!syncing && selected.kind === "video") project.editSelected({out_point: outPoint, still_duration: outPoint - inPoint})
    onCropEnabledChanged: updateCrop()
    onCropXChanged: updateCrop()
    onCropYChanged: updateCrop()
    onCropWChanged: updateCrop()
    onCropHChanged: updateCrop()
    onCropAspectChanged: if (!syncing && selected.kind === "video") project.editSelected({crop_aspect: cropAspect})
    onAudioEnabledChanged: if (!syncing && selected.kind === "video") project.editSelected({audio_enabled: audioEnabled})

    function updateCrop() {
        if (!syncing && selected.kind === "video") project.editSelected({crop: cropEnabled ? [cropX, cropY, cropW, cropH] : []})
    }
    function syncSelection() {
        syncing = true
        var c = selected, crop = c.crop || []
        inPoint = c.in_point || 0; outPoint = c.out_point || 0
        cropEnabled = crop.length === 4
        cropX = crop[0] || 0; cropY = crop[1] || 0
        cropW = crop[2] || nativeWidth; cropH = crop[3] || nativeHeight
        cropAspect = c.crop_aspect || "free"; audioEnabled = c.audio_enabled !== false
        syncing = false
        viewer.syncCrop()
    }
    function resetCrop() {
        editHistory.begin(); syncing = true
        cropX = 0; cropY = 0; cropW = nativeWidth; cropH = nativeHeight; cropEnabled = false; cropAspect = "free"
        syncing = false; project.editSelected({crop: [], crop_aspect: "free"}); editHistory.end()
    }
    function setCrop(x, y, w, h) {
        syncing = true; cropX = x; cropY = y; cropW = w; cropH = h; cropEnabled = true; syncing = false; updateCrop()
    }
    function timecode(value) {
        var frames = Math.max(0, Math.round(value * fps)), rate = Math.max(1, Math.round(fps))
        function pad(n) { return ("0" + n).slice(-2) }
        return pad(Math.floor(frames / rate / 3600)) + ":" + pad(Math.floor(frames / rate / 60) % 60) + ":" + pad(Math.floor(frames / rate) % 60) + ":" + pad(frames % rate)
    }
    function seek(value) { playhead = Math.max(0, Math.min(duration, value)); viewer.seekSource() }
    function selectClip(id) {
        project.select(id)
        for (var i = 0; i < clipLayout.length; i++) if (clipLayout[i].id === id) { seek(clipLayout[i].start); break }
        inspectorVisible = true
        if (compactLayout) compactInspectorMode = true
    }
    function splitAtPlayhead() { editHistory.begin(); project.split(playhead); editHistory.end() }
    function markIn() { if (selected.kind === "video") inPoint = Math.min(outPoint - 1/fps, viewer.sourcePosition) }
    function markOut() { if (selected.kind === "video") outPoint = Math.max(inPoint + 1/fps, viewer.sourcePosition) }
    function togglePlayback() { viewer.togglePlayback() }
    function chooseWorkspace(workspace) {
        var key = typeof workspace === "number"
            ? ["media", "titles", "edit", "color", "audio", "deliver"][workspace]
            : workspace
        activeWorkspace = key || "edit"
        activeWorkspacePage = ["media", "titles", "edit", "color", "audio", "deliver"].indexOf(activeWorkspace)
        if (activeWorkspace === "media") {
            mediaPoolVisible = true; libraryPage = 0; compactInspectorMode = false
        } else if (activeWorkspace === "titles") {
            mediaPoolVisible = true; libraryPage = 1; inspectorVisible = true; inspectorTab = 2; compactInspectorMode = false
        } else if (activeWorkspace === "edit") {
            mediaPoolVisible = true; libraryPage = 0; inspectorVisible = true; inspectorTab = 0; compactInspectorMode = false
        } else {
            mediaPoolVisible = false; inspectorVisible = true; compactInspectorMode = true
            inspectorTab = activeWorkspace === "color" ? 3 : activeWorkspace === "audio" ? 1 : 4
        }
    }
    function openTools() {
        if (!filePath || backend.montageEditing.busy) return
        viewer.pause()
        editingTools.openSource(filePath, {duration: previewClip.source_duration || duration, width: nativeWidth, height: nativeHeight, fps: fps,
            has_audio: hasAudio, start: inPoint, end: outPoint, crop: cropEnabled ? [cropX,cropY,cropW,cropH] : []})
        if (doc.editing_documents[filePath]) editingTools.document = doc.editing_documents[filePath]
    }
    function requestAction(action, path) {
        if (project.saving || project.importer.busy) { message = I18n.t("editor.wait_operation"); return }
        pendingAction = action; pendingPath = path || ""
        if (project.dirty) unsavedDialog.open()
        else performPending()
    }
    function performPending() {
        var action = pendingAction, path = pendingPath
        pendingAction = ""; pendingPath = ""
        viewer.pause()
        if (action === "close") { allowClose = true; root.close(); allowClose = false }
        else if (action === "new") projectDialog.openNew()
        else if (action === "open") { var chosen = path || project.chooseProject(); if (chosen) project.open(chosen) }
        else if (action === "source") loadSourceProject(path)
        else if (action === "empty") project.create(I18n.t("editor.untitled"), {})
        else if (action === "recover") project.recover(path)
    }
    function loadSourceProject(path) {
        project.create(path ? path.split(/[\\/]/).pop().replace(/\.[^.]+$/, "") : I18n.t("editor.untitled"), {})
        if (path) project.importMedia([path], true)
        playhead = 0
    }
    function openForFile(path) {
        if (visible && project.dirty) requestAction("source", path)
        else if (!visible || path || !project.dirty) loadSourceProject(path)
        show(); raise(); requestActivate()
        if (!path && project.recoveries.length) recoveryDialog.open()
    }
    function openExport() { viewer.pause(); exportDialog.open() }
    function applyAndClose() {
        if (filePath && selected.kind === "video") {
            var session = {in_point: inPoint, out_point: outPoint, crop_x: cropEnabled ? cropX : null, crop_y: cropEnabled ? cropY : null,
                crop_w: cropEnabled ? cropW : null, crop_h: cropEnabled ? cropH : null, crop_aspect: cropAspect,
                audio_enabled: audioEnabled, output_format: outputFormat, fast_copy: fastCopy && !cropEnabled && !isImage, is_image: isImage,
                still_duration: outPoint-inPoint, media_type: isImage ? "image" : "video"}
            backend.applyMontageToTask(filePath, session)
            applied(filePath, session)
            message = I18n.t("editor.applied")
        }
    }
    function cancelAndClose() { requestAction("close", "") }
    function copyClip() { clipboardClip = selected.kind === "video" ? JSON.parse(JSON.stringify(selected)) : null }
    function pasteClip() { if (clipboardClip) project.duplicateClip(clipboardClip) }
    signal applied(string path, var sessionData)
    signal cancelled()
    onClosing: function(event) {
        if (!allowClose && project && project.dirty) { event.accepted = false; requestAction("close", ""); return }
        viewer.pause()
        if (render && render.busy) { event.accepted = false; message = I18n.t("editor.render_running"); return }
    }

    UndoHistory {
        id: editHistory; objectName: "montageUndoHistory"
        capture: function() { return root.editState }
        restore: function(state) {
            root.project.restore(state.document)
            root.syncing = true
            for (var key in state.empty) root[key] = state.empty[key]
            root.syncing = false
        }
    }
    Connections {
        target: root.project
        function onLoaded() { root.playhead = 0; root.message = ""; root.syncSelection(); Qt.callLater(function() { editHistory.reset() }) }
        function onSelectionChanged() { root.syncSelection() }
        function onSaved() { if (root.pendingAction && !root.project.dirty) root.performPending() }
    }
    Connections {
        target: backend
        function onMontageWaveformReady(path, waveform) { if (path === root.filePath) root.waveformPath = waveform }
    }
    onFilePathChanged: {
        waveformPath = ""
        if (backend && filePath && !isImage) backend.requestMontageWaveform(filePath)
    }
    MontageToolsWindow {
        id: editingTools; transientParent: root
        onDocumentChanged: if (visible && sourcePath && root.project && editHistory.initialized) {
            var docs = {}; docs[sourcePath] = document; root.project.updateSection("editing_documents", docs)
        }
    }
    Settings {
        id: workspaceSettings; category: "EditorWorkspaceV1"
        property real mediaWidth: 250
        property real inspectorWidth: 300
        property real timelineHeight: 270
    }
    Shortcut { sequences: [StandardKey.Save]; enabled: root.active; onActivated: project.save() }
    Shortcut { sequences: [StandardKey.SaveAs]; enabled: root.active; onActivated: project.saveAs() }
    Shortcut { sequences: [StandardKey.Open]; enabled: root.active; onActivated: root.requestAction("open", "") }
    Shortcut { sequences: [StandardKey.New]; enabled: root.active; onActivated: root.requestAction("new", "") }
    Shortcut { sequences: [StandardKey.Undo]; enabled: root.active && !root.textEditing; onActivated: editHistory.undo() }
    Shortcut { sequences: [StandardKey.Redo]; enabled: root.active && !root.textEditing; onActivated: editHistory.redo() }
    Shortcut { sequence: Qt.platform.os === "osx" ? "Meta+I" : "Ctrl+I"; enabled: root.active; onActivated: project.chooseMedia() }
    Shortcut { sequence: Qt.platform.os === "osx" ? "Meta+E" : "Ctrl+E"; enabled: root.active; onActivated: root.openExport() }
    Shortcut { sequence: "Space"; enabled: root.active && !root.textEditing; onActivated: root.togglePlayback() }
    Shortcut { sequence: "B"; enabled: root.active && !root.textEditing; onActivated: root.bladeTool = true }
    Shortcut { sequence: "A"; enabled: root.active && !root.textEditing; onActivated: root.bladeTool = false }
    Shortcut { sequence: "C"; enabled: root.active && !root.textEditing; onActivated: root.bladeTool = true }
    Shortcut { sequence: "V"; enabled: root.active && !root.textEditing; onActivated: root.bladeTool = false }
    Shortcut { sequence: "Delete"; enabled: root.active && !root.textEditing; onActivated: project.deleteSelected() }
    Shortcut { sequence: "+"; enabled: root.active && !root.textEditing; onActivated: timelineZoom = Math.min(8, timelineZoom * 1.3) }
    Shortcut { sequence: "-"; enabled: root.active && !root.textEditing; onActivated: timelineZoom = Math.max(.5, timelineZoom / 1.3) }
    Shortcut { sequence: "?"; enabled: root.active && !root.textEditing; onActivated: shortcutsDialog.open() }
    Shortcut { sequences: [StandardKey.Copy]; enabled: root.active && !root.textEditing; onActivated: root.copyClip() }
    Shortcut { sequences: [StandardKey.Paste]; enabled: root.active && !root.textEditing; onActivated: root.pasteClip() }

    ColumnLayout {
        anchors.fill: parent; spacing: 0
        EditorTopBar { editor: root; Layout.fillWidth: true }
        SplitView {
            id: verticalSplit; objectName: "editorVerticalSplit"
            Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Vertical
            handle: Rectangle { implicitHeight: 5; color: SplitHandle.hovered || SplitHandle.pressed ? EditorTheme.accent : EditorTheme.background }
            SplitView {
                id: upperSplit; objectName: "editorUpperSplit"; orientation: Qt.Horizontal
                SplitView.fillHeight: true; SplitView.minimumHeight: 250
                handle: Rectangle { implicitWidth: 5; color: SplitHandle.hovered || SplitHandle.pressed ? EditorTheme.accent : EditorTheme.background }
                MontageMediaPool {
                    id: mediaPool; objectName: "editorMediaPool"; editor: root
                    visible: root.mediaPoolVisible && !root.viewerMaximized && (!root.compactLayout || !root.compactInspectorMode)
                    SplitView.minimumWidth: 210; SplitView.preferredWidth: workspaceSettings.mediaWidth; SplitView.maximumWidth: 480
                    onWidthChanged: if (upperSplit.resizing) workspaceSettings.mediaWidth = width
                }
                EditorViewer { id: viewer; objectName: "editorViewer"; editor: root; SplitView.fillWidth: true; SplitView.minimumWidth: 350 }
                EditorInspector {
                    objectName: "editorInspector"; editor: root
                    visible: root.inspectorVisible && !root.viewerMaximized && (!root.compactLayout || root.compactInspectorMode)
                    SplitView.minimumWidth: 260; SplitView.preferredWidth: workspaceSettings.inspectorWidth; SplitView.maximumWidth: 440
                    onWidthChanged: if (upperSplit.resizing) workspaceSettings.inspectorWidth = width
                }
            }
            MontageDualTimeline {
                id: dualTimeline; objectName: "editorTimeline"; editor: root
                visible: !root.viewerMaximized
                SplitView.minimumHeight: 190; SplitView.preferredHeight: workspaceSettings.timelineHeight; SplitView.maximumHeight: root.height * 0.65
                onHeightChanged: if (verticalSplit.resizing) workspaceSettings.timelineHeight = height
            }
        }
        EditorBottomBar { editor: root; Layout.fillWidth: true }
        Label {
            Layout.fillWidth: true; Layout.margins: visible ? 8 : 0
            visible: text.length > 0; wrapMode: Text.Wrap; color: EditorTheme.secondary; font.pixelSize: EditorTheme.smallSize
            text: root.message || (project ? project.error : "") || (project && project.importer.error ? project.importer.error : "")
        }
    }
    EditorProjectDialog { id: projectDialog; editor: root }
    EditorExportDialog { id: exportDialog; editor: root }
    EditorComponentGallery { id: componentGallery }
    EditorDialog {
        id: shortcutsDialog
        parent: root.contentItem
        anchors.centerIn: parent
        width: Math.min(500, root.width - 32)
        title: I18n.t("editor.shortcuts")
        standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            spacing: EditorTheme.space2
            Label {
                Layout.fillWidth: true
                text: I18n.t("editor.shortcuts_hint")
                color: EditorTheme.textSecondary
                font.pixelSize: EditorTheme.fontSize
                wrapMode: Text.Wrap
            }
            Repeater {
                model: [
                    { key: "Space", label: "studio.play" },
                    { key: "C", label: "editor.split" },
                    { key: "V", label: "editor.selection_tool" },
                    { key: "Delete", label: "editor.delete" },
                    { key: "Ctrl+Z", label: "history.undo" },
                    { key: "Ctrl+Shift+Z", label: "history.redo" },
                    { key: "+ / −", label: "editor.zoom" }
                ]
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: EditorTheme.space3
                    Label {
                        text: modelData.key
                        color: EditorTheme.textPrimary
                        font.family: "monospace"
                        font.pixelSize: EditorTheme.fontSize
                        horizontalAlignment: Text.AlignHCenter
                        Layout.preferredWidth: 112
                    }
                    Label {
                        text: I18n.t(modelData.label)
                        color: EditorTheme.textSecondary
                        font.pixelSize: EditorTheme.fontSize
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
    EditorDialog {
        id: unsavedDialog; parent: root.contentItem; anchors.centerIn: parent; width: Math.min(460, root.width - 32)
        title: I18n.t("editor.save_changes")
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: EditorTheme.space4
            Label { Layout.fillWidth: true; text: I18n.t("editor.unsaved_hint"); wrapMode: Text.Wrap; color: EditorTheme.textPrimary; font.pixelSize: EditorTheme.fontSize }
            RowLayout {
                Layout.fillWidth: true; spacing: EditorTheme.space2
                EditorButton { text: I18n.t("editor.dont_save"); variant: "danger"; onClicked: { unsavedDialog.close(); project.discardAutosave(); root.performPending() } }
                Item { Layout.fillWidth: true }
                EditorButton { text: I18n.t("cancel"); onClicked: { unsavedDialog.close(); root.pendingAction = "" } }
                EditorButton { text: I18n.t("editor.save"); primary: true; onClicked: { unsavedDialog.close(); if (!project.save()) root.pendingAction = "" } }
            }
        }
    }
    Dialog {
        id: recoveryDialog; parent: root.contentItem; modal: true; anchors.centerIn: parent; width: Math.min(500, root.width - 32)
        title: I18n.t("editor.recovery"); standardButtons: Dialog.Close
        background: Rectangle { color: EditorTheme.panel; border.color: EditorTheme.border; radius: 8 }
        contentItem: ColumnLayout {
            Repeater {
                model: root.project ? root.project.recoveries : []
                RowLayout {
                    required property var modelData
                    Label { Layout.fillWidth: true; text: modelData.name + "\n" + modelData.modified; color: EditorTheme.text; elide: Text.ElideRight }
                    EditorButton { text: I18n.t("editor.recover"); onClicked: { recoveryDialog.close(); root.requestAction("recover", modelData.path) } }
                    EditorButton { text: I18n.t("editor.discard"); onClicked: project.discardRecovery(modelData.path) }
                }
            }
        }
    }
    function editProjectSettings() { projectDialog.openSettings() }
    function openComponentGallery() { componentGallery.show(); componentGallery.raise(); componentGallery.requestActivate() }
}
