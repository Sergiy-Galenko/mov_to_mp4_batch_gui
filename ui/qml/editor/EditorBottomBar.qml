import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property var editor
    implicitHeight: 34
    color: EditorTheme.bgPanel
    border.width: 1
    border.color: EditorTheme.borderSubtle
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: EditorTheme.space3
        anchors.rightMargin: EditorTheme.space3
        spacing: EditorTheme.space3
        Label { text: I18n.t("editor.autosave") + ": " + I18n.t(editor.doc.project_settings.autosave ? "editor.on" : "editor.off"); color: EditorTheme.textSecondary; font.pixelSize: EditorTheme.smallSize }
        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 14; color: EditorTheme.borderSubtle }
        Label { text: editor.doc.project_settings.width + " × " + editor.doc.project_settings.height + " · " + editor.fps + " fps"; color: EditorTheme.textSecondary; font.pixelSize: EditorTheme.smallSize }
        Item { Layout.fillWidth: true }
        Label { text: I18n.t("editor.shortcuts_hint"); color: EditorTheme.textDisabled; font.pixelSize: EditorTheme.smallSize; elide: Text.ElideRight }
    }
}
