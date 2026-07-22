import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var appRoot
    implicitWidth: 328
    color: Theme.panelBackground
    border.width: 1
    border.color: Theme.borderMuted
    clip: true

    readonly property bool batchSelection: appRoot && appRoot.selectedPaths.length > 1
    readonly property bool hasSelection: appRoot && appRoot.selectedPath.length > 0

    ScrollView {
        anchors.fill: parent
        anchors.margins: Theme.space3
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.space3

            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: root.batchSelection ? I18n.t("selected") + " · " + appRoot.selectedPaths.length : I18n.t("selected_file")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeMd
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                AppIconButton {
                    iconName: "close"
                    accessibleLabel: I18n.t("cancel")
                    onClicked: appRoot.clearQueueSelection()
                }
            }

            Rectangle {
                visible: !root.batchSelection
                Layout.fillWidth: true
                Layout.preferredHeight: 154
                radius: Theme.radiusMd
                color: Theme.panelSecondary
                border.width: 1
                border.color: Theme.borderMuted
                clip: true

                Image {
                    anchors.fill: parent
                    anchors.margins: 8
                    source: appRoot ? appRoot.selectedThumbnailSource : ""
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    visible: source.toString().length > 0
                }

                AppIcon {
                    anchors.centerIn: parent
                    visible: !(appRoot && appRoot.selectedThumbnailSource.length > 0)
                    name: "file"
                    iconColor: Theme.textMuted
                    width: 36
                    height: 36
                }
            }

            Label {
                visible: !root.batchSelection
                Layout.fillWidth: true
                text: appRoot ? (appRoot.selectedName || appRoot.selectedPath) : ""
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeMd
                font.weight: Font.DemiBold
                maximumLineCount: 2
                elide: Text.ElideMiddle
                wrapMode: Text.Wrap
            }

            Label {
                visible: !root.batchSelection
                Layout.fillWidth: true
                text: appRoot ? appRoot.selectedPath : ""
                color: Theme.textMuted
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                elide: Text.ElideMiddle
            }

            GridLayout {
                visible: !root.batchSelection
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Theme.space2
                rowSpacing: 7

                Label { text: I18n.t("media_type"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; text: appRoot ? String(appRoot.selectedMediaType || "—").toUpperCase() : "—"; color: Theme.textSecondary; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("resolution"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; text: backend ? backend.infoRes || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("queue_show_duration"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; text: backend ? backend.infoDuration || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("codec"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; text: backend ? backend.infoCodec || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("source_size"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; text: backend ? backend.infoSize || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
            }

            Label { visible: !root.batchSelection; text: I18n.t("output_format"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }

            AppComboBox {
                id: formatCombo
                visible: !root.batchSelection
                Layout.fillWidth: true
                model: appRoot ? appRoot.formatOptionsFor(appRoot.selectedMediaType) : []
                currentIndex: appRoot ? Math.max(0, find(appRoot.selectedPreviewFormat)) : 0
                onActivated: if (appRoot) appRoot.selectedPreviewFormat = currentText
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderMuted }

            Label {
                visible: root.batchSelection
                Layout.fillWidth: true
                text: root.batchSelection ? appRoot.selectedPaths.length + " " + I18n.t("files") + " " + I18n.t("selected").toLowerCase() : ""
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSm
                wrapMode: Text.WordWrap
            }

            Button {
                visible: root.batchSelection
                Layout.fillWidth: true
                implicitHeight: Theme.buttonHeight
                enabled: root.batchSelection
                text: I18n.t("batch_override")
                onClicked: appRoot && appRoot.openSidebarSection(5, "selected_override", appRoot.navIndexFor(5, "selected_override"))
            }

            Button {
                visible: root.batchSelection
                Layout.fillWidth: true
                implicitHeight: Theme.buttonHeight
                enabled: root.batchSelection && backend && !backend.isRunning
                text: I18n.t("convert_selected")
                onClicked: appRoot && appRoot.convertSelectedPaths()
            }

            Button {
                visible: root.batchSelection
                Layout.fillWidth: true
                implicitHeight: Theme.buttonHeight
                enabled: root.batchSelection
                text: I18n.t("batch_remove")
                onClicked: appRoot && appRoot.removeSelectedPaths()
            }

            Button {
                visible: !root.batchSelection
                Layout.fillWidth: true
                implicitHeight: Theme.buttonHeight
                enabled: root.hasSelection && backend && !backend.isRunning
                text: I18n.t("convert_this_file")
                onClicked: appRoot && appRoot.convertSelectedFormat(formatCombo.currentText)
            }

            Button {
                visible: !root.batchSelection
                Layout.fillWidth: true
                implicitHeight: Theme.buttonHeight
                enabled: root.hasSelection
                text: I18n.t("change")
                onClicked: appRoot && appRoot.openSelectedSettings()
            }
        }
    }
}
