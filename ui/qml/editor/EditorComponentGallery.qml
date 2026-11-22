import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Window {
    id: root
    width: 760
    height: 500
    minimumWidth: 600
    minimumHeight: 380
    visible: false
    title: I18n.t("editor.components")
    color: EditorTheme.bgApp

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            anchors.margins: EditorTheme.space4
            spacing: EditorTheme.space4
            Label { text: I18n.t("editor.components"); color: EditorTheme.textPrimary; font.pixelSize: 20; font.weight: Font.DemiBold }
            Label { text: I18n.t("editor.components_hint"); color: EditorTheme.textSecondary; font.pixelSize: EditorTheme.fontSize; wrapMode: Text.Wrap; Layout.fillWidth: true }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: buttons.implicitHeight + EditorTheme.space4 * 2
                radius: EditorTheme.radiusPanel
                color: EditorTheme.bgPanel
                border.width: 1
                border.color: EditorTheme.borderSubtle
                RowLayout {
                    id: buttons
                    anchors.fill: parent
                    anchors.margins: EditorTheme.space4
                    spacing: EditorTheme.space2
                    EditorButton { text: I18n.t("editor.primary_action"); variant: "primary"; iconName: "share" }
                    EditorButton { text: I18n.t("editor.secondary_action"); variant: "secondary" }
                    EditorButton { text: I18n.t("editor.ghost_action"); variant: "ghost" }
                    EditorButton { text: I18n.t("editor.toggle_action"); variant: "toggle"; checkable: true; checked: true; iconName: "magnet" }
                    EditorButton { text: I18n.t("editor.segmented"); variant: "segmented"; checkable: true; checked: true }
                    EditorButton { text: I18n.t("editor.delete"); variant: "danger"; iconName: "trash" }
                    EditorButton { iconOnly: true; variant: "icon"; iconName: "settings"; text: I18n.t("editor.properties") }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: tabs.implicitHeight + EditorTheme.space4 * 2
                radius: EditorTheme.radiusPanel
                color: EditorTheme.bgPanel
                border.width: 1
                border.color: EditorTheme.borderSubtle
                RowLayout {
                    id: tabs
                    anchors.fill: parent
                    anchors.margins: EditorTheme.space4
                    spacing: EditorTheme.space1
                    Repeater {
                        model: ["media", "edit", "color", "audio", "titles", "deliver"]
                        EditorButton { required property int index; required property string modelData; text: I18n.t("editor." + modelData); variant: "tab"; checkable: true; checked: index === 1 }
                    }
                }
            }

            Label { text: I18n.t("editor.focus_hint"); color: EditorTheme.textDisabled; font.pixelSize: EditorTheme.smallSize; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }
}
