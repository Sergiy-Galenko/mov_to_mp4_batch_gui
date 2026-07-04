import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property bool collapsed: false
    property int activeIndex: 0
    property var navigationItems: []
    signal sectionRequested(int pageIndex, string target, int navIndex)
    signal addFilesRequested()
    signal addFolderRequested()
    signal dedupeRequested()

    width: collapsed ? 58 : Theme.sidebarWidth
    color: Theme.bgSecondary
    border.width: 1
    border.color: Theme.borderSubtle
    clip: true

    Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space3
        spacing: Theme.space3

        Label {
            visible: !root.collapsed
            text: I18n.t("mode")
            color: Theme.textDisabled
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontSizeXs
        }

        ScrollView {
            id: navScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: navScroll.availableWidth
                Layout.fillWidth: true
                spacing: Theme.space1

                Repeater {
                    model: root.navigationItems
                    delegate: ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space1

                        Label {
                            visible: !root.collapsed && index === 5
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.space2
                            text: I18n.t("settings")
                            color: Theme.textDisabled
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontSizeXs
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Theme.buttonHeight
                            radius: Theme.radiusSm
                            color: root.activeIndex === index ? Theme.bgElevated : (mouse.containsMouse ? Theme.overlayHover : Theme.transparent)
                            border.width: root.activeIndex === index || mouse.containsMouse ? 1 : 0
                            border.color: root.activeIndex === index ? Theme.borderStrong : Theme.borderSubtle

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.space3
                                anchors.rightMargin: Theme.space2
                                spacing: Theme.space2

                                Label {
                                    text: modelData.icon
                                    color: root.activeIndex === index ? Theme.accent : Theme.textSecondary
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontSizeSm
                                    font.bold: root.activeIndex === index
                                    Layout.preferredWidth: 24
                                    horizontalAlignment: Text.AlignHCenter
                                }

                                Label {
                                    visible: !root.collapsed
                                    Layout.fillWidth: true
                                    text: I18n.t(modelData.title)
                                    color: root.activeIndex === index ? Theme.textPrimary : Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeSm
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: mouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: root.sectionRequested(modelData.page, modelData.target || "", index)
                            }
                        }
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderSubtle }

        SecondaryButton {
            Layout.fillWidth: true
            text: root.collapsed ? "+" : "+  " + I18n.t("add_files")
            onClicked: root.addFilesRequested()
        }
        SecondaryButton {
            Layout.fillWidth: true
            text: root.collapsed ? "F" : "F  " + I18n.t("add_folder")
            onClicked: root.addFolderRequested()
        }
        SecondaryButton {
            Layout.fillWidth: true
            text: root.collapsed ? "D" : "D  " + I18n.t("hash_dedupe")
            onClicked: root.dedupeRequested()
        }
    }
}
