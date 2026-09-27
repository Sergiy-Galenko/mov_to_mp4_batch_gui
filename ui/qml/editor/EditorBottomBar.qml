import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
Rectangle {
    id: root; property var editor
    implicitHeight: EditorTheme.controlHeight + 12; color: EditorTheme.panel
    RowLayout {
        anchors.fill: parent; anchors.margins: 6; spacing: 4
        Repeater {
            model: [{key:"media", icon:"folder"},{key:"cut",icon:"crop"},{key:"edit",icon:"film"},{key:"color",icon:"palette"},{key:"audio",icon:"audio"},{key:"deliver",icon:"share"}]
            EditorButton { required property int index; required property var modelData; text: I18n.t("editor." + modelData.key); iconName: modelData.icon; checked: editor.activeWorkspacePage === index; onClicked: editor.chooseWorkspace(index) }
        }
        Item { Layout.fillWidth: true }
        Label { visible: root.width > 1120; text: I18n.t("editor.autosave") + ": " + I18n.t(editor.doc.project_settings.autosave ? "editor.on" : "editor.off"); color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize }
        Label { text: editor.doc.project_settings.width + " × " + editor.doc.project_settings.height + " · " + editor.fps + " fps"; color: EditorTheme.secondary; font.pixelSize: EditorTheme.smallSize }
    }
}
