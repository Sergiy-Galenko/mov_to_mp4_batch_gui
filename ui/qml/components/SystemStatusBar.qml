import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    objectName: "systemStatusBar"
    property var appRoot
    readonly property var scan: backend ? backend.systemProfile : ({busy: false, result: {}, error: "", stage: "idle", progress: 0})
    readonly property var info: scan.result

    implicitHeight: 30
    implicitWidth: mainRow.implicitWidth + 18
    Layout.preferredHeight: 30
    Layout.preferredWidth: implicitWidth

    radius: Theme.isMac ? 15 : Theme.radiusButton
    color: mouseArea.containsMouse ? Theme.overlayHover : Theme.panelSecondary
    border.width: 1
    border.color: mouseArea.containsMouse ? Theme.borderDefault : Theme.borderMuted

    function openDetails() { details.open() }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.openDetails()

        ToolTip.visible: mouseArea.containsMouse && !details.visible
        ToolTip.delay: 400
        ToolTip.text: I18n.t("system.title") + " — " + I18n.t("system.details")
    }

    RowLayout {
        id: mainRow
        anchors.centerIn: parent
        spacing: 8

        // Busy State
        BusyIndicator {
            running: root.scan.busy
            visible: running
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
        }

        // Error Indicator
        Rectangle {
            visible: !root.scan.busy && !!root.scan.error
            width: 6; height: 6; radius: 3
            color: Theme.statusError
        }

        // CPU / Hardware Icon
        AppIcon {
            visible: !root.scan.busy && !root.scan.error
            name: "cpu"
            Layout.preferredWidth: 14
            Layout.preferredHeight: 14
            iconColor: Theme.accent
        }

        // Hardware Summary Text
        Label {
            font.pixelSize: Theme.fontSizeSm
            font.weight: Font.Medium
            color: root.scan.error ? Theme.statusError : Theme.textPrimary
            elide: Text.ElideRight
            text: root.scan.busy ? I18n.t("setup." + root.scan.stage) + " · " + root.scan.progress + "%"
                : root.scan.error ? I18n.t("system.failed")
                : root.info.os ? (root.info.cpu ? root.info.cpu : root.info.os) + (root.info.ram_gib ? " · " + root.info.ram_gib + " GB RAM" : "")
                : I18n.t("system.title")
        }

        // Auto-tune status badge
        Rectangle {
            visible: !root.scan.busy && !root.scan.error && (!!root.info.os) && (!root.appRoot || root.appRoot.width > 860)
            radius: 6
            Layout.preferredHeight: 18
            implicitHeight: 18
            implicitWidth: badgeRow.implicitWidth + 10
            color: backend && backend.autoTuneEnabled ? Theme.accentSoft : Theme.subtleFill
            border.width: 1
            border.color: backend && backend.autoTuneEnabled ? Theme.borderDefault : Theme.borderMuted

            RowLayout {
                id: badgeRow
                anchors.centerIn: parent
                spacing: 4
                Rectangle {
                    width: 5; height: 5; radius: 2.5
                    color: backend && backend.autoTunePending ? Theme.statusWarning
                         : backend && backend.autoTuneEnabled ? Theme.statusSuccess
                         : Theme.textDisabled
                }
                Label {
                    text: I18n.t(backend && backend.autoTunePending ? "system.pending" : backend && backend.autoTuneEnabled ? "system.automatic" : "system.manual")
                    color: Theme.textSecondary
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
            }
        }

        // Details button
        AppButton {
            objectName: "systemDetailsButton"
            visible: !root.appRoot || root.appRoot.width > 920
            text: I18n.t("system.details")
            Layout.preferredHeight: 22
            font.pixelSize: 11
            onClicked: root.openDetails()
        }
    }

    Dialog {
        id: details
        objectName: "systemProfileDialog"
        parent: Overlay.overlay
        title: I18n.t("system.title")
        modal: true
        width: Math.min(620, parent ? parent.width - 32 : 620)
        height: Math.min(580, parent ? parent.height - 32 : 580)
        x: parent ? (parent.width - width) / 2 : 0
        y: parent ? (parent.height - height) / 2 : 0
        standardButtons: Dialog.Close
        background: Rectangle {
            color: Theme.panelBackground
            radius: Theme.radiusLg
            border.width: 1
            border.color: Theme.borderMuted
        }
        contentItem: ScrollView {
            clip: true
            ColumnLayout {
                width: details.availableWidth
                spacing: 12
                ProgressBar {
                    Layout.fillWidth: true
                    visible: root.scan.busy
                    from: 0
                    to: 100
                    value: root.scan.progress
                }
                Label {
                    Layout.fillWidth: true
                    text: I18n.t("setup." + root.scan.stage)
                    color: Theme.textPrimary
                    visible: root.scan.busy
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: specsColumn.implicitHeight + 20
                    radius: Theme.radiusMd
                    color: Theme.panelSecondary
                    border.width: 1
                    border.color: Theme.borderMuted
                    ColumnLayout {
                        id: specsColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                            text: root.info.os ? root.info.os + " " + root.info.version + " · " + root.info.architecture
                                + "\nCPU: " + root.info.cpu + " (" + root.info.physical_cpus + " / " + root.info.logical_cpus + ")"
                                + "\nRAM: " + root.info.ram_gib + " GB · " + I18n.t("system.available") + ": " + root.info.available_gib + " GB"
                                + "\nGPU: " + (root.info.gpu && root.info.gpu.length ? root.info.gpu.join(", ") : I18n.t("system.unknown"))
                                + "\n" + I18n.t("system.encoders") + ": " + (root.info.encoders && root.info.encoders.length ? root.info.encoders.join(", ") : root.info.encoding_checked ? "CPU" : I18n.t("whisper.unavailable")) : ""
                        }
                    }
                }
                AppCheckBox {
                    text: I18n.t("system.auto_tune")
                    checked: backend ? backend.autoTuneEnabled : false
                    enabled: !!backend && !backend.isRunning
                    onClicked: backend.autoTuneEnabled = checked
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: I18n.t("system.explanation")
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSmall
                }
                RowLayout {
                    spacing: 8
                    Label { text: I18n.t("system.parallel"); color: Theme.textPrimary }
                    AppSpinBox {
                        objectName: "systemConcurrency"
                        from: 1
                        to: 16
                        value: backend ? Math.max(1, backend.concurrencyLimit) : 1
                        enabled: !!backend && !backend.isRunning && !backend.autoTuneEnabled
                        onValueModified: backend.concurrencyLimit = value
                    }
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.textSecondary
                    text: root.info.warnings ? root.info.warnings.join("\n") : ""
                    visible: text.length > 0
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: Theme.statusError
                    text: root.scan.error
                    visible: text.length > 0
                }
                RowLayout {
                    spacing: 8
                    AppButton {
                        text: I18n.t("system.rescan")
                        enabled: !!backend && !root.scan.busy && !backend.isRunning
                        onClicked: backend.startSystemScan()
                    }
                    AppButton {
                        text: I18n.t("cancel")
                        visible: root.scan.busy
                        onClicked: root.scan.cancel()
                    }
                }
            }
        }
    }
}
