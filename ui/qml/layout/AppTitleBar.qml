import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQml.Models 2.15
import App 1.0
import "../components"

Item {
    id: root
    property var appRoot
    property url logoSource: ""
    readonly property int sidebarExtent: appRoot && appRoot.sidebarCollapsed ? 62 : Theme.sidebarWidth
    implicitHeight: Theme.titlebarHeight
    objectName: "appTitleBar"

    Rectangle { anchors.fill: parent; color: Theme.windowBackground }
    Rectangle { width: root.sidebarExtent; height: parent.height; color: Theme.sidebarBackground }

    // Native traffic lights remain above this area on macOS. Drag only on the
    // empty toolbar; buttons keep their normal pointer and keyboard behavior.
    MouseArea {
        id: titleBarDragArea
        objectName: "titleBarDragArea"
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        property point clickPos: Qt.point(0, 0)
        property bool manualDragging: false

        onPressed: function(mouse) {
            clickPos = Qt.point(mouse.x, mouse.y)
            manualDragging = false
            if (!root.appRoot) return
            if (root.appRoot.visibility === Window.FullScreen) return

            var systemMoved = false
            try {
                systemMoved = root.appRoot.startSystemMove()
            } catch (e) {
                systemMoved = false
            }
            if (!systemMoved) {
                manualDragging = true
            }
        }

        onPositionChanged: function(mouse) {
            if (!manualDragging || !root.appRoot) return
            if (root.appRoot.visibility === Window.FullScreen) return

            if (root.appRoot.visibility === Window.Maximized) {
                var ratio = mouse.x / Math.max(root.appRoot.width, 1)
                root.appRoot.showNormal()
                clickPos.x = root.appRoot.width * ratio
            }

            var deltaX = mouse.x - clickPos.x
            var deltaY = mouse.y - clickPos.y
            root.appRoot.x += deltaX
            root.appRoot.y += deltaY
        }

        onReleased: manualDragging = false
        onCanceled: manualDragging = false

        onDoubleClicked: {
            manualDragging = false
            if (!root.appRoot || root.appRoot.visibility === Window.FullScreen) return
            if (root.appRoot.visibility === Window.Maximized) {
                root.appRoot.showNormal()
            } else {
                root.appRoot.showMaximized()
            }
        }
    }
    RowLayout {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: root.sidebarExtent
        spacing: 8
        Item { Layout.preferredWidth: Theme.isMac ? 86 : 8; visible: !appRoot || !appRoot.sidebarCollapsed }
        BrandMark {
            visible: !Theme.isMac && (!appRoot || !appRoot.sidebarCollapsed)
            source: root.logoSource
            Layout.preferredWidth: 25; Layout.preferredHeight: 25
        }
        Item { Layout.fillWidth: true }
        AppIconButton {
            objectName: "sidebarToggleButton"
            Layout.rightMargin: 12
            // In collapsed macOS mode, native window controls occupy the top
            // toolbar; keep the sidebar toggle below them in the content bar.
            visible: !(Theme.isMac && appRoot && appRoot.sidebarCollapsed)
            iconName: "sidebar"
            accessibleLabel: appRoot && appRoot.sidebarCollapsed ? I18n.t("expand") : I18n.t("collapse")
            onClicked: if (appRoot) appRoot.sidebarCollapsed = !appRoot.sidebarCollapsed
        }
    }
    RowLayout {
        anchors.left: parent.left
        anchors.leftMargin: root.sidebarExtent + (Theme.isMac && appRoot && appRoot.sidebarCollapsed ? 36 : 20)
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        AppIconButton {
            visible: Theme.isMac && appRoot && appRoot.sidebarCollapsed
            iconName: "sidebar"
            accessibleLabel: I18n.t("expand")
            onClicked: appRoot.sidebarCollapsed = false
        }
        Rectangle {
            Layout.preferredWidth: 68
            Layout.preferredHeight: 30
            radius: Theme.isMac ? 15 : Theme.radiusButton
            color: Theme.panelSecondary
            border.width: 1
            border.color: Theme.borderMuted
            Row {
                anchors.fill: parent
                AppIconButton {
                    objectName: "navigationBack"
                    width: 33; height: 30
                    enabled: appRoot && appRoot.canNavigateBack
                    iconName: "back"
                    accessibleLabel: I18n.t("design.back")
                    onClicked: appRoot.navigateHistory(-1)
                }
                Rectangle { width: 1; height: 16; y: 7; color: Theme.borderDefault }
                AppIconButton {
                    objectName: "navigationForward"
                    width: 33; height: 30
                    enabled: appRoot && appRoot.canNavigateForward
                    iconName: "chevron"
                    accessibleLabel: I18n.t("design.forward")
                    onClicked: appRoot.navigateHistory(1)
                }
            }
        }
        Label {
            objectName: "currentPageTitle"
            Layout.fillWidth: true
            Layout.minimumWidth: 60
            text: appRoot ? appRoot.currentSectionTitle() : I18n.t("app.title")
            font.family: Theme.bodyFont
            font.pixelSize: Theme.fontHeading
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            elide: Text.ElideRight
        }
        SystemStatusBar {
            id: systemStatusBar
            appRoot: root.appRoot
        }
        HistoryButtons { history: appRoot ? appRoot.settingsHistory : null; targetWindow: appRoot }
        AppIconButton {
            iconName: "bell"
            accessibleLabel: I18n.t("notifications")
            prominent: appRoot && appRoot.toastHistory.length > 0
            onClicked: appRoot && appRoot.openNotifications()
        }
        AppIconButton {
            visible: root.width > 960
            iconName: Theme.lightMode ? "moon" : "sun"
            accessibleLabel: Theme.lightMode ? I18n.t("switch_to_dark_theme") : I18n.t("switch_to_light_theme")
            onClicked: if (backend) backend.themeMode = Theme.lightMode ? "dark" : "light"
        }
        AppIconButton {
            objectName: "appearanceButton"
            iconName: "palette"
            accessibleLabel: I18n.t("appearance.title")
            onClicked: appRoot && appRoot.openAppearance()
        }
        AppIconButton {
            id: menuButton
            iconName: "more"
            accessibleLabel: I18n.t("design.app_menu")
            onClicked: applicationMenu.open()
            Menu {
                id: applicationMenu
                objectName: "applicationMenu"
                y: menuButton.height + 4
                width: 236
                padding: 6
                background: Rectangle { color: Theme.panelBackground; radius: Theme.radiusMd; border.width: 1; border.color: Theme.borderDefault }
                MenuItem { text: I18n.t("nav_queue"); onTriggered: appRoot.openTopMode("convert") }
                MenuItem { text: I18n.t("workspace_photo"); onTriggered: appRoot.openTopMode("photo") }
                MenuItem { text: I18n.t("workspace_video"); onTriggered: appRoot.openTopMode("video") }
                MenuItem { text: I18n.t("workspace_text"); onTriggered: appRoot.openTopMode("text") }
                MenuItem { text: I18n.t("nav_montage"); onTriggered: appRoot.openTopMode("montage") }
                MenuSeparator {}
                Menu {
                    id: languageMenu
                    objectName: "languageMenu"
                    title: I18n.t("language")
                    Instantiator {
                        model: backend ? backend.availableLanguages : []
                        onObjectAdded: function(index, object) { languageMenu.insertItem(index, object) }
                        onObjectRemoved: function(index, object) { languageMenu.removeItem(object) }
                        delegate: MenuItem {
                            required property var modelData
                            text: modelData.label
                            checkable: true
                            checked: appRoot && appRoot.languageActive(modelData.code)
                            onTriggered: appRoot.setAppLanguage(modelData.code)
                        }
                    }
                }
                MenuItem { text: I18n.t("switch_to_dark_theme"); onTriggered: if (backend) backend.themeMode = "dark" }
                MenuItem { text: I18n.t("switch_to_light_theme"); onTriggered: if (backend) backend.themeMode = "light" }
                MenuSeparator {}
                MenuItem { text: I18n.t("design.deduplicate"); onTriggered: if (backend) backend.deduplicateQueueByHash() }
                MenuItem { text: I18n.t("system.title"); onTriggered: systemStatusBar.openDetails() }
                MenuItem { text: I18n.t("settings"); onTriggered: appRoot.openSidebarSection(5, "core", -1) }
            }
        }
    }
}
