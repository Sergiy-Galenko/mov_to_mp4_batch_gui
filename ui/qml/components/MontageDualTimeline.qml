import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../editor"
Rectangle {
    id: root
    property var editor
    property string contextId: ""
    readonly property real pixelsPerSecond: Math.max(12, (trackView.width-32)/Math.max(10, editor.duration)) * editor.timelineZoom
    readonly property real extent: Math.max(trackView.width, Math.max(10,editor.duration) * pixelsPerSecond + 80)
    readonly property int trackHeight: 52
    readonly property real tickStep: pixelsPerSecond > 90 ? 1 : pixelsPerSecond > 35 ? 2 : pixelsPerSecond > 15 ? 5 : 10
    color: EditorTheme.background; clip: true
    function formatTimecode(value) { return editor.timecode(value) }
    function setInToPlayhead() { editor.markIn() }
    function setOutToPlayhead() { editor.markOut() }
    function snapped(time) {
        if (!editor.snappingEnabled) return Math.max(0,time)
        var result = Math.round(time*editor.fps)/editor.fps
        for (var i=0;i<editor.clipLayout.length;i++) {
            if (Math.abs(result-editor.clipLayout[i].start)*pixelsPerSecond < 8) result = editor.clipLayout[i].start
            if (Math.abs(result-editor.clipLayout[i].end)*pixelsPerSecond < 8) result = editor.clipLayout[i].end
        }
        return Math.max(0,result)
    }
    ColumnLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillWidth: true; implicitHeight: EditorTheme.controlHeight+12; color: EditorTheme.panel
            RowLayout {
                anchors.fill: parent; anchors.margins: 6; spacing: 5
                EditorButton { iconName: "cursor"; iconOnly: true; text: I18n.t("editor.selection_tool") + " (A)"; checked: !editor.bladeTool; onClicked: editor.bladeTool = false }
                EditorButton { iconName: "cut"; iconOnly: true; text: I18n.t("editor.blade") + " (B)"; checked: editor.bladeTool; onClicked: editor.bladeTool = true }
                EditorButton { iconName: "magnet"; iconOnly: true; text: I18n.t("editor.snapping"); checked: editor.snappingEnabled; onClicked: editor.snappingEnabled = !editor.snappingEnabled }
                EditorButton { text: I18n.t("editor.in"); enabled: editor.selected.kind === "video"; onClicked: editor.markIn() }
                EditorButton { text: I18n.t("editor.out"); enabled: editor.selected.kind === "video"; onClicked: editor.markOut() }
                EditorButton { text: I18n.t("editor.split"); iconName: "cut"; enabled: editor.duration > 0; onClicked: editor.splitAtPlayhead() }
                Item { Layout.fillWidth: true }
                Label { visible: root.width > 1150; text: "Timeline 1"; color: EditorTheme.secondary; font.pixelSize: EditorTheme.smallSize }
                Label { text: editor.timecode(editor.playhead); color: EditorTheme.text; font.family: Theme.monoFont; font.pixelSize: EditorTheme.smallSize }
                EditorButton { text: I18n.t("editor.zoom_out"); iconName: "minus"; iconOnly: true; onClicked: editor.timelineZoom = Math.max(.5,editor.timelineZoom/1.3) }
                Slider { objectName: "editorTimelineZoom"; Layout.preferredWidth: 100; from: .5; to: 8; value: editor.timelineZoom; onMoved: editor.timelineZoom = value }
                EditorButton { text: I18n.t("editor.zoom_in"); iconName: "add"; iconOnly: true; onClicked: editor.timelineZoom = Math.min(8,editor.timelineZoom*1.3) }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Item {
                Layout.preferredWidth: 142; Layout.fillHeight: true; clip: true
                Rectangle { anchors.fill: parent; color: EditorTheme.panel }
                Label { x: 12; y: 5; text: I18n.t("editor.tracks"); font.pixelSize: EditorTheme.smallSize; color: EditorTheme.muted }
                Column {
                    width: parent.width; y: 28-trackView.contentY
                    Repeater {
                        model: [
                            {name:"V2",key:"titles",lock:"titles_locked",toggle:"titles_visible",icon:"eye"},
                            {name:"V1",key:"video",lock:"video_locked",toggle:"",icon:"film"},
                            {name:"A1",key:"original_audio",lock:"audio_locked",toggle:"audio_muted",icon:"volume"},
                            {name:"A2",key:"music",lock:"audio_locked",toggle:"music_muted",icon:"volume"}]
                        Rectangle {
                            required property var modelData
                            width: parent.width; height: root.trackHeight; color: EditorTheme.panel; border.color: EditorTheme.border
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 6; spacing: 3
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Label { text: modelData.name; color: EditorTheme.text; font.bold: true; font.pixelSize: EditorTheme.smallSize }
                                    Label { Layout.fillWidth: true; text: I18n.t("editor."+modelData.key); color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize-1; elide: Text.ElideRight }
                                }
                                EditorButton { implicitWidth: 26; implicitHeight: 28; iconOnly: true; iconName: modelData.icon; text: I18n.t(modelData.icon === "eye" ? "editor.visibility" : "editor.mute"); enabled: !!modelData.toggle; checked: !!modelData.toggle && !!editor.doc.tracks[modelData.toggle]; onClicked: { var patch={}; patch[modelData.toggle] = !editor.doc.tracks[modelData.toggle]; editor.project.updateSection("tracks",patch) } }
                                EditorButton { implicitWidth: 26; implicitHeight: 28; iconOnly: true; iconName: "lock"; text: I18n.t("editor.lock_track"); checked: !!editor.doc.tracks[modelData.lock]; onClicked: { var patch={}; patch[modelData.lock]=!editor.doc.tracks[modelData.lock]; editor.project.updateSection("tracks",patch) } }
                            }
                        }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                Item {
                    Layout.fillWidth: true; Layout.preferredHeight: 28; clip: true
                    Rectangle { anchors.fill: parent; color: EditorTheme.panel }
                    Row {
                        x: -trackView.contentX; height: parent.height
                        Repeater {
                            model: Math.ceil(root.extent / (root.tickStep * root.pixelsPerSecond))
                            Item {
                                required property int index; width: root.tickStep * root.pixelsPerSecond; height: 28
                                Rectangle { y: 20; width: 1; height: 8; color: EditorTheme.muted }
                                Label { x: 5; y: 4; text: Math.floor(index*root.tickStep/60) + ":" + ("0"+Math.floor(index*root.tickStep%60)).slice(-2); font.pixelSize: EditorTheme.smallSize; font.family: Theme.monoFont; color: EditorTheme.secondary }
                            }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        onPressed: function(mouse) { editor.seek(root.snapped((mouse.x+trackView.contentX)/root.pixelsPerSecond)) }
                        onPositionChanged: function(mouse) { if (pressed) editor.seek(root.snapped((mouse.x+trackView.contentX)/root.pixelsPerSecond)) }
                    }
                    Rectangle { x: editor.playhead*root.pixelsPerSecond-trackView.contentX-4; y: 17; width: 8; height: 8; rotation: 45; color: EditorTheme.danger }
                }
                Flickable {
                    id: trackView; objectName: "editorTrackView"; Layout.fillWidth: true; Layout.fillHeight: true
                    contentWidth: root.extent; contentHeight: root.trackHeight*4; clip: true; boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    Repeater { model: 4; Rectangle { required property int index; width: root.extent; height: root.trackHeight; y: index*root.trackHeight; color: index%2 ? "#141821" : "#181c25"; border.color: EditorTheme.border } }
                    MouseArea { width: root.extent; height: trackView.contentHeight; onClicked: function(mouse) { editor.project.select(""); editor.seek(root.snapped(mouse.x/root.pixelsPerSecond)) } }
                    Repeater {
                        model: editor.doc.titles
                        Rectangle {
                            id: titleClip; required property var modelData
                            x: modelData.start*root.pixelsPerSecond; y: 5; width: Math.max(8,(modelData.end-modelData.start)*root.pixelsPerSecond); height: root.trackHeight-10
                            color: EditorTheme.title; radius: 4; border.width: editor.project.selectedId === modelData.id ? 2 : 1; border.color: editor.project.selectedId === modelData.id ? "#ffffff" : "#a781ce"; opacity: editor.doc.tracks.titles_visible ? 1 : .35
                            Label { anchors.fill: parent; anchors.margins: 8; text: modelData.text; textFormat: Text.PlainText; color: EditorTheme.text; elide: Text.ElideRight; font.pixelSize: EditorTheme.smallSize; verticalAlignment: Text.AlignVCenter }
                            MouseArea {
                                anchors.fill: parent; property real pressX: 0; acceptedButtons: Qt.LeftButton | Qt.RightButton
                                onPressed: function(mouse) { pressX = mouse.x; editor.project.select(modelData.id); editor.inspectorTab = 2; editor.inspectorVisible = true }
                                onReleased: function(mouse) { if (!editor.doc.tracks.titles_locked && Math.abs(mouse.x-pressX)>5) { var position=root.snapped(modelData.start+(mouse.x-pressX)/root.pixelsPerSecond); editor.project.editSelected({start:position,end:position+modelData.end-modelData.start}) } }
                                onClicked: function(mouse) { if (mouse.button === Qt.RightButton) clipMenu.popup() }
                            }
                        }
                    }
                    Repeater {
                        model: editor.clipLayout
                        Rectangle {
                            id: videoClip; required property var modelData
                            x: modelData.start*root.pixelsPerSecond; y: root.trackHeight+4
                            width: Math.max(8,modelData.duration*root.pixelsPerSecond); height: root.trackHeight-8
                            color: clipMouse.containsMouse ? "#316697" : EditorTheme.video; radius: 4
                            border.width: editor.project.selectedId === modelData.id ? 2 : 1; border.color: editor.project.selectedId === modelData.id ? "white" : "#4b8ed0"
                            opacity: modelData.clip.enabled === false ? .35 : 1
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 6; spacing: 6
                                Image { visible: videoClip.width > 100 && !!modelData.clip.thumbnail; source: modelData.clip.thumbnail || ""; Layout.preferredWidth: 48; Layout.fillHeight: true; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                                Label { Layout.fillWidth: true; text: modelData.clip.name; color: EditorTheme.text; font.pixelSize: EditorTheme.smallSize; elide: Text.ElideRight }
                            }
                            Rectangle { anchors.right: parent.right; anchors.bottom: parent.bottom; width: Math.min(parent.width, Math.max(12,(modelData.clip.transition_duration || .5)*root.pixelsPerSecond)); height: 6; color: "#e9b969"; visible: modelData.clip.transition_to_next !== "none" && modelData.index < editor.clipLayout.length-1 }
                            MouseArea {
                                id: clipMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.RightButton
                                property real pressX: 0
                                onPressed: function(mouse) { pressX=mouse.x; editor.project.select(modelData.id); editor.inspectorTab=0; editor.inspectorVisible=true }
                                onClicked: function(mouse) {
                                    if (mouse.button===Qt.RightButton) { clipMenu.popup(); return }
                                    var point = root.snapped(modelData.start+mouse.x/root.pixelsPerSecond)
                                    editor.seek(point)
                                    if (editor.bladeTool) editor.splitAtPlayhead()
                                }
                                onReleased: function(mouse) {
                                    if (editor.doc.tracks.video_locked || Math.abs(mouse.x-pressX)<8 || editor.bladeTool) return
                                    var targetTime=modelData.start+(mouse.x-pressX)/root.pixelsPerSecond, target=editor.clipLayout.length-1
                                    for(var i=0;i<editor.clipLayout.length;i++) if(targetTime<editor.clipLayout[i].end) {target=i;break}
                                    editor.project.moveClip(modelData.id,target)
                                }
                                ToolTip.visible: containsMouse; ToolTip.text: modelData.clip.name + "\n" + editor.timecode(modelData.duration)
                            }
                            Repeater {
                                model: 2
                                Rectangle {
                                    required property int index; width: 5; height: parent.height-8; y: 4; x: index===0 ? 2 : parent.width-width-2; radius: 2; color: "#d5e9ff"; visible: editor.project.selectedId === modelData.id
                                    MouseArea {
                                        anchors.fill: parent; anchors.margins: -3; cursorShape: Qt.SizeHorCursor; property real startX: 0
                                        onPressed: function(mouse) { startX=mapToItem(trackView.contentItem,mouse.x,mouse.y).x; editor.history.begin() }
                                        onReleased: function(mouse) {
                                            var delta=(mapToItem(trackView.contentItem,mouse.x,mouse.y).x-startX)/root.pixelsPerSecond
                                            if(editor.snappingEnabled) delta=Math.round(delta*editor.fps)/editor.fps
                                            if(index===0) editor.inPoint=Math.max(0,Math.min(editor.outPoint-1/editor.fps,modelData.clip.in_point+delta))
                                            else editor.outPoint=Math.max(editor.inPoint+1/editor.fps,Math.min(modelData.clip.source_duration,modelData.clip.out_point+delta))
                                            editor.history.end()
                                        }
                                        onCanceled: editor.history.end()
                                    }
                                }
                            }
                        }
                    }
                    Repeater {
                        model: editor.clipLayout
                        Rectangle {
                            required property var modelData
                            x: modelData.start*root.pixelsPerSecond; y: root.trackHeight*2+6; width: Math.max(8,modelData.duration*root.pixelsPerSecond); height: root.trackHeight-12
                            visible: modelData.clip.has_audio; color: EditorTheme.audio; radius: 4; border.color: "#388f7c"; opacity: editor.doc.tracks.audio_muted || modelData.clip.audio_enabled === false ? .35 : 1
                            Image { anchors.fill: parent; anchors.margins: 2; source: modelData.clip.source_path === editor.filePath && editor.waveformPath ? editor.project.fileUrl(editor.waveformPath) : ""; fillMode: Image.Stretch; asynchronous: true; opacity: .7 }
                            Label { anchors.fill: parent; anchors.margins: 8; text: modelData.clip.name; color: EditorTheme.text; font.pixelSize: EditorTheme.smallSize; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                            MouseArea { anchors.fill: parent; onClicked: { editor.project.select(modelData.id); editor.inspectorTab=1; editor.inspectorVisible=true } }
                        }
                    }
                    Repeater {
                        model: editor.doc.timeline.audio_tracks
                        Rectangle {
                            required property var modelData
                            x: (modelData.offset || 0)*root.pixelsPerSecond; y: root.trackHeight*3+6; width: Math.max(40,(editor.duration-(modelData.offset || 0))*root.pixelsPerSecond); height: root.trackHeight-12
                            color: "#285044"; radius: 4; border.color: editor.project.selectedId===modelData.id ? "white" : "#5f9f7b"; opacity: editor.doc.tracks.music_muted ? .35 : 1
                            Label { anchors.fill: parent; anchors.margins: 8; text: modelData.name; color: EditorTheme.text; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                            MouseArea { anchors.fill: parent; acceptedButtons: Qt.LeftButton | Qt.RightButton; onClicked: function(mouse) { editor.project.select(modelData.id); editor.inspectorTab=1; editor.inspectorVisible=true; if(mouse.button===Qt.RightButton) clipMenu.popup() } }
                        }
                    }
                    Rectangle { x: editor.playhead*root.pixelsPerSecond; width: 2; height: trackView.contentHeight; color: EditorTheme.danger }
                    Label { anchors.centerIn: parent; visible: editor.timelineClips.length===0; text: I18n.t("editor.timeline_empty"); color: EditorTheme.muted }
                    DropArea { width: root.extent; height: trackView.contentHeight; keys: ["editor-media"]; onDropped: function(drop) { if(drop.source && drop.source.mediaId) { editor.project.addToTimeline(drop.source.mediaId); drop.acceptProposedAction() } } }
                }
            }
        }
    }
    Menu {
        id: clipMenu
        MenuItem { text: I18n.t("editor.copy"); enabled: editor.selected.kind==="video"; onTriggered: editor.copyClip() }
        MenuItem { text: I18n.t("editor.cut"); enabled: editor.selected.kind==="video"; onTriggered: { editor.copyClip(); editor.project.deleteSelected() } }
        MenuItem { text: I18n.t("editor.paste"); enabled: !!editor.clipboardClip; onTriggered: editor.pasteClip() }
        MenuItem { text: I18n.t("editor.split"); enabled: editor.selected.kind==="video"; onTriggered: editor.splitAtPlayhead() }
        MenuItem { text: I18n.t("editor.delete"); onTriggered: editor.project.deleteSelected() }
        MenuItem { text: I18n.t("editor.disable_clip"); enabled: editor.selected.kind==="video"; checkable: true; checked: editor.selected.enabled===false; onTriggered: editor.project.editSelected({enabled: !checked}) }
        MenuItem { text: I18n.t("editor.speed_unavailable"); enabled: false }
        MenuItem { text: I18n.t("editor.properties"); onTriggered: editor.inspectorVisible=true }
    }
}
