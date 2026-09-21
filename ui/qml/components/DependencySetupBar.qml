import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    objectName: "dependencySetupBar"
    readonly property var job: backend ? backend.whisperSetup : null
    implicitHeight: content.implicitHeight + 16
    color: Theme.panelSecondary

    ColumnLayout {
        id: content
        anchors.fill: parent; anchors.margins: 8; spacing: 6
        RowLayout {
            Layout.fillWidth: true
            BusyIndicator { running: root.job && root.job.busy; visible: running; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
            Label { text: I18n.t("dependencies.title"); color: Theme.textPrimary }
            Label {
                Layout.fillWidth: true; elide: Text.ElideRight
                color: root.job && root.job.error ? Theme.accentWarn : Theme.textSecondary
                text: root.job ? I18n.t("setup." + root.job.stage) : ""
            }
            AppCheckBox {
                text: I18n.t("dependencies.automatic")
                checked: backend && backend.autoDependencySetup
                onClicked: if (backend) backend.autoDependencySetup = checked
            }
            AppButton {
                text: I18n.t("cancel"); visible: root.job && root.job.busy
                onClicked: root.job.cancel()
            }
            AppButton {
                objectName: "retryDependencySetup"
                text: I18n.t("dependencies.retry"); visible: root.job && !root.job.busy
                onClicked: backend.retryDependencySetup()
            }
        }
        ProgressBar {
            Layout.fillWidth: true; visible: root.job && root.job.busy
            indeterminate: true
        }
        Label {
            Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
            text: root.job && root.job.error ? root.job.error : I18n.t("dependencies.hint")
            color: root.job && root.job.error ? Theme.accentWarn : Theme.textMuted
            visible: root.job && (root.job.busy || root.job.error.length > 0 || root.job.stage === "idle")
        }
    }
}
