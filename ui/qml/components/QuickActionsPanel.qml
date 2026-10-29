import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: panel
    property var appRoot
    implicitHeight: content.implicitHeight + 24
    color: Theme.panelBackground
    ColumnLayout {
        id: content
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
        spacing: 8
        Flow {
            Layout.fillWidth: true
            spacing: 8
            AppButton { objectName: "quickAudioAction"; text: I18n.t("quick_audio"); enabled: backend && !backend.isRunning; onClicked: appRoot.quickAction("audio") }
            AppButton { text: I18n.t("quick_compress"); enabled: backend && !backend.isRunning; onClicked: appRoot.quickAction("compress") }
            AppButton { text: I18n.t("quick_format"); enabled: backend && !backend.isRunning; onClicked: appRoot.quickAction("format") }
            AppButton { text: I18n.t("quick_subtitles"); enabled: backend && !backend.isRunning; onClicked: appRoot.quickAction("subtitles") }
            AppButton { objectName: "interfaceModeButton"; text: I18n.t(appRoot.simpleMode ? "advanced_mode" : "simple_mode"); onClicked: appRoot.simpleMode = !appRoot.simpleMode }
        }
        Flow {
            visible: appRoot.simpleMode
            Layout.fillWidth: true
            spacing: 8
            AppComboBox {
                objectName: "simpleFormatCombo"
                width: 110
                model: appRoot.formatOptionsFor(appRoot.simpleMediaType)
                currentIndex: Math.max(0, model.indexOf(appRoot.currentFormatFor(appRoot.simpleMediaType)))
                onActivated: {
                    var patch = {}
                    patch[appRoot.outputFormatKeyFor(appRoot.simpleMediaType)] = currentText
                    appRoot.patchSettings(patch)
                }
                Accessible.name: I18n.t("output_format")
            }
            AppComboBox {
                objectName: "simpleQualityCombo"
                width: 190
                visible: appRoot.simpleMediaType === "audio" || appRoot.simpleMediaType === "video"
                model: [I18n.t("quality_small"), I18n.t("quality_balanced"), I18n.t("quality_high"), I18n.t("quality_custom")]
                currentIndex: appRoot.qualityProfile < 0 ? 3 : appRoot.qualityProfile
                onActivated: if (currentIndex < 3) appRoot.setQualityProfile(currentIndex)
                Accessible.name: I18n.t("quality")
            }
            AppButton { text: I18n.t("output_folder"); enabled: backend && !backend.isRunning; onClicked: backend.ensureOutputDirSelected() }
        }
        Label {
            visible: appRoot.simpleMode
            Layout.fillWidth: true
            text: I18n.t(appRoot.qualityProfile < 0 ? "quality_custom_hint" : ["quality_small_hint", "quality_balanced_hint", "quality_high_hint"][appRoot.qualityProfile])
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.fontMeta
            color: Theme.textSecondary
        }
        Label {
            visible: appRoot.simpleMode
            Layout.fillWidth: true
            text: backend ? backend.outputDir : ""
            elide: Text.ElideMiddle
            color: Theme.textMuted
            font.pixelSize: Theme.fontMeta
        }
    }
}
