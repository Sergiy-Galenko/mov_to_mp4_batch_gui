import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ToolbarIconButton {
    id: root
    objectName: "dependencySetupButton"
    readonly property var job: backend ? backend.whisperSetup : null
    readonly property bool busy: !!job && job.busy
    readonly property bool failed: !!job && job.error.length > 0 && job.stage !== "cancelled"
    readonly property string stage: job ? job.stage : "idle"
    readonly property string statusText: I18n.t("setup." + stage)
    readonly property color statusColor: failed ? Theme.statusError
        : busy ? Theme.accent : stage === "ready" ? Theme.statusSuccess : Theme.textMuted

    iconName: "download"
    highlighted: details.visible
    prominent: busy || failed
    accessibleLabel: I18n.t("dependencies.title") + " — " + statusText
    ToolTip.visible: hovered && !details.visible
    onClicked: details.visible ? details.close() : details.open()

    Rectangle {
        objectName: "dependencyStatusIndicator"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 5
        width: 9
        height: 9
        radius: 5
        visible: root.busy || root.failed || root.stage === "ready"
        color: root.statusColor
        border.width: 1
        border.color: Theme.panelBackground
    }

    Popup {
        id: details
        objectName: "dependencySetupPopup"
        parent: root
        modal: false
        dim: false
        focus: true
        padding: 16
        margins: 12
        width: Math.min(400, Overlay.overlay ? Overlay.overlay.width - 24 : 400)
        height: Math.min(content.implicitHeight + topPadding + bottomPadding,
                         Overlay.overlay ? Overlay.overlay.height - 24 : 440)
        // Follow the toolbar button as layouts move it; popup margins keep the
        // card inside the window when there is less room on either side.
        x: root.width - width
        y: root.height + 10
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.panelBackground
            radius: Theme.radiusLg
            border.width: 1
            border.color: Theme.borderDefault
        }

        contentItem: ColumnLayout {
            id: content
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Label {
                    Layout.fillWidth: true
                    text: I18n.t("dependencies.title")
                    font.family: Theme.bodyFont
                    font.pixelSize: Theme.fontTitle
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                    wrapMode: Text.WordWrap
                }
                AppIconButton {
                    objectName: "closeDependencySetup"
                    iconName: "close"
                    accessibleLabel: I18n.t("close")
                    onClicked: details.close()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: statusContent.implicitHeight + 24
                color: Theme.panelSecondary
                radius: Theme.radiusMd

                ColumnLayout {
                    id: statusContent
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        BusyIndicator {
                            running: root.busy && details.visible
                            visible: root.busy
                            Layout.preferredWidth: 22
                            Layout.preferredHeight: 22
                        }
                        AppIcon {
                            visible: !root.busy
                            name: root.stage === "ready" ? "check" : root.failed ? "info" : "download"
                            iconColor: root.statusColor
                            Layout.preferredWidth: 20
                            Layout.preferredHeight: 20
                        }
                        Label {
                            objectName: "dependencySetupStatus"
                            Layout.fillWidth: true
                            text: root.statusText
                            font.pixelSize: Theme.fontBody
                            color: root.failed ? Theme.statusError : Theme.textPrimary
                            wrapMode: Text.WordWrap
                        }
                    }
                    ProgressBar {
                        objectName: "dependencySetupProgress"
                        Layout.fillWidth: true
                        visible: root.busy
                        indeterminate: root.busy && details.visible
                        palette.highlight: Theme.accent
                    }
                }
            }

            ScrollView {
                id: messageScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                implicitHeight: Math.min(144, message.implicitHeight)
                visible: root.failed || root.stage !== "ready"
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                Label {
                    id: message
                    objectName: "dependencySetupMessage"
                    width: messageScroll.availableWidth
                    text: root.failed ? root.job.error : I18n.t("dependencies.hint")
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    font.pixelSize: Theme.fontSmall
                    color: root.failed ? Theme.statusError : Theme.textSecondary
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 1
                color: Theme.borderMuted
            }

            AppCheckBox {
                objectName: "automaticDependencySetup"
                Layout.fillWidth: true
                text: I18n.t("dependencies.automatic")
                checked: !!backend && backend.autoDependencySetup
                enabled: !!backend
                onClicked: backend.autoDependencySetup = checked
            }

            AppButton {
                objectName: "cancelDependencySetup"
                Layout.fillWidth: true
                text: I18n.t("cancel")
                visible: root.busy
                onClicked: root.job.cancel()
            }
            AppButton {
                objectName: "retryDependencySetup"
                Layout.fillWidth: true
                text: I18n.t("dependencies.retry")
                iconName: "refresh"
                variant: "primary"
                visible: !root.busy
                enabled: !!root.job
                onClicked: backend.retryDependencySetup()
            }
        }
    }
}
