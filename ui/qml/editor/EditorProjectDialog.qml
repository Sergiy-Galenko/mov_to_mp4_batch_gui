import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
EditorDialog {
    id: root; objectName: "editorProjectDialog"
    property var editor
    property bool creating: true
    parent: editor.contentItem
    anchors.centerIn: parent
    width: Math.min(540, parent.width - 32)
    title: I18n.t(creating ? "editor.new_project" : "editor.project_settings")
    function openNew() { creating = true; name.text = I18n.t("editor.untitled"); location.text = ""; resolution.currentIndex = 0; rate.currentIndex = 2; automatic.checked = true; interval.currentIndex = 2; open() }
    function openSettings() {
        creating = false; name.text = editor.doc.project_name
        location.text = editor.project.path ? editor.project.path.replace(/[/\\][^/\\]+$/, "") : ""
        var s = editor.doc.project_settings
        resolution.currentIndex = Math.max(0, resolution.model.indexOf(s.width + "x" + s.height))
        rate.currentIndex = Math.max(0, rate.model.indexOf(String(s.fps)))
        automatic.checked = s.autosave; interval.currentIndex = [1,2,5,10,15].indexOf(s.autosave_minutes)
        open()
    }
    contentItem: ColumnLayout {
        spacing: 12
        Label { text: I18n.t("editor.project_name"); color: EditorTheme.secondary }
        EditorField { id: name; objectName: "projectNameField"; Layout.fillWidth: true }
        Label { text: I18n.t("editor.location"); color: EditorTheme.secondary }
        RowLayout {
            Layout.fillWidth: true
            EditorField { id: location; Layout.fillWidth: true; placeholderText: I18n.t("editor.choose_on_save") }
            EditorButton { text: I18n.t("editor.browse"); onClicked: { var path = editor.project.chooseFolder(); if (path) location.text = path } }
        }
        Label { Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; text: location.text ? location.text + "/" + name.text.replace(/[/\\:]/g,"_") + ".vproj" : ""; color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize }
        GridLayout {
            columns: 2; columnSpacing: 12; rowSpacing: 8; Layout.fillWidth: true
            Label { text: I18n.t("editor.resolution"); color: EditorTheme.secondary }
            EditorCombo { id: resolution; model: ["1920x1080","3840x2160","1280x720","1080x1920","1080x1080"]; Layout.fillWidth: true }
            Label { text: I18n.t("editor.frame_rate"); color: EditorTheme.secondary }
            EditorCombo { id: rate; model: ["24","25","30","50","60"]; Layout.fillWidth: true }
            Label { text: I18n.t("editor.autosave"); color: EditorTheme.secondary }
            Switch { id: automatic; checked: true; palette.highlight: EditorTheme.accent }
            Label { text: I18n.t("editor.interval"); color: EditorTheme.secondary }
            EditorCombo { id: interval; enabled: automatic.checked; model: ["1 " + I18n.t("editor.minutes_short"), "2 " + I18n.t("editor.minutes_short"), "5 " + I18n.t("editor.minutes_short"), "10 " + I18n.t("editor.minutes_short"), "15 " + I18n.t("editor.minutes_short")]; currentIndex: 2; Layout.fillWidth: true }
        }
        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: I18n.t("editor.autosave_hint"); color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            EditorButton { text: I18n.t("cancel"); onClicked: root.close() }
            EditorButton {
                text: I18n.t(root.creating ? "editor.create_project" : "editor.apply"); primary: true; enabled: name.text.trim().length > 0
                onClicked: {
                    var dimensions = resolution.currentText.split("x")
                    var settings = {width: Number(dimensions[0]), height: Number(dimensions[1]), fps: Number(rate.currentText), autosave: automatic.checked, autosave_minutes: [1,2,5,10,15][interval.currentIndex]}
                    if (root.creating) editor.project.create(name.text, settings)
                    else { editor.project.rename(name.text); editor.project.updateSection("project_settings", settings) }
                    if (location.text && (root.creating || location.text !== editor.project.path.replace(/[/\\][^/\\]+$/, ""))) {
                        var path = location.text + "/" + name.text.replace(/[/\\:]/g,"_") + ".vproj"
                        editor.project.saveNewLocation(path)
                    }
                    root.close()
                }
            }
        }
    }
}
