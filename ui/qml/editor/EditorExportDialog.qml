import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
EditorDialog {
    id: root; objectName: "editorExportDialog"; property var editor
    readonly property var renderState: editor && editor.render ? editor.render : ({busy: false, progress: 0, elapsed: 0, remaining: -1, stage: "", result: ({path: ""}), error: ""})
    parent: editor.contentItem; anchors.centerIn: parent
    width: Math.min(520, parent.width-32); height: Math.min(650, parent.height-32)
    title: I18n.t(renderState.busy ? "editor.rendering" : "editor.quick_export")
    contentItem: ScrollView {
        id: scroll; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: scroll.availableWidth; spacing: 12
            EditorExportPanel { editor: root.editor; Layout.fillWidth: true; showExport: false; visible: !root.renderState.busy }
            ColumnLayout {
                visible: root.renderState.busy; Layout.fillWidth: true
                Label { text: I18n.t("editor.rendering"); color: EditorTheme.text }
                ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: root.renderState.progress; indeterminate: value === 0 }
                Label { text: root.renderState.progress + "%"; color: EditorTheme.text }
                Label { text: I18n.t("editor.elapsed") + ": " + root.renderState.elapsed + " s"; color: EditorTheme.secondary }
                Label { text: I18n.t("editor.remaining") + ": " + (root.renderState.remaining >= 0 ? root.renderState.remaining + " s" : "—"); color: EditorTheme.secondary }
                Label { Layout.fillWidth: true; text: I18n.t("editor.render_background"); wrapMode: Text.Wrap; color: EditorTheme.muted }
            }
            Label { Layout.fillWidth: true; visible: root.renderState.stage === "ready" && !!root.renderState.result.path; text: I18n.t("editor.export_complete") + "\n" + (root.renderState.result.path || ""); wrapMode: Text.WrapAnywhere; color: EditorTheme.success }
            Label { Layout.fillWidth: true; visible: root.renderState.stage === "error"; text: I18n.t("editor.export_failed"); wrapMode: Text.Wrap; color: EditorTheme.danger }
            InspectorSection { Layout.fillWidth: true; visible: root.renderState.error.length > 0 && root.renderState.error !== "cancelled"; title: I18n.t("editor.details"); expanded: false; Label { Layout.fillWidth: true; text: root.renderState.error; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: EditorTheme.secondary } }
        }
    }
    footer: RowLayout {
        spacing: 8
        Item { Layout.fillWidth: true }
        EditorButton { text: I18n.t("close"); onClicked: root.close() }
        EditorButton { text: I18n.t("cancel"); visible: root.renderState.busy; onClicked: root.renderState.cancel() }
        EditorButton {
            text: I18n.t("editor.export_video"); primary: true; visible: !root.renderState.busy; enabled: editor.timelineClips.length > 0
            Layout.rightMargin: 20; Layout.bottomMargin: 16
            onClicked: { if (!root.editor || !root.editor.render) return; var path = root.editor.render.chooseOutput(root.editor.doc); if (path) root.editor.render.export(root.editor.doc, path) }
        }
    }
}
