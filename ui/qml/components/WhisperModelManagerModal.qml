import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Dialog {
    id: root
    objectName: "whisperModelManager"
    parent: Overlay.overlay
    title: I18n.t("whisper.title")
    modal: true
    padding: 16
    header: RowLayout {
        height: 58
        spacing: 10
        NavigationIcon { Layout.leftMargin: 16; name: "subtitle"; tint: "#007AFF"; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
        Label { Layout.fillWidth: true; Layout.rightMargin: 16; text: root.title; color: Theme.textPrimary; font.pixelSize: Theme.fontHeading; font.weight: Font.DemiBold; elide: Text.ElideRight }
    }
    Overlay.modal: Rectangle { color: Theme.modalScrim }
    width: Math.min(780, parent ? parent.width - 32 : 780)
    height: Math.min(680, parent ? parent.height - 32 : 680)
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0

    property string selectedModel: "base"
    property string selectedDevice: "auto"
    property string selectedEngine: "auto"
    property var modelsList: []
    property var devices: ["auto", "cpu"]
    property string effectiveEngine: ""
    property bool engineInstalled: false
    property string activeDownloadingModel: ""
    property real downloadProgress: 0
    property string downloadFile: ""
    readonly property bool downloading: activeDownloadingModel.length > 0
    signal modelChosen(string name)
    signal deviceChosen(string device)
    signal engineChosen(string engine)

    function refreshModels() {
        if (!backend) return
        effectiveEngine = backend.getWhisperEngine(selectedDevice, selectedEngine)
        engineInstalled = backend.whisperEngineInstalled(effectiveEngine)
        modelsList = backend.getWhisperModels(selectedDevice, selectedEngine)
        devices = backend.getWhisperDevices(selectedEngine)
        var active = ""
        for (var i = 0; i < modelsList.length; i++) {
            if (modelsList[i].state === "downloading") {
                active = modelsList[i].name
                downloadProgress = modelsList[i].progress
            }
        }
        activeDownloadingModel = active
    }

    function chooseModel(name) { root.modelChosen(name) }
    function chooseDevice(device) { root.deviceChosen(device) }
    onOpened: { refreshModels(); backend.whisperSetup.check() }
    onSelectedDeviceChanged: if (visible) refreshModels()
    onSelectedEngineChanged: if (visible) refreshModels()

    Connections {
        target: backend
        function onWhisperModelsChanged() { root.refreshModels() }
        function onWhisperDownloadProgress(name, pct, message) {
            if (name === root.activeDownloadingModel) {
                root.downloadProgress = pct
                root.downloadFile = message
            }
        }
    }

    WhisperSetupDialog {
        id: setupDialog
        selectedModel: root.selectedModel
        selectedEngine: root.effectiveEngine || "whisper"
        selectedDevice: root.selectedDevice
    }

    background: Rectangle {
        color: Theme.panelBackground
        radius: Theme.radiusLg
        border.width: 1
        border.color: Theme.borderMuted
    }

    contentItem: ColumnLayout {
        spacing: 12
        AppButton { text: I18n.t("whisper.setup"); onClicked: setupDialog.open() }
        Label {
            Layout.fillWidth: true
            text: I18n.t("whisper.description")
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.fontSizeSm
        }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            FieldLabel { text: I18n.t("engine") }
            AppComboBox {
                objectName: "whisperEngineCombo"
                model: ["auto", "whisper", "faster-whisper"]
                currentIndex: Math.max(0, model.indexOf(root.selectedEngine))
                enabled: !root.downloading
                onActivated: root.engineChosen(currentText)
            }
            FieldLabel { text: I18n.t("whisper.device") }
            AppComboBox {
                objectName: "whisperDeviceCombo"
                model: root.devices.indexOf(root.selectedDevice) >= 0 ? root.devices : root.devices.concat([root.selectedDevice])
                currentIndex: Math.max(0, model.indexOf(root.selectedDevice))
                enabled: !root.downloading
                onActivated: root.chooseDevice(currentText)
            }
        }
        Label {
            Layout.fillWidth: true
            text: I18n.t("whisper.device_hint")
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.fontMeta
        }
        Label {
            Layout.fillWidth: true
            visible: root.devices.indexOf(root.selectedDevice) < 0 || root.effectiveEngine.length === 0
            text: I18n.t("whisper.device_unavailable")
            color: Theme.accentWarn
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            visible: !root.engineInstalled
            text: I18n.t("whisper.install_hint")
            color: Theme.accentWarn
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.fontMeta
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: I18n.t("whisper.cache") + ": " + root.effectiveEngine
                color: Theme.textSecondary
                font.pixelSize: Theme.fontMeta
            }
            SecondaryButton {
                Layout.fillWidth: false
                iconName: "refresh"
                text: I18n.t("whisper.refresh")
                onClicked: root.refreshModels()
            }
        }
        ColumnLayout {
            visible: root.downloading
            Layout.fillWidth: true
            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: root.activeDownloadingModel + " · " + root.downloadFile
                    color: Theme.textPrimary
                    elide: Text.ElideMiddle
                }
                Label {
                    text: root.downloadProgress >= 0 ? Math.round(root.downloadProgress * 100) + "%" : ""
                    color: Theme.textSecondary
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    objectName: "whisperCancelDownload"
                    text: I18n.t("cancel")
                    onClicked: backend.cancelWhisperDownload()
                }
            }
            ProgressBar {
                objectName: "whisperDownloadProgress"
                Layout.fillWidth: true
                from: 0; to: 1
                value: root.downloadProgress
                indeterminate: root.downloadProgress < 0
            }
        }
        ListView {
            id: modelsView
            objectName: "whisperModelsList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: root.modelsList
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: modelsView.width
                height: cardContent.implicitHeight + 24
                radius: Theme.radiusMd
                color: Theme.panelSecondary
                border.width: 1
                border.color: root.selectedModel === modelData.name ? Theme.accentPrimary : Theme.borderMuted
                ColumnLayout {
                    id: cardContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: modelData.name.toUpperCase()
                            color: Theme.textPrimary
                            font.weight: Font.Bold
                            font.pixelSize: Theme.fontSizeSm
                        }
                        Label {
                            Layout.fillWidth: true
                            text: I18n.t("whisper.state." + modelData.state)
                            color: modelData.downloaded ? Theme.statusSuccess : Theme.textSecondary
                            elide: Text.ElideRight
                            font.pixelSize: Theme.fontMeta
                        }
                        PrimaryButton {
                            Layout.fillWidth: false
                            objectName: "whisperDownload_" + modelData.name
                            visible: !modelData.downloaded
                            iconName: "download"
                            text: I18n.t("whisper.download")
                            enabled: !root.downloading && root.effectiveEngine.length > 0
                            onClicked: backend.downloadWhisperModel(modelData.name, root.selectedDevice, root.selectedEngine)
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            visible: modelData.disk_bytes > 0
                            iconName: "trash"
                            text: I18n.t("whisper.delete")
                            enabled: !root.downloading && !(backend && backend.isRunning)
                            onClicked: {
                                deleteDialog.modelName = modelData.name
                                deleteDialog.open()
                            }
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            objectName: "whisperSelect_" + modelData.name
                            iconName: "check"
                            text: root.selectedModel === modelData.name ? I18n.t("whisper.selected") : I18n.t("whisper.select")
                            enabled: root.selectedModel !== modelData.name
                            onClicked: root.chooseModel(modelData.name)
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "~" + modelData.size_mb + " MB · " + I18n.t("whisper.memory") + ": ~" + modelData.vram_mb + " MB · " + I18n.t("whisper.disk") + ": " + modelData.disk_size_mb + " MB"
                        wrapMode: Text.WordWrap
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontMeta
                    }
                    Label {
                        Layout.fillWidth: true
                        visible: modelData.error.length > 0
                        text: modelData.error
                        wrapMode: Text.WrapAnywhere
                        color: Theme.accentError
                        font.pixelSize: Theme.fontMeta
                    }

                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            SecondaryButton {
                Layout.fillWidth: false
                text: I18n.t("whisper.close")
                onClicked: root.close()
            }
        }
    }
    Dialog {
        id: deleteDialog
        property string modelName: ""
        implicitHeight: 240
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(420, parent ? parent.width - 48 : 420)
        title: I18n.t("whisper.delete") + " " + modelName + "?"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: backend.deleteWhisperModel(modelName, root.selectedDevice, root.selectedEngine)
        contentItem: Label {
            text: I18n.t("whisper.delete_hint")
            wrapMode: Text.WordWrap
        }
    }
}
