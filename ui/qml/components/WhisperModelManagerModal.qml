import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Dialog {
    id: root
    title: "Керування моделями Whisper (Субтитри)"
    modal: true
    width: 620
    height: 520
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)

    background: Rectangle {
        color: Theme.panelBackground
        radius: Theme.radiusLg
        border.width: 1
        border.color: Theme.borderMuted
    }

    property var modelsList: []
    property string activeDownloadingModel: ""
    property real downloadProgress: 0.0
    property string downloadStatusText: ""

    function refreshModels() {
        if (backend && backend.getWhisperModels) {
            root.modelsList = backend.getWhisperModels()
        }
    }

    onOpened: refreshModels()

    Connections {
        target: backend
        function onWhisperModelsChanged() { root.refreshModels() }
        function onWhisperDownloadProgress(name, pct, msg) {
            root.activeDownloadingModel = pct < 1.0 && pct > 0.0 ? name : ""
            root.downloadProgress = pct
            root.downloadStatusText = msg
            if (pct >= 1.0) root.refreshModels()
        }
    }

    contentItem: ColumnLayout {
        spacing: 12

        // Header description and device selector
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: "Моделі Whisper для автоматичної генерації субтитрів та транскрипції."
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSm
                wrapMode: Text.WordWrap
            }
            AppIconButton {
                iconName: "refresh"
                accessibleLabel: "Оновити"
                onClicked: root.refreshModels()
            }
        }

        // Hardware Acceleration selector
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                text: "Прискорювач обчислень:"
                color: Theme.textMuted
                font.pixelSize: Theme.fontSizeSm
            }
            AppComboBox {
                id: deviceCombo
                Layout.preferredWidth: 180
                model: backend && backend.getWhisperDevices ? backend.getWhisperDevices() : ["auto", "cpu"]
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.borderMuted
        }

        // Download progress bar if downloading
        ColumnLayout {
            visible: root.activeDownloadingModel.length > 0
            Layout.fillWidth: true
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: root.downloadStatusText
                    color: Theme.accentPrimary
                    font.pixelSize: Theme.fontMeta
                    font.weight: Font.DemiBold
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: Math.round(root.downloadProgress * 100) + "%"
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontMeta
                    font.family: Theme.monoFont
                }
            }

            ProgressBar {
                Layout.fillWidth: true
                value: root.downloadProgress
                from: 0.0
                to: 1.0
            }
        }

        // Models List
        ListView {
            id: modelsListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: root.modelsList

            delegate: Rectangle {
                width: modelsListView.width
                height: 64
                radius: Theme.radiusMd
                color: Theme.panelSecondary
                border.width: 1
                border.color: modelData.downloaded ? Theme.accentPrimary : Theme.borderMuted

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            spacing: 8
                            Label {
                                text: modelData.name.toUpperCase()
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeSm
                                font.weight: Font.Bold
                            }
                            Rectangle {
                                radius: 3
                                height: 16
                                width: statusText.implicitWidth + 8
                                color: modelData.downloaded ? "#22C55E22" : "#6B728022"
                                border.width: 1
                                border.color: modelData.downloaded ? "#22C55E" : "#6B7280"
                                Text {
                                    id: statusText
                                    anchors.centerIn: parent
                                    text: modelData.downloaded ? "Завантажено (" + modelData.disk_size_mb + " MB)" : "Не завантажено"
                                    color: modelData.downloaded ? "#22C55E" : Theme.textMuted
                                    font.pixelSize: 10
                                    font.weight: Font.Medium
                                }
                            }
                        }

                        Label {
                            text: "Розмір: ~" + modelData.size_mb + " MB  ·  Швидкість: " + modelData.speed + "  ·  VRAM: ~" + modelData.vram_mb + " MB"
                            color: Theme.textMuted
                            font.pixelSize: Theme.fontMeta
                        }
                    }

                    // Action buttons
                    RowLayout {
                        spacing: 6

                        PrimaryButton {
                            visible: !modelData.downloaded
                            text: "Завантажити"
                            enabled: root.activeDownloadingModel.length === 0
                            implicitHeight: 30
                            onClicked: {
                                if (backend && backend.downloadWhisperModel) {
                                    backend.downloadWhisperModel(modelData.name)
                                }
                            }
                        }

                        SecondaryButton {
                            visible: modelData.downloaded
                            text: "Видалити"
                            implicitHeight: 30
                            onClicked: {
                                if (backend && backend.deleteWhisperModel) {
                                    backend.deleteWhisperModel(modelData.name)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Dialog buttons
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            SecondaryButton {
                text: "Закрити"
                onClicked: root.close()
            }
        }
    }
}

