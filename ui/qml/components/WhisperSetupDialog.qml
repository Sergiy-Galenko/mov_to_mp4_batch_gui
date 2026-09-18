import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Dialog {
    id: root
    objectName: "whisperSetupDialog"
    parent: Overlay.overlay
    title: I18n.t("whisper.setup")
    modal: true
    property string selectedModel: "tiny"
    property string selectedEngine: "whisper"
    property string selectedDevice: "auto"
    property string samplePath: ""
    readonly property var job: backend ? backend.whisperSetup : ({busy: false, diagnostics: {}, result: {}, error: "", stage: "idle", progress: 0})
    readonly property var engineInfo: job.diagnostics.engines ? job.diagnostics.engines[selectedEngine] : ({})
    width: Math.min(660, parent ? parent.width - 32 : 660)
    height: Math.min(640, parent ? parent.height - 32 : 640)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    standardButtons: Dialog.Close
    onOpened: if (!job.busy) job.check()
    background: Rectangle { color: Theme.panelBackground; radius: Theme.radiusLg; border.color: Theme.borderMuted }
    contentItem: ScrollView {
        clip: true
        ColumnLayout {
            width: root.availableWidth
            spacing: 12
            Label { Layout.fillWidth: true; text: root.selectedEngine + " · " + root.selectedModel + " · " + root.selectedDevice.toUpperCase(); color: Theme.textPrimary }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: I18n.t("whisper.setup_hint"); color: Theme.textSecondary }
            RowLayout {
                AppButton { text: I18n.t("whisper.install"); enabled: !root.job.busy; onClicked: root.job.install(root.selectedEngine, pythonPath.text) }
                AppButton { text: I18n.t("whisper.check"); enabled: !root.job.busy; onClicked: root.job.check() }
            }
            AppTextField { id: pythonPath; Layout.fillWidth: true; placeholderText: I18n.t("whisper.python_path"); enabled: !root.job.busy }
            Label {
                Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.textPrimary
                text: root.engineInfo && root.engineInfo.installed ? I18n.t("whisper.installed") + " · " + root.engineInfo.version : I18n.t("whisper.not_installed")
            }
            RowLayout {
                Repeater {
                    model: ["cpu", "mps", "cuda"]
                    Label {
                        required property string modelData
                        color: Theme.textPrimary
                        text: modelData.toUpperCase() + ": " + I18n.t(root.engineInfo && root.engineInfo.devices && root.engineInfo.devices.indexOf(modelData) >= 0 ? "whisper.available" : "whisper.unavailable")
                    }
                }
            }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.textSecondary; text: root.engineInfo && root.engineInfo.errors ? root.engineInfo.errors.join("\n") : ""; visible: text.length > 0 }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: I18n.t("whisper.test_hint"); color: Theme.textSecondary }
            RowLayout {
                AppButton {
                    text: I18n.t("whisper.sample")
                    enabled: !root.job.busy
                    onClicked: { var path = backend.pickWhisperTestMedia(); if (path) root.samplePath = path }
                }
                Label { Layout.fillWidth: true; elide: Text.ElideMiddle; text: root.samplePath; color: Theme.textSecondary }
            }
            AppButton {
                objectName: "whisperTestButton"
                text: I18n.t("whisper.test")
                enabled: !root.job.busy && root.samplePath.length > 0 && !!root.engineInfo && !!root.engineInfo.installed
                onClicked: root.job.test(root.samplePath, root.selectedModel, root.selectedEngine, root.selectedDevice, backend.ffmpegPath)
            }
            ProgressBar { Layout.fillWidth: true; visible: root.job.busy; indeterminate: root.job.stage === "installing" || root.job.stage === "recognizing"; from: 0; to: 100; value: root.job.progress }
            Label { Layout.fillWidth: true; text: I18n.t("setup." + root.job.stage); color: Theme.textPrimary }
            AppButton { text: I18n.t("cancel"); visible: root.job.busy; onClicked: root.job.cancel() }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.job.error; visible: text.length > 0; color: Theme.accentWarn }
            Label {
                Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.textPrimary
                text: root.job.result.device ? root.job.result.device.toUpperCase() + " · " + root.job.result.seconds + " s\n"
                    + (root.job.result.text || I18n.t("whisper.no_speech")) : ""
            }
        }
    }
}
