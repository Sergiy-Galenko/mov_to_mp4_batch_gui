import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property bool collapsed: false
    property int activeIndex: 0
    signal sectionRequested(int index)
    signal addFilesRequested()
    signal addFolderRequested()
    signal dedupeRequested()

    width: collapsed ? 56 : Theme.sidebarWidth
    color: Theme.bgSurface
    border.width: 1
    border.color: Theme.bgBorder
    clip: true

    Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        Label {
            visible: !root.collapsed
            text: I18n.t("mode")
            color: Theme.textMuted
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
        }

        Repeater {
            model: [
                { title: "queue", icon: "Q" },
                { title: "analytics", icon: "A" },
                { title: "presets", icon: "P" },
                { title: "ffmpeg", icon: "F" },
                { title: "settings", icon: "S" }
            ]
            delegate: Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                radius: Theme.radiusButton
                color: root.activeIndex === index ? Theme.bgElevated : (mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
                border.width: root.activeIndex === index ? 1 : 0
                border.color: Theme.bgBorder

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    spacing: 9

                    Label {
                        text: modelData.icon
                        color: root.activeIndex === index ? Theme.accentPrimary : Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                        Layout.preferredWidth: 18
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Label {
                        visible: !root.collapsed
                        Layout.fillWidth: true
                        text: I18n.t(modelData.title)
                        color: root.activeIndex === index ? Theme.textPrimary : Theme.textSecondary
                        font.pixelSize: Theme.fontSmall
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.sectionRequested(index)
                }
            }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.bgBorder }

        Button {
            Layout.fillWidth: true
            text: root.collapsed ? "📄" : "📄  " + I18n.t("add_files")
            onClicked: root.addFilesRequested()
        }
        Button {
            Layout.fillWidth: true
            text: root.collapsed ? "📁" : "📁  " + I18n.t("add_folder")
            onClicked: root.addFolderRequested()
        }
        Button {
            Layout.fillWidth: true
            text: root.collapsed ? "🔎" : "🔎  " + I18n.t("hash_dedupe")
            onClicked: root.dedupeRequested()
        }

        Item { Layout.fillHeight: true }
    }
}
