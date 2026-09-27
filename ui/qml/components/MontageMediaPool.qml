import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../editor"
Rectangle {
    id: root
    property var editor
    property int activeFilter: 0
    property string searchQuery: ""
    property bool isGridView: true
    property string selectedMedia: ""
    property var menuItem: ({})
    readonly property var mediaItems: editor ? editor.doc.media.filter(function(item) {
        return (root.activeFilter === 0 || item.media_type === ["", "video", "audio", "image"][root.activeFilter])
            && item.name.toLowerCase().indexOf(root.searchQuery.toLowerCase()) >= 0
    }) : []
    color: EditorTheme.panel; clip: true
    function details(item) {
        var duration = item.duration || 0, mins = Math.floor(duration/60), seconds = Math.floor(duration%60)
        return mins + ":" + ("0" + seconds).slice(-2) + (item.media_type === "audio" ? " · Audio" : " · " + item.width + "×" + item.height + (item.media_type === "video" ? " · " + item.fps + " fps" : ""))
    }
    DropArea {
        anchors.fill: parent
        onDropped: function(drop) { if (drop.hasUrls) { editor.project.importMedia(drop.urls.map(function(url) { return String(url) }), false); drop.acceptProposedAction() } }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { Layout.fillWidth: true; text: I18n.t(editor.libraryPage === 1 ? "editor.titles" : editor.libraryPage === 2 ? "editor.transitions" : "editor.media_pool"); color: EditorTheme.text; font.pixelSize: EditorTheme.fontSize + 1; font.bold: true; elide: Text.ElideRight }
            EditorButton { iconName: "add"; iconOnly: true; text: I18n.t("editor.import_media"); enabled: !editor.project || !editor.project.importer.busy; onClicked: editor.project.chooseMedia() }
        }
        RowLayout {
            Layout.fillWidth: true; visible: editor.libraryPage === 0; spacing: 3
            Repeater { model: ["all","video","audio","images"]; EditorButton { required property int index; required property string modelData; Layout.fillWidth: true; text: I18n.t("editor." + modelData); checked: root.activeFilter === index; onClicked: root.activeFilter = index; font.pixelSize: EditorTheme.smallSize; implicitWidth: 40 } }
        }
        EditorField { Layout.fillWidth: true; placeholderText: I18n.t("editor.search"); onTextChanged: root.searchQuery = text; visible: editor.libraryPage !== 1 }
        RowLayout {
            Layout.fillWidth: true; visible: editor.libraryPage === 0
            Label { Layout.fillWidth: true; text: root.mediaItems.length + " " + I18n.t("editor.items"); color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize }
            EditorButton { text: I18n.t("editor.grid"); iconName: "grid"; iconOnly: true; checked: root.isGridView; onClicked: root.isGridView = true }
            EditorButton { text: I18n.t("editor.list"); iconName: "list"; iconOnly: true; checked: !root.isGridView; onClicked: root.isGridView = false }
        }
        ProgressBar { Layout.fillWidth: true; visible: editor.project && editor.project.importer.busy; from: 0; to: 100; value: editor.project ? editor.project.importer.progress : 0 }
        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: editor.libraryPage
            Item {
                GridView {
                    id: mediaGrid; objectName: "editorMediaGrid"; anchors.fill: parent; clip: true
                    model: root.mediaItems
                    cellWidth: root.isGridView ? width / Math.max(1, Math.floor(width / 150)) : width
                    cellHeight: root.isGridView ? 156 : 74
                    ScrollBar.vertical: ScrollBar {}
                    delegate: Item {
                        id: mediaCard
                        required property var modelData
                        width: mediaGrid.cellWidth; height: mediaGrid.cellHeight
                        Rectangle { anchors.fill: parent; anchors.margins: 3; radius: 5; color: cardMouse.containsMouse ? EditorTheme.hover : EditorTheme.raised; border.width: root.selectedMedia === modelData.id ? 2 : 1; border.color: root.selectedMedia === modelData.id ? EditorTheme.accent : EditorTheme.border }
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 10; spacing: 5
                            Item {
                                visible: root.isGridView; Layout.fillWidth: true; Layout.fillHeight: true
                                Image { anchors.fill: parent; source: modelData.thumbnail || ""; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                AppIcon { anchors.centerIn: parent; width: 28; height: 28; name: modelData.media_type === "audio" ? "audio" : "film"; visible: !modelData.thumbnail; iconColor: EditorTheme.secondary }
                            }
                            Label { Layout.fillWidth: true; text: modelData.name; color: EditorTheme.text; font.pixelSize: EditorTheme.fontSize; elide: Text.ElideMiddle }
                            Label { Layout.fillWidth: true; text: root.details(modelData); color: EditorTheme.secondary; font.pixelSize: EditorTheme.smallSize; elide: Text.ElideRight }
                        }
                        Item { id: dragProxy; property string mediaId: modelData.id; width: 1; height: 1; Drag.active: cardMouse.drag.active; Drag.keys: ["editor-media"]; Drag.source: dragProxy; Drag.hotSpot.x: 0; Drag.hotSpot.y: 0 }
                        MouseArea {
                            id: cardMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.RightButton
                            drag.target: dragProxy
                            onClicked: function(mouse) { root.selectedMedia = modelData.id; if (mouse.button === Qt.RightButton) { root.menuItem = modelData; mediaMenu.popup() } }
                            onDoubleClicked: editor.project.addToTimeline(modelData.id)
                            onReleased: { dragProxy.Drag.drop(); dragProxy.x = 0; dragProxy.y = 0 }
                            ToolTip.visible: containsMouse; ToolTip.delay: 750; ToolTip.text: modelData.path + "\n" + I18n.t("editor.double_click_add")
                        }
                    }
                }
                ColumnLayout {
                    anchors.centerIn: parent; width: parent.width - 16; visible: root.mediaItems.length === 0; spacing: 12
                    AppIcon { name: "folder"; iconColor: EditorTheme.muted; Layout.preferredWidth: 38; Layout.preferredHeight: 38; Layout.alignment: Qt.AlignHCenter }
                    Label { Layout.fillWidth: true; text: I18n.t("editor.drop_media"); color: EditorTheme.secondary; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                    EditorButton { text: I18n.t("editor.import_media"); primary: true; Layout.alignment: Qt.AlignHCenter; onClicked: editor.project.chooseMedia() }
                    Label { Layout.fillWidth: true; text: "MOV, MP4, MKV, MP3, WAV, PNG, JPG"; color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                }
            }
            ColumnLayout {
                spacing: 12
                Label { Layout.fillWidth: true; text: I18n.t("editor.title_hint"); wrapMode: Text.Wrap; color: EditorTheme.secondary }
                EditorButton { Layout.fillWidth: true; text: I18n.t("editor.add_title"); iconName: "text"; primary: true; onClicked: { editor.project.addTitle(editor.playhead); editor.inspectorVisible = true; editor.inspectorTab = 2 } }
                EditorButton { Layout.fillWidth: true; text: I18n.t("editor.import_subtitles"); iconName: "text"; onClicked: editor.project.importSubtitles() }
                EditorButton { Layout.fillWidth: true; text: I18n.t("studio.title"); enabled: !!editor.filePath; onClicked: editor.openTools() }
                Item { Layout.fillHeight: true }
            }
            ColumnLayout {
                Label { Layout.fillWidth: true; text: I18n.t("editor.transition_hint"); wrapMode: Text.Wrap; color: EditorTheme.secondary }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                    model: [{id:"none",name:"Cut"},{id:"fade",name:"Cross Fade"},{id:"dissolve",name:"Dissolve"},{id:"wipeleft",name:"Wipe Left"},{id:"wiperight",name:"Wipe Right"},{id:"slideup",name:"Slide Up"},{id:"slidedown",name:"Slide Down"},{id:"circlecrop",name:"Circle"}].filter(function(t) { return t.name.toLowerCase().indexOf(root.searchQuery.toLowerCase()) >= 0 })
                    delegate: EditorButton {
                        required property var modelData; width: ListView.view.width; text: modelData.name; iconName: "sliders"
                        enabled: editor.selected.kind === "video"; checked: editor.selected.transition_to_next === modelData.id
                        onClicked: editor.project.editSelected({transition_to_next: modelData.id})
                    }
                }
            }
        }
    }
    Menu {
        id: mediaMenu
        MenuItem { text: I18n.t("editor.add_timeline"); onTriggered: editor.project.addToTimeline(root.menuItem.id) }
        MenuItem { text: I18n.t("editor.reveal"); onTriggered: editor.project.reveal(root.menuItem.path) }
        MenuItem { text: I18n.t("editor.rename"); onTriggered: { renameField.text = root.menuItem.name; renameDialog.open() } }
        MenuItem { text: I18n.t("editor.properties"); onTriggered: editor.message = root.menuItem.path + " · " + root.details(root.menuItem) }
        MenuItem { text: I18n.t("editor.remove_media"); onTriggered: editor.project.removeMedia(root.menuItem.id) }
    }
    EditorDialog {
        id: renameDialog; parent: editor.contentItem; anchors.centerIn: parent; width: 360; title: I18n.t("editor.rename")
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: EditorField { id: renameField }
        onAccepted: editor.project.renameMedia(root.menuItem.id, renameField.text)
    }
}
