import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var archiveBackend
    property var resultData: archiveBackend ? archiveBackend.lastResult : ({})
    property bool isExtract: false
    signal doneClicked()

    color: Theme.panelBackground
    radius: Theme.radiusMd
    border.width: 1
    border.color: Theme.borderMuted
    clip: true

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: scroll.availableWidth
            spacing: Theme.space3

            // Success Header
            Rectangle {
                Layout.fillWidth: true
                Layout.margins: Theme.space3
                implicitHeight: 64
                radius: Theme.radiusSm
                color: Qt.rgba(0.2, 0.78, 0.35, 0.15)
                border.width: 1
                border.color: Qt.rgba(0.2, 0.78, 0.35, 0.4)

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.space3
                    spacing: Theme.space3

                    AppIcon {
                        name: "check"
                        implicitWidth: 24
                        implicitHeight: 24
                        iconColor: "#34C759"
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label {
                            text: root.isExtract ? I18n.t("archive.extracted_success") : I18n.t("archive.created_success")
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.Bold
                            color: Theme.textPrimary
                        }
                        Label {
                            text: root.resultData ? (root.resultData.elapsedFormatted || "") : ""
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textSecondary
                        }
                    }
                }
            }

            // Compression Comparison Card (Only for Compress mode)
            Rectangle {
                visible: !root.isExtract && !!root.resultData && !!root.resultData.originalSize
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space3
                Layout.rightMargin: Theme.space3
                implicitHeight: compGrid.implicitHeight + Theme.space4 * 2
                radius: Theme.radiusSm
                color: Theme.panelSecondary
                border.width: 1
                border.color: Theme.borderMuted

                GridLayout {
                    id: compGrid
                    anchors.fill: parent
                    anchors.margins: Theme.space4
                    columns: 3
                    columnSpacing: Theme.space2

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Label {
                            text: I18n.t("archive.before")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeXs
                        }
                        Label {
                            text: root.resultData ? (root.resultData.originalSizeFormatted || "") : ""
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.DemiBold
                            font.family: Theme.monoFont
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Label {
                            text: I18n.t("archive.after")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeXs
                        }
                        Label {
                            text: root.resultData ? (root.resultData.archiveSizeFormatted || "") : ""
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.DemiBold
                            font.family: Theme.monoFont
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Label {
                            text: root.resultData && root.resultData.isLarger ? I18n.t("archive.difference") : I18n.t("archive.saved")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeXs
                        }
                        Label {
                            text: {
                                if (!root.resultData) return ""
                                if (root.resultData.isLarger) {
                                    return "+" + Math.abs(root.resultData.savedPercent) + "%"
                                }
                                return root.resultData.savedPercent + "%"
                            }
                            color: root.resultData && root.resultData.isLarger ? Theme.warning : "#34C759"
                            font.pixelSize: Theme.fontSizeMd
                            font.weight: Font.Bold
                            font.family: Theme.monoFont
                        }
                    }
                }
            }

            // Note if size increased
            Label {
                visible: !root.isExtract && !!root.resultData && !!root.resultData.isLarger
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space3
                Layout.rightMargin: Theme.space3
                text: I18n.t("archive.larger_notice")
                color: Theme.warning
                font.pixelSize: Theme.fontSizeXs
                wrapMode: Text.Wrap
            }

            // Output path card
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.space3
                Layout.rightMargin: Theme.space3
                implicitHeight: pathCol.implicitHeight + Theme.space3 * 2
                radius: Theme.radiusSm
                color: Theme.panelSecondary
                border.width: 1
                border.color: Theme.borderMuted

                ColumnLayout {
                    id: pathCol
                    anchors.fill: parent
                    anchors.margins: Theme.space3
                    spacing: Theme.space1

                    Label {
                        text: I18n.t("archive.output_location")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeXs
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.resultData ? (root.resultData.outputPath || root.resultData.destination || "") : ""
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeSm
                        font.family: Theme.monoFont
                        elide: Text.ElideMiddle
                    }
                }
            }

            // Action Buttons
            ColumnLayout {
                Layout.fillWidth: true
                Layout.margins: Theme.space3
                spacing: Theme.space2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.open_folder")
                        implicitHeight: 34
                        onClicked: {
                            var p = root.resultData ? (root.resultData.outputPath || root.resultData.destination || "") : ""
                            if (archiveBackend && p) {
                                archiveBackend.openInFileManager(p)
                            }
                        }
                    }

                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.copy_path")
                        implicitHeight: 34
                        onClicked: {
                            var p = root.resultData ? (root.resultData.outputPath || root.resultData.destination || "") : ""
                            if (archiveBackend && p) {
                                archiveBackend.copyToClipboard(p)
                            }
                        }
                    }
                }

                PrimaryButton {
                    Layout.fillWidth: true
                    text: I18n.t("archive.done")
                    implicitHeight: 36
                    onClicked: root.doneClicked()
                }
            }
        }
    }
}
