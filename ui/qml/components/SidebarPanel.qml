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

    Layout.preferredWidth: collapsed ? 58 : Theme.sidebarWidth
    Layout.minimumWidth: collapsed ? 58 : 196
    color: Theme.sidebarBackground
    border.width: 0
    clip: true

    Behavior on Layout.preferredWidth {
        NumberAnimation { duration: 170; easing.type: Easing.OutCubic }
    }

    function groupVisible(index) {
        if (root.collapsed || index < 0 || index >= root.navigationItems.length)
            return false
        var current = root.navigationItems[index]
        var previous = index > 0 ? root.navigationItems[index - 1] : null
        return current.group && (!previous || previous.group !== current.group)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: Theme.space3
        anchors.bottomMargin: Theme.space3
        spacing: Theme.space2

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: root.collapsed ? Theme.space2 : Theme.space3
            Layout.rightMargin: Theme.space2
            Layout.preferredHeight: 30
            spacing: Theme.space2

            Label {
                visible: !root.collapsed
                Layout.fillWidth: true
                text: I18n.t("app.title")
                color: Theme.textPrimary
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontSizeSm
                font.bold: true
                elide: Text.ElideRight
            }

            AppIconButton {
                Layout.alignment: Qt.AlignRight
                iconName: root.collapsed ? "chevron" : "chevron"
                rotation: root.collapsed ? 0 : 180
                accessibleLabel: root.collapsed ? I18n.t("expand") : I18n.t("collapse")
                onClicked: root.collapsed = !root.collapsed
            }
        }

        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            Column {
                width: scroll.availableWidth
                spacing: 2

                Repeater {
                    model: root.navigationItems

                    delegate: Item {
                        width: parent.width
                        height: (root.groupVisible(index) ? 26 : 0) + 36

                        Label {
                            visible: root.groupVisible(index)
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: Theme.space3
                            anchors.rightMargin: Theme.space2
                            height: 26
                            verticalAlignment: Text.AlignVCenter
                            text: I18n.t(modelData.group).toUpperCase()
                            color: Theme.textMuted
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Button {
                            id: navButton
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: root.collapsed ? Theme.space2 : Theme.space2
                            anchors.rightMargin: Theme.space2
                            anchors.top: parent.top
                            anchors.topMargin: root.groupVisible(index) ? 26 : 0
                            height: 34
                            hoverEnabled: true
                            focusPolicy: Qt.StrongFocus
                            Accessible.name: I18n.t(modelData.title)
                            ToolTip.visible: root.collapsed && hovered
                            ToolTip.delay: 550
                            ToolTip.text: I18n.t(modelData.title)
                            onClicked: root.sectionRequested(modelData.page, modelData.target || "", index)

                            background: Rectangle {
                                radius: Theme.radiusSm
                                color: root.activeIndex === index
                                       ? Theme.selectionBackground
                                       : navButton.hovered ? Theme.overlayHover : Theme.transparent
                                border.width: navButton.activeFocus ? 2 : 0
                                border.color: Theme.focusRing
                            }

                            contentItem: RowLayout {
                                spacing: root.collapsed ? 0 : Theme.space2

                                AppIcon {
                                    Layout.preferredWidth: 18
                                    Layout.preferredHeight: 18
                                    Layout.leftMargin: root.collapsed ? 8 : 10
                                    name: modelData.icon || "dot"
                                    iconColor: root.activeIndex === index ? Theme.accentPrimary : Theme.textSecondary
                                }

                                Label {
                                    visible: !root.collapsed
                                    Layout.fillWidth: true
                                    text: I18n.t(modelData.title)
                                    color: root.activeIndex === index ? Theme.textPrimary : Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeSm
                                    font.weight: root.activeIndex === index ? Font.DemiBold : Font.Normal
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.space2
            Layout.rightMargin: Theme.space2
            Layout.preferredHeight: 1
            color: Theme.borderMuted
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.space2
            Layout.rightMargin: Theme.space2
            spacing: 2

            Button {
                id: addFilesButton
                Layout.fillWidth: true
                implicitHeight: 34
                hoverEnabled: true
                Accessible.name: I18n.t("add_files")
                ToolTip.visible: root.collapsed && hovered
                ToolTip.text: I18n.t("add_files")
                onClicked: root.addFilesRequested()
                background: Rectangle {
                    radius: Theme.radiusSm
                    color: addFilesButton.hovered ? Theme.overlayHover : Theme.transparent
                }
                contentItem: RowLayout {
                    spacing: Theme.space2
                    AppIcon { Layout.preferredWidth: 18; Layout.preferredHeight: 18; Layout.leftMargin: root.collapsed ? 8 : 10; name: "plus"; iconColor: Theme.textSecondary }
                    Label { visible: !root.collapsed; Layout.fillWidth: true; text: I18n.t("add_files"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
                }
            }

            Button {
                id: addFolderButton
                Layout.fillWidth: true
                implicitHeight: 34
                hoverEnabled: true
                Accessible.name: I18n.t("add_folder")
                ToolTip.visible: root.collapsed && hovered
                ToolTip.text: I18n.t("add_folder")
                onClicked: root.addFolderRequested()
                background: Rectangle {
                    radius: Theme.radiusSm
                    color: addFolderButton.hovered ? Theme.overlayHover : Theme.transparent
                }
                contentItem: RowLayout {
                    spacing: Theme.space2
                    AppIcon { Layout.preferredWidth: 18; Layout.preferredHeight: 18; Layout.leftMargin: root.collapsed ? 8 : 10; name: "folder"; iconColor: Theme.textSecondary }
                    Label { visible: !root.collapsed; Layout.fillWidth: true; text: I18n.t("add_folder"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
                }
            }
        }
    }
}
