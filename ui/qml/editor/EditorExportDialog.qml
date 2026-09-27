import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
EditorDialog {
    id: root; objectName: "editorExportDialog"; property var editor
    parent: editor.contentItem; anchors.centerIn: parent
    width: Math.min(520, parent.width-32); height: Math.min(650, parent.height-32)
    title: I18n.t(editor.render && editor.render.busy ? "editor.rendering" : "editor.quick_export")
    contentItem: ScrollView {
        id: scroll; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: scroll.availableWidth; spacing: 12
            EditorExportPanel { editor: root.editor; Layout.fillWidth: true; showExport: false; visible: !editor.render.busy }
            ColumnLayout {
                visible: editor.render.busy; Layout.fillWidth: true
                Label { text: I18n.t("editor.rendering"); color: EditorTheme.text }
                ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: editor.render.progress; indeterminate: value === 0 }
                Label { text: editor.render.progress + "%"; color: EditorTheme.text }
                Label { text: I18n.t("editor.elapsed") + ": " + editor.render.elapsed + " s"; color: EditorTheme.secondary }
                Label { text: I18n.t("editor.remaining") + ": " + (editor.render.remaining >= 0 ? editor.render.remaining + " s" : "—"); color: EditorTheme.secondary }
                Label { Layout.fillWidth: true; text: I18n.t("editor.render_background"); wrapMode: Text.Wrap; color: EditorTheme.muted }
            }
            Label { Layout.fillWidth: true; visible: editor.render.stage === "ready" && !!editor.render.result.path; text: I18n.t("editor.export_complete") + "\n" + (editor.render.result.path || ""); wrapMode: Text.WrapAnywhere; color: EditorTheme.success }
            Label { Layout.fillWidth: true; visible: editor.render.stage === "error"; text: I18n.t("editor.export_failed"); wrapMode: Text.Wrap; color: EditorTheme.danger }
            InspectorSection { Layout.fillWidth: true; visible: editor.render.error.length > 0 && editor.render.error !== "cancelled"; title: I18n.t("editor.details"); expanded: false; Label { Layout.fillWidth: true; text: editor.render.error; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: EditorTheme.secondary } }
        }
    }
    footer: RowLayout {
        spacing: 8
        Item { Layout.fillWidth: true }
        EditorButton { text: I18n.t("close"); onClicked: root.close() }
        EditorButton { text: I18n.t("cancel"); visible: editor.render.busy; onClicked: editor.render.cancel() }
        EditorButton {
            text: I18n.t("editor.export_video"); primary: true; visible: !editor.render.busy; enabled: editor.timelineClips.length > 0
            Layout.rightMargin: 20; Layout.bottomMargin: 16
            onClicked: { var path = editor.render.chooseOutput(editor.doc); if (path) editor.render.export(editor.doc, path) }
        }
    }
}
