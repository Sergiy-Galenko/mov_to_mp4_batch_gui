import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    objectName: "appSidebar"
    property var appRoot
    property bool collapsed: false
    property int activeIndex: 0
    property var navigationItems: []
    property bool moreExpanded: false
    property alias searchField: navigationSearch
    signal sectionRequested(int pageIndex, string target, int navIndex)
    signal addFilesRequested()
    signal addFolderRequested()
    signal archiveRequested()
    signal updateRequested()
    signal dedupeRequested()

    Layout.preferredWidth: collapsed ? 62 : Theme.sidebarWidth
    Layout.minimumWidth: collapsed ? 62 : 220
    color: Theme.sidebarBackground
    clip: true

    onCollapsedChanged: if (appRoot && appRoot.sidebarCollapsed !== collapsed) appRoot.sidebarCollapsed = collapsed

    onActiveIndexChanged: {
        if (!root.collapsed && root.activeIndex >= 0 && root.activeIndex < root.navigationItems.length && !root.navigationItems[root.activeIndex].primary)
            root.moreExpanded = true
        revealActiveTimer.restart()
    }
    onHeightChanged: revealActiveTimer.restart()
    Component.onCompleted: revealActiveTimer.restart()
    Timer { id: revealActiveTimer; interval: 50; onTriggered: root.ensureActiveVisible() }
    function ensureActiveVisible() {
        var item = navigationRepeater.itemAt(activeIndex)
        var viewport = scroll.contentItem
        if (!item || !viewport) return
        var top = item.y
        var bottom = top + item.height
        if (top < viewport.contentY) viewport.contentY = top
        else if (bottom > viewport.contentY + viewport.height)
            viewport.contentY = Math.min(bottom - viewport.height, Math.max(0, viewport.contentHeight - viewport.height))
    }

    function navigationItemVisible(index) {
        if (index < 0 || index >= root.navigationItems.length)
            return false
        return root.collapsed || root.moreExpanded || !!root.navigationItems[index].primary
    }

    function groupVisible(index) {
        if (root.collapsed || !root.navigationItemVisible(index))
            return false
        for (var previous = index - 1; previous >= 0; --previous) {
            if (root.navigationItemVisible(previous))
                return root.navigationItems[previous].group !== root.navigationItems[index].group
        }
        return true
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: Theme.space2
        anchors.bottomMargin: Theme.space3
        spacing: Theme.space2

        AppTextField {
            id: navigationSearch
            objectName: "sidebarSearchField"
            visible: !root.collapsed
            Layout.leftMargin: 12; Layout.rightMargin: 12
            Layout.fillWidth: true
            search: true
            placeholderText: I18n.t("global_search")
            text: appRoot ? appRoot.globalSearchText : ""
            onTextChanged: if (appRoot) appRoot.runGlobalSearch(text)
            Keys.onReturnPressed: {
                if (appRoot) appRoot.activateSelectedSearchResult()
            }
            Keys.onDownPressed: if (appRoot) appRoot.moveGlobalSearchSelection(1)
            Keys.onUpPressed: if (appRoot) appRoot.moveGlobalSearchSelection(-1)
            Keys.onEscapePressed: {
                clear()
                if (appRoot) appRoot.runGlobalSearch("")
            }
        }

        RowLayout {
            visible: !root.collapsed
            Layout.fillWidth: true
            Layout.leftMargin: 16; Layout.rightMargin: 12
            Layout.topMargin: 8; Layout.bottomMargin: 10
            spacing: 10
            Rectangle {
                width: 42; height: 42
                radius: Theme.isMac ? 21 : 8
                color: Theme.panelSecondary
                BrandMark { anchors.centerIn: parent; width: 30; height: 30; source: appRoot ? appRoot.appLogoSource : "" }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label {
                    Layout.fillWidth: true
                    text: I18n.t("app.title")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeMd
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Label {
                    text: I18n.t("design.workspace")
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontMeta
                }
            }
        }

        ScrollView {
            id: scroll
            objectName: "navigationScroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            Column {
                width: scroll.availableWidth
                spacing: 2
                Repeater {
                    id: navigationRepeater
                    model: root.navigationItems
                    delegate: Item {
                        required property int index
                        required property var modelData
                        width: parent.width
                        height: root.navigationItemVisible(index) ? (root.groupVisible(index) ? 27 : 0) + Theme.navigationHeight : 0
                        Label {
                            visible: root.groupVisible(index)
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.leftMargin: 19; anchors.rightMargin: 12
                            height: 27
                            verticalAlignment: Text.AlignVCenter
                            text: I18n.t(modelData.group)
                            color: Theme.textDisabled
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        Button {
                            id: navButton
                            objectName: "nav_" + (modelData.target || modelData.title)
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.margins: 8
                            anchors.top: parent.top
                            anchors.topMargin: root.groupVisible(index) ? 27 : 0
                            height: Theme.navigationHeight
                            padding: 0
                            hoverEnabled: true
                            focusPolicy: Qt.StrongFocus
                            highlighted: root.activeIndex === index
                            Accessible.name: I18n.t(modelData.title)
                            Accessible.role: Accessible.PageTab
                            Accessible.selected: highlighted
                            ToolTip.visible: hovered && (root.collapsed || navigationLabel.truncated)
                            ToolTip.delay: 550
                            ToolTip.text: I18n.t(modelData.title)
                            onClicked: root.sectionRequested(modelData.page, modelData.target || "", index)
                            background: Rectangle {
                                radius: Theme.isMac ? 7 : 4
                                color: navButton.highlighted ? Theme.navigationSelection : navButton.hovered ? Theme.overlayHover : "transparent"
                                border.width: navButton.visualFocus ? 2 : 0
                                border.color: Theme.focusRing
                                Rectangle {
                                    visible: !Theme.isMac && navButton.highlighted
                                    width: 3; height: 18; radius: 2
                                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                    color: Theme.accent
                                }
                            }
                            contentItem: RowLayout {
                                spacing: 9
                                NavigationIcon {
                                    Layout.leftMargin: root.collapsed ? 8 : 9
                                    Layout.preferredWidth: 26; Layout.preferredHeight: 26
                                    glyphSize: 17
                                    name: modelData.icon || "settings"
                                    tint: modelData.tint || Theme.accent
                                }
                                Label {
                                    id: navigationLabel
                                    visible: !root.collapsed
                                    Layout.fillWidth: true
                                    Layout.rightMargin: 8
                                    text: I18n.t(modelData.title)
                                    color: navButton.highlighted ? Theme.navigationText : Theme.textPrimary
                                    font.pixelSize: Theme.fontSizeSm
                                    font.weight: navButton.highlighted ? Font.DemiBold : Font.Normal
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
                AppButton {
                    visible: !root.collapsed
                    width: parent.width - 16
                    x: 8
                    text: root.moreExpanded ? I18n.t("show_less") : I18n.t("show_more")
                    iconName: root.moreExpanded ? "close" : "plus"
                    onClicked: root.moreExpanded = !root.moreExpanded
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 16; Layout.rightMargin: 16
            Layout.preferredHeight: 1
            color: Theme.borderMuted
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 12; Layout.rightMargin: 12
            spacing: 6
            AppButton {
                Layout.fillWidth: true
                text: root.collapsed ? "" : I18n.t("add_files")
                iconName: "plus"
                Accessible.name: I18n.t("add_files")
                onClicked: root.addFilesRequested()
            }
            AppIconButton {
                visible: !root.collapsed
                iconName: "folder"
                accessibleLabel: I18n.t("add_folder")
                onClicked: root.addFolderRequested()
            }
            AppIconButton {
                objectName: "sidebarArchiveButton"
                iconName: "archive"
                accessibleLabel: I18n.t("nav_archive")
                ToolTip.text: I18n.t("nav_archive")
                onClicked: root.archiveRequested()
            }
            AppIconButton {
                objectName: "sidebarUpdateIconButton"
                iconName: "refresh"
                accessibleLabel: I18n.t("check_update")
                ToolTip.text: I18n.t("check_update")
                onClicked: root.updateRequested()
            }
        }
    }
}
