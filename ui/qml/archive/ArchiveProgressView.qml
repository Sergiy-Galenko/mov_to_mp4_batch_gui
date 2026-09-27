import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var archiveBackend
    property string title: I18n.t("archive.processing")

    color: Theme.panelBackground
    radius: Theme.radiusMd
    border.width: 1
    border.color: Theme.borderMuted
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space4
        spacing: Theme.space3

        RowLayout {
            Layout.fillWidth: true
            AppIcon {
                name: "archive"
                implicitWidth: 20
                implicitHeight: 20
                iconColor: Theme.accent
            }
            Label {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Theme.fontSizeLg
                font.weight: Font.DemiBold
                color: Theme.textPrimary
            }
            Label {
                text: (archiveBackend ? archiveBackend.progress : 0) + "%"
                font.pixelSize: Theme.fontSizeLg
                font.weight: Font.Bold
                font.family: Theme.monoFont
                color: Theme.accent
            }
        }

        // Progress bar
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 8
            radius: 4
            color: Theme.panelSecondary
            clip: true

            Rectangle {
                width: parent.width * Math.min(1.0, Math.max(0.0, (archiveBackend ? archiveBackend.progress : 0) / 100.0))
                height: parent.height
                radius: 4
                color: Theme.accent

                Behavior on width {
                    NumberAnimation { duration: 120 }
                }
            }
        }

        // Statistics Grid
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: Theme.space3
            rowSpacing: Theme.space2

            Label {
                text: I18n.t("archive.files") + ":"
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSm
            }
            Label {
                Layout.fillWidth: true
                text: (archiveBackend ? archiveBackend.filesDone : 0) + " / " + (archiveBackend ? archiveBackend.filesTotal : 0)
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeSm
                font.family: Theme.monoFont
            }

            Label {
                text: I18n.t("archive.processed") + ":"
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSm
            }
            Label {
                Layout.fillWidth: true
                text: (archiveBackend ? archiveBackend.bytesDoneText : "0 B") + " / " + (archiveBackend ? archiveBackend.bytesTotalText : "0 B")
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeSm
                font.family: Theme.monoFont
            }

            Label {
                text: I18n.t("archive.elapsed") + ":"
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSm
            }
            Label {
                Layout.fillWidth: true
                text: archiveBackend ? archiveBackend.elapsedText : "00:00"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeSm
                font.family: Theme.monoFont
            }
        }

        // Current file name
        Label {
            Layout.fillWidth: true
            text: archiveBackend ? archiveBackend.currentFile : ""
            color: Theme.textMuted
            font.pixelSize: Theme.fontSizeXs
            elide: Text.ElideMiddle
        }

        Item { Layout.fillHeight: true }

        // Cancel button
        AppButton {
            Layout.fillWidth: true
            text: I18n.t("cancel")
            implicitHeight: 34
            onClicked: {
                if (archiveBackend) {
                    archiveBackend.cancel()
                }
            }
        }
    }
}
