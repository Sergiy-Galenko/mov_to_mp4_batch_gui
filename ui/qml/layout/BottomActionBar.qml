import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var appRoot
    readonly property int outputBlockWidth: width > 960 ? 264 : 176
    implicitHeight: 76
    color: Theme.panelBackground
    border.width: 1
    border.color: Theme.borderMuted

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space4
        anchors.rightMargin: Theme.space4
        spacing: Theme.space4

        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.minimumWidth: 220
            spacing: 5
            RowLayout {
                Layout.fillWidth: true
                Label { text: backend ? backend.totalProgressText : "--"; color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; font.weight: Font.DemiBold }
                Item { Layout.fillWidth: true }
                Label { text: I18n.t("eta") + ": " + (backend ? backend.sessionEtaText : "--:--"); color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta }
                Label { visible: root.width > 980; text: backend ? backend.sessionAvgSpeedText : "--"; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta }
            }
            AppProgressBar { Layout.fillWidth: true; value: backend ? backend.totalProgress : 0 }
        }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 38; color: Theme.borderMuted }

        RowLayout {
            Layout.preferredWidth: root.outputBlockWidth
            Layout.minimumWidth: root.outputBlockWidth
            Layout.maximumWidth: root.outputBlockWidth
            spacing: Theme.space2
            AppIconButton { iconName: "folder"; accessibleLabel: I18n.t("choose_output_folder"); onClicked: backend && backend.pickOutputDir() }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Label { text: I18n.t("output_folder"); color: Theme.textMuted; font.pixelSize: 11 }
                Label {
                    Layout.fillWidth: true
                    text: backend && backend.outputDirConfigured ? backend.outputDir : I18n.t("output_folder_required")
                    color: backend && backend.outputDirConfigured ? Theme.textSecondary : Theme.warning
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideMiddle
                }
            }
        }

        AppIconButton {
            visible: root.width > 760
            iconName: backend && backend.isPaused ? "play" : "pause"
            accessibleLabel: backend && backend.isPaused ? I18n.t("resume") : I18n.t("pause")
            enabled: backend && backend.isRunning
            onClicked: backend && (backend.isPaused ? backend.resumeConversion() : backend.pauseConversion())
        }

        AppIconButton {
            visible: root.width > 840
            iconName: "stop"
            accessibleLabel: I18n.t("stop")
            enabled: backend && backend.isRunning
            onClicked: backend && backend.stopConversion()
        }

        Button {
            id: convertButton
            Layout.preferredWidth: root.width > 900 ? 138 : 112
            implicitHeight: 36
            enabled: backend ? backend.queueCount > 0 && !backend.isRunning && appRoot && appRoot.formValid : false
            hoverEnabled: true
            Accessible.name: I18n.t("convert_all")
            onClicked: appRoot && appRoot.startIfValid()
            background: Rectangle {
                radius: Theme.radiusSm
                color: !convertButton.enabled ? Theme.disabledBg : convertButton.down ? Theme.accentPressed : convertButton.hovered ? Theme.accentHover : Theme.accentPrimary
                border.width: convertButton.activeFocus ? 2 : 1
                border.color: convertButton.activeFocus ? Theme.focusRing : Theme.accentPrimary
            }
            contentItem: RowLayout {
                spacing: 6
                AppIcon { Layout.preferredWidth: 16; Layout.preferredHeight: 16; Layout.leftMargin: 10; name: "play"; iconColor: Theme.textOnAccent }
                Label { Layout.fillWidth: true; text: I18n.t("convert_all"); color: Theme.textOnAccent; font.pixelSize: Theme.fontSizeSm; font.weight: Font.DemiBold; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
            }
        }
    }
}
