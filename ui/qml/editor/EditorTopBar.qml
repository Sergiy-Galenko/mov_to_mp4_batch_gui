import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"
Rectangle {
    id: root
    property var editor
    implicitHeight: top.implicitHeight + tools.implicitHeight + 22
    color: EditorTheme.panel
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 8; spacing: 8
        RowLayout {
            id: top; Layout.fillWidth: true; spacing: 8
            BrandMark { source: Qt.resolvedUrl("../../../assets/app-logo-v2.png"); Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
            EditorButton {
                text: I18n.t("editor.project"); iconName: "chevron-down"
                onClicked: projectMenu.open()
                Menu {
                    id: projectMenu; y: parent.height; width: 260
                    palette.window: EditorTheme.panel; palette.text: EditorTheme.text; palette.highlight: EditorTheme.accent
                    MenuItem { text: I18n.t("editor.new_project"); onTriggered: editor.requestAction("new", "") }
                    MenuItem { text: I18n.t("editor.open_project"); onTriggered: editor.requestAction("open", "") }
                    MenuItem { text: I18n.t("editor.save"); onTriggered: editor.project.save() }
                    MenuItem { text: I18n.t("editor.save_as"); onTriggered: editor.project.saveAs() }
                    Menu {
                        title: I18n.t("editor.recent")
                        Repeater {
                            model: editor.project ? editor.project.recent : []
                            MenuItem { required property var modelData; text: modelData.name; onTriggered: editor.requestAction("open", modelData.path) }
                        }
                    }
                    MenuSeparator {}
                    MenuItem { text: I18n.t("editor.project_settings"); onTriggered: editor.editProjectSettings() }
                    MenuItem { text: I18n.t("editor.close_project"); onTriggered: editor.requestAction("empty", "") }
                }
            }
            EditorButton { iconOnly: true; iconName: "undo"; text: I18n.t("history.undo"); enabled: editor.history.canUndo; onClicked: editor.history.undo() }
            EditorButton { iconOnly: true; iconName: "redo"; text: I18n.t("history.redo"); enabled: editor.history.canRedo; onClicked: editor.history.redo() }
            ColumnLayout {
                Layout.fillWidth: true; Layout.minimumWidth: 100; spacing: 2
                Item {
                    Layout.fillWidth: true; implicitHeight: Math.max(22, projectName.implicitHeight)
                    Label {
                        id: projectName; anchors.fill: parent
                        text: editor.doc.project_name + (editor.project && editor.project.dirty ? " *" : "")
                        visible: !nameField.visible; color: EditorTheme.text; font.pixelSize: EditorTheme.fontSize + 2; font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter; elide: Text.ElideMiddle
                        MouseArea { anchors.fill: parent; onDoubleClicked: { nameField.text = editor.doc.project_name; nameField.visible = true; nameField.forceActiveFocus(); nameField.selectAll() } }
                    }
                    EditorField {
                        id: nameField; objectName: "editorProjectName"; anchors.fill: parent; visible: false
                        horizontalAlignment: Text.AlignHCenter
                        onAccepted: { editor.project.rename(text); visible = false }
                        Keys.onEscapePressed: visible = false
                    }
                }
                Label {
                    Layout.fillWidth: true; text: editor.project && editor.project.path ? editor.project.path : I18n.t("editor.unsaved_project")
                    color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize; elide: Text.ElideMiddle; horizontalAlignment: Text.AlignHCenter
                    ToolTip.visible: pathHover.hovered; ToolTip.text: text
                    HoverHandler { id: pathHover }
                }
            }
            Label {
                visible: root.width > 1160; font.pixelSize: EditorTheme.smallSize
                text: editor.project && editor.project.saving ? I18n.t("editor.saving") : editor.project && editor.project.dirty ? I18n.t("editor.unsaved") : I18n.t("editor.saved")
                color: editor.project && editor.project.dirty ? "#eabf68" : EditorTheme.success
            }
            EditorButton { objectName: "editorSaveButton"; iconName: "save"; text: I18n.t("editor.save"); enabled: editor.project && !editor.project.saving; onClicked: editor.project.save() }
            EditorButton { objectName: "editorQuickExport"; iconName: "share"; text: I18n.t("editor.quick_export"); primary: true; enabled: editor.timelineClips.length > 0 && !editor.render.busy; onClicked: editor.openExport() }
        }
        RowLayout {
            id: tools; Layout.fillWidth: true; spacing: 6
            EditorButton { text: I18n.t("editor.media_pool"); iconName: "folder"; checked: editor.mediaPoolVisible && editor.libraryPage === 0; onClicked: { editor.mediaPoolVisible = !editor.mediaPoolVisible || editor.libraryPage !== 0; editor.libraryPage = 0 } }
            EditorButton { text: I18n.t("editor.titles"); iconName: "text"; checked: editor.mediaPoolVisible && editor.libraryPage === 1; onClicked: { editor.mediaPoolVisible = true; editor.libraryPage = 1 } }
            EditorButton { text: I18n.t("editor.transitions"); iconName: "sliders"; checked: editor.mediaPoolVisible && editor.libraryPage === 2; onClicked: { editor.mediaPoolVisible = true; editor.libraryPage = 2 } }
            EditorButton { objectName: "openMontageTools"; text: I18n.t("studio.title"); iconName: "text"; enabled: editor.filePath.length > 0 && !backend.montageEditing.busy; onClicked: editor.openTools() }
            Item { Layout.fillWidth: true }
            Label { visible: root.width > 1200; text: "Timeline 1"; color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize }
            EditorButton { text: I18n.t("editor.inspector"); iconName: "sliders"; checked: editor.inspectorVisible; onClicked: editor.inspectorVisible = !editor.inspectorVisible }
        }
    }
}
