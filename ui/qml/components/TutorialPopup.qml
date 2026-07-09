import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
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

    property bool compact: width < 520
    property int adaptiveMargin: compact ? Theme.space4 : Theme.space6

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

        Label {
            Layout.fillWidth: true
            text: "📖 " + I18n.t("tutorial_title")
            color: Theme.textPrimary
            font.family: Theme.displayFont
            font.pixelSize: root.compact ? Theme.fontSizeLg : Theme.fontSizeXl
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        ScrollView {
            id: tutorialScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            contentHeight: tutorialColumn.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ColumnLayout {
                id: tutorialColumn
                width: tutorialScroll.availableWidth
                spacing: root.compact ? Theme.space3 : Theme.space4

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: tutorialScroll.availableWidth
                    spacing: Theme.space2

                    Label {
                        Layout.fillWidth: true
                        text: "1️⃣ " + I18n.t("tutorial_add_files_title")
                        color: Theme.accentPrimary
                        font.pixelSize: root.compact ? Theme.fontSizeMd : Theme.fontSizeLg
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: I18n.t("tutorial_add_files_body")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: tutorialScroll.availableWidth
                    spacing: Theme.space2

                    Label {
                        Layout.fillWidth: true
                        text: "2️⃣ " + I18n.t("tutorial_output_title")
                        color: Theme.statusWarning
                        font.pixelSize: root.compact ? Theme.fontSizeMd : Theme.fontSizeLg
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: I18n.t("tutorial_output_body")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: tutorialScroll.availableWidth
                    spacing: Theme.space2

                    Label {
                        Layout.fillWidth: true
                        text: "3️⃣ " + I18n.t("tutorial_format_title")
                        color: Theme.accent
                        font.pixelSize: root.compact ? Theme.fontSizeMd : Theme.fontSizeLg
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: I18n.t("tutorial_format_body")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: tutorialScroll.availableWidth
                    spacing: Theme.space2

                    Label {
                        Layout.fillWidth: true
                        text: "4️⃣ " + I18n.t("tutorial_start_title")
                        color: Theme.statusSuccess
                        font.pixelSize: root.compact ? Theme.fontSizeMd : Theme.fontSizeLg
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: I18n.t("tutorial_start_body")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }
            }
        }

        PrimaryButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Math.min(200, parent.width)
            Layout.preferredHeight: 44
            text: I18n.t("got_it")
            font.pixelSize: Theme.fontSizeMd
            font.bold: true
            onClicked: root.close()
        }
    }
}
