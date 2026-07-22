import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtCore
import App 1.0

Popup {
    id: root
    width: parent ? Math.max(360, Math.min(parent.width - 24, Math.round(parent.width * 0.82), 680)) : 640
    height: parent ? Math.max(420, Math.min(parent.height - 24, Math.round(parent.height * 0.82), 600)) : 560
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    property string currentVersion: (typeof backend !== "undefined" && backend) ? backend.appVersion : "1.2.1"
    property url logoSource: Qt.resolvedUrl("../../../assets/app-logo.png")
    property bool compact: width < 520
    property int adaptiveMargin: compact ? Theme.space4 : Theme.space5
    property int logoSize: compact ? 48 : 64

    Settings {
        id: settings
        category: "App"
        property string lastSeenVersion: ""
    }

    Component.onCompleted: {
        if (settings.lastSeenVersion !== root.currentVersion)
            root.open()
    }

    onClosed: settings.lastSeenVersion = root.currentVersion

    background: Rectangle {
        color: Theme.bgElevated
        radius: Theme.radiusLg
        border.width: 1
        border.color: Theme.borderStrong
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.adaptiveMargin
        spacing: root.compact ? Theme.space3 : Theme.space4

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space3

            Image {
                Layout.preferredWidth: root.logoSize
                Layout.preferredHeight: root.logoSize
                source: root.logoSource
                fillMode: Image.PreserveAspectFit
                smooth: true
                asynchronous: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Label {
                    Layout.fillWidth: true
                    text: I18n.t("app.title")
                    color: Theme.textPrimary
                    font.family: Theme.displayFont
                    font.pixelSize: root.compact ? Theme.fontSizeLg : Theme.fontSizeXl
                    font.bold: true
                    elide: Text.ElideRight
                }

                Label {
                    Layout.fillWidth: true
                    text: I18n.t("version") + " " + root.currentVersion
                    color: Theme.accentPrimary
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontSizeMd
                    elide: Text.ElideRight
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.borderSubtle
        }

        ScrollView {
            id: releaseScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            contentHeight: releaseColumn.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ColumnLayout {
                id: releaseColumn
                width: releaseScroll.availableWidth
                spacing: root.compact ? Theme.space3 : Theme.space4

                ReleaseSection {
                    title: I18n.t("whats_new_workspace_title")
                    accent: Theme.accentPrimary
                    body: I18n.t("whats_new_workspace_body")
                }

                ReleaseSection {
                    title: I18n.t("whats_new_preview_title")
                    accent: Theme.statusSuccess
                    body: I18n.t("whats_new_preview_body")
                }

                ReleaseSection {
                    title: I18n.t("whats_new_text_title")
                    accent: Theme.statusWarning
                    body: I18n.t("whats_new_text_body")
                }

                ReleaseSection {
                    title: I18n.t("whats_new_ui_title")
                    accent: Theme.statusRunning
                    body: I18n.t("whats_new_ui_body")
                }
            }
        }

        PrimaryButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Math.min(220, parent.width)
            Layout.preferredHeight: 44
            text: I18n.t("get_started")
            font.pixelSize: Theme.fontSizeMd
            font.bold: true
            onClicked: root.close()
        }
    }

    component ReleaseSection: ColumnLayout {
        property string title: ""
        property string body: ""
        property color accent: Theme.accentPrimary

        Layout.fillWidth: true
        Layout.preferredWidth: releaseScroll.availableWidth
        spacing: Theme.space2

        Label {
            Layout.fillWidth: true
            text: title
            color: accent
            font.pixelSize: root.compact ? Theme.fontSizeMd : Theme.fontSizeLg
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Text {
            width: parent.width
            Layout.fillWidth: true
            Layout.preferredWidth: parent.width
            text: body
            textFormat: Text.RichText
            wrapMode: Text.WordWrap
            color: Theme.textSecondary
            font.family: Theme.bodyFont
            font.pixelSize: root.compact ? Theme.fontSizeSm : Theme.fontSizeMd
            lineHeight: 1.35
        }
    }
}
