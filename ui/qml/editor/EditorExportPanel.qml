import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
ColumnLayout {
    id: root; property var editor
    property bool showExport: true
    readonly property var options: editor.doc.export_settings
    readonly property var resolutionValues: ["timeline", "1920x1080", "3840x2160", "1280x720", "1080x1920"]
    readonly property var fpsValues: [0, 24, 25, 30, 50, 60]
    readonly property var qualityValues: ["auto", "low", "medium", "high"]
    spacing: 10
    function update(values) { editor.project.updateSection("export_settings", values) }
    GridLayout {
        Layout.fillWidth: true; columns: 2; rowSpacing: 8; columnSpacing: 10
        Label { text: I18n.t("editor.format"); color: EditorTheme.secondary }
        EditorCombo { Layout.fillWidth: true; model: ["mp4","mov","mkv","avi"]; currentIndex: Math.max(0, model.indexOf(root.options.format)); onActivated: root.update({format: currentText}) }
        Label { text: I18n.t("editor.codec"); color: EditorTheme.secondary }
        EditorCombo { Layout.fillWidth: true; model: ["h264","h265","prores","copy"]; currentIndex: Math.max(0, model.indexOf(root.options.codec)); onActivated: root.update({codec: currentText, fast_copy: currentText === "copy"}) }
        Label { text: I18n.t("editor.resolution"); color: EditorTheme.secondary }
        EditorCombo { Layout.fillWidth: true; model: [I18n.t("editor.timeline"), "1920x1080", "3840x2160", "1280x720", "1080x1920"]; currentIndex: Math.max(0, root.resolutionValues.indexOf(root.options.resolution)); onActivated: root.update({resolution: root.resolutionValues[currentIndex]}) }
        Label { text: I18n.t("editor.frame_rate"); color: EditorTheme.secondary }
        EditorCombo { Layout.fillWidth: true; model: [I18n.t("editor.timeline"), "24", "25", "30", "50", "60"]; currentIndex: Math.max(0, root.fpsValues.indexOf(Number(root.options.fps))); onActivated: root.update({fps: root.fpsValues[currentIndex]}) }
        Label { text: I18n.t("editor.quality"); color: EditorTheme.secondary }
        EditorCombo { Layout.fillWidth: true; model: [I18n.t("editor.quality_auto"), I18n.t("editor.quality_low"), I18n.t("editor.quality_medium"), I18n.t("editor.quality_high")]; currentIndex: Math.max(0, root.qualityValues.indexOf(root.options.quality)); onActivated: root.update({quality: root.qualityValues[currentIndex]}) }
        Label { text: "kbps"; color: EditorTheme.secondary }
        EditorNumber { Layout.fillWidth: true; maximum: 200000; value: root.options.bitrate || 0; onEdited: function(number) { root.update({bitrate: number}) } }
        Label { text: I18n.t("editor.fast_copy"); color: EditorTheme.secondary }
        Switch { checked: !!root.options.fast_copy; onToggled: root.update({fast_copy: checked, codec: checked ? "copy" : "h264"}) }
    }
    Label { Layout.fillWidth: true; text: I18n.t("editor.copy_hint"); visible: !!root.options.fast_copy; color: EditorTheme.muted; wrapMode: Text.Wrap; font.pixelSize: EditorTheme.smallSize }
    Label { text: I18n.t("editor.filename"); color: EditorTheme.secondary }
    EditorField { Layout.fillWidth: true; text: root.options.filename || ""; placeholderText: editor.doc.project_name + "_Final"; onEditingFinished: root.update({filename: text}) }
    Label { text: I18n.t("editor.location"); color: EditorTheme.secondary }
    RowLayout {
        Layout.fillWidth: true
        EditorField { Layout.fillWidth: true; text: root.options.directory || ""; placeholderText: I18n.t("editor.choose_on_export"); onEditingFinished: root.update({directory: text}) }
        EditorButton { iconName: "folder"; iconOnly: true; text: I18n.t("editor.browse"); onClicked: { var path = editor.project.chooseFolder(); if (path) root.update({directory: path}) } }
    }
    EditorButton { Layout.fillWidth: true; visible: root.showExport; primary: true; iconName: "share"; text: I18n.t("editor.export_video"); enabled: editor.timelineClips.length > 0 && !editor.render.busy; onClicked: editor.openExport() }
}
