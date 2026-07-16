import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var appRoot
    property alias searchField: globalSearchField
    property url logoSource: ""
    implicitHeight: Theme.titlebarHeight
    color: Theme.panelBackground
    border.width: 0

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space4
        anchors.rightMargin: Theme.space3
        spacing: Theme.space3

        Image {
            Layout.preferredWidth: 28
            Layout.preferredHeight: 28
            source: root.logoSource
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            smooth: true
        }

        Label {
            text: I18n.t("app.title")
            color: Theme.textPrimary
            font.family: Theme.displayFont
            font.pixelSize: Theme.fontSizeLg
            font.weight: Font.DemiBold
        }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 22; color: Theme.borderMuted }

        Button {
            id: workspaceButton
            Layout.preferredWidth: 156
            implicitHeight: 32
            hoverEnabled: true
            Accessible.name: I18n.t("mode")
            onClicked: workspaceMenu.open()
            background: Rectangle {
                radius: Theme.radiusSm
                color: workspaceButton.hovered ? Theme.overlayHover : Theme.transparent
                border.width: workspaceButton.activeFocus ? 2 : 1
                border.color: workspaceButton.activeFocus ? Theme.focusRing : Theme.borderMuted
            }
            contentItem: RowLayout {
                spacing: Theme.space2
                Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.space2
                    text: appRoot ? appRoot.workspaceTitle() : I18n.t("nav_queue")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeSm
                    elide: Text.ElideRight
                }
                AppIcon { Layout.preferredWidth: 16; Layout.preferredHeight: 16; name: "chevron"; iconColor: Theme.textSecondary; rotation: 90 }
            }

            Menu {
                id: workspaceMenu
                y: workspaceButton.height + 4
                width: 188
                padding: 4
                background: Rectangle { color: Theme.panelBackground; border.width: 1; border.color: Theme.borderDefault; radius: Theme.radiusMd }
                MenuItem { text: I18n.t("nav_queue"); onTriggered: appRoot && appRoot.openTopMode("convert") }
                MenuItem { text: I18n.t("workspace_photo"); onTriggered: appRoot && appRoot.openTopMode("photo") }
                MenuItem { text: I18n.t("workspace_video"); onTriggered: appRoot && appRoot.openTopMode("video") }
                MenuItem { text: I18n.t("workspace_text"); onTriggered: appRoot && appRoot.openTopMode("text") }
                MenuSeparator {}
                MenuItem { text: I18n.t("nav_downloads"); onTriggered: appRoot && appRoot.openTopMode("downloads") }
            }
        }

        Item { Layout.fillWidth: true }

        AppTextField {
            id: globalSearchField
            Layout.preferredWidth: root.width > 1080 ? 236 : 168
            placeholderText: I18n.t("global_search")
            text: appRoot ? appRoot.globalSearchText : ""
            onTextChanged: if (appRoot) appRoot.runGlobalSearch(text)
            Keys.onReturnPressed: {
                if (appRoot && appRoot.globalSearchResults.length > 0)
                    appRoot.activateSearchResult(appRoot.globalSearchResults[0])
            }
        }

        AppIconButton {
            iconName: "bell"
            accessibleLabel: I18n.t("notifications")
            prominent: appRoot && appRoot.toastHistory.length > 0
            onClicked: appRoot && appRoot.openNotifications()
        }

        AppIconButton {
            iconName: Theme.lightMode ? "moon" : "sun"
            accessibleLabel: Theme.lightMode ? I18n.t("switch_to_dark_theme") : I18n.t("switch_to_light_theme")
            onClicked: {
                if (!backend)
                    return
                backend.themeMode = backend.themeMode === "light" ? "dark" : "light"
            }
        }

        Button {
            id: languageButton
            Layout.preferredWidth: 52
            implicitHeight: 32
            hoverEnabled: true
            Accessible.name: I18n.t("language")
            onClicked: languagePopup.open()
            background: Rectangle {
                radius: Theme.radiusSm
                color: languageButton.hovered ? Theme.overlayHover : Theme.transparent
                border.width: languageButton.activeFocus ? 2 : 0
                border.color: Theme.focusRing
            }
            contentItem: RowLayout {
                spacing: 3
                AppIcon { Layout.preferredWidth: 16; Layout.preferredHeight: 16; Layout.leftMargin: 4; name: "language"; iconColor: Theme.textSecondary }
                Label { text: appRoot ? appRoot.languageButtonLabel(appRoot._langVersion) : ""; color: Theme.textSecondary; font.pixelSize: 11; font.weight: Font.DemiBold }
            }

            Popup {
                id: languagePopup
                y: languageButton.height + 4
                width: 190
                padding: 6
                focus: true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { color: Theme.panelBackground; border.width: 1; border.color: Theme.borderDefault; radius: Theme.radiusMd }
                contentItem: ColumnLayout {
                    spacing: 2
                    Repeater {
                        model: backend ? backend.availableLanguages : []
                        delegate: Button {
                            id: languageOption
                            Layout.fillWidth: true
                            implicitHeight: 32
                            hoverEnabled: true
                            onClicked: { if (appRoot) appRoot.setAppLanguage(modelData.code); languagePopup.close() }
                            background: Rectangle { radius: Theme.radiusSm; color: appRoot && appRoot.languageActive(modelData.code) ? Theme.selectionBackground : languageOption.hovered ? Theme.overlayHover : Theme.transparent }
                            contentItem: Label { leftPadding: 8; rightPadding: 8; text: modelData.label || ""; color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                }
            }
        }

        AppIconButton {
            iconName: "settings"
            accessibleLabel: I18n.t("settings")
            onClicked: appRoot && appRoot.openSidebarSection(5, "core", appRoot.navIndexFor(5, "core"))
        }
    }
}
