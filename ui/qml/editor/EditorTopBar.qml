import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var editor
    implicitHeight: 92
    color: EditorTheme.bgPanel
    border.width: 1
    border.color: EditorTheme.borderSubtle

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: EditorTheme.space3
        anchors.rightMargin: EditorTheme.space3
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            spacing: EditorTheme.space2

            EditorButton {
                text: I18n.t("editor.project")
                iconName: "folder"
                variant: "ghost"
                onClicked: projectMenu.open()
                Menu {
                    id: projectMenu
                    y: parent.height + 4
                    width: 260
                    palette.window: EditorTheme.bgPanel
                    palette.text: EditorTheme.textPrimary
                    palette.highlight: EditorTheme.accent
                    MenuItem { text: I18n.t("editor.new_project"); onTriggered: editor.requestAction("new", "") }
                    MenuItem { text: I18n.t("editor.open_project"); onTriggered: editor.requestAction("open", "") }
                    MenuItem { text: I18n.t("editor.save"); onTriggered: editor.project.save() }
                    MenuItem { text: I18n.t("editor.save_as"); onTriggered: editor.project.saveAs() }
                    MenuSeparator {}
                    MenuItem { text: I18n.t("editor.project_settings"); onTriggered: editor.editProjectSettings() }
                    MenuItem { text: I18n.t("editor.components"); onTriggered: editor.openComponentGallery() }
                    MenuItem { text: I18n.t("editor.close_project"); onTriggered: editor.requestAction("empty", "") }
                }
            }

            Rectangle {
                implicitWidth: 65; implicitHeight: 32; radius: EditorTheme.radiusControl
                color: EditorTheme.bgElevated; border.width: 1; border.color: EditorTheme.borderSubtle
                Row {
                    anchors.centerIn: parent
                    EditorButton { iconOnly: true; iconName: "undo"; variant: "icon"; text: I18n.t("history.undo"); shortcut: "Ctrl+Z"; enabled: editor.history.canUndo; onClicked: editor.history.undo() }
                    Rectangle { width: 1; height: 18; anchors.verticalCenter: parent.verticalCenter; color: EditorTheme.borderSubtle }
                    EditorButton { iconOnly: true; iconName: "redo"; variant: "icon"; text: I18n.t("history.redo"); shortcut: "Ctrl+Shift+Z"; enabled: editor.history.canRedo; onClicked: editor.history.redo() }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 120
                spacing: 1
                Label { Layout.fillWidth: true; text: editor.displayProjectName; color: EditorTheme.textPrimary; font.pixelSize: EditorTheme.headingSize; font.weight: Font.DemiBold; elide: Text.ElideMiddle }
                Label { Layout.fillWidth: true; text: editor.project && editor.project.saving ? I18n.t("editor.saving") : editor.project && editor.project.dirty ? I18n.t("editor.unsaved") : I18n.t("editor.saved"); color: editor.project && editor.project.dirty ? EditorTheme.warning : EditorTheme.success; font.pixelSize: EditorTheme.smallSize; elide: Text.ElideRight }
            }

            EditorButton { objectName: "editorSaveButton"; iconName: "save"; text: I18n.t("editor.save"); variant: "ghost"; enabled: editor.project && !editor.project.saving; onClicked: editor.project.save() }
            EditorButton { objectName: "editorQuickExport"; iconName: "share"; text: I18n.t("editor.export"); variant: "primary"; enabled: editor.timelineClips.length > 0 && !editor.render.busy; onClicked: editor.openExport() }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: EditorTheme.borderSubtle }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            spacing: EditorTheme.space1
            Repeater {
                model: [
                    {key: "media", icon: "folder"}, {key: "edit", icon: "film"},
                    {key: "color", icon: "palette"}, {key: "audio", icon: "audio"},
                    {key: "titles", icon: "text"}, {key: "deliver", icon: "share"}
                ]
                EditorButton {
                    required property var modelData
                    text: I18n.t("editor." + modelData.key)
                    iconName: modelData.icon
                    variant: "tab"
                    checked: editor.activeWorkspace === modelData.key
                    onClicked: editor.chooseWorkspace(modelData.key)
                }
            }
            Item { Layout.fillWidth: true }
            EditorButton {
                iconOnly: true; iconName: "sliders"; variant: "icon"; text: I18n.t("editor.properties")
                checked: editor.compactLayout ? editor.compactInspectorMode : editor.inspectorVisible
                onClicked: {
                    if (editor.compactLayout) editor.compactInspectorMode = !editor.compactInspectorMode
                    else editor.inspectorVisible = !editor.inspectorVisible
                }
            }
        }
    }
}
