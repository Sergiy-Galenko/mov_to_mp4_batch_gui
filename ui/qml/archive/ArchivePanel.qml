import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var appRoot: null
    property var archiveBackend: (typeof backend !== "undefined" && backend) ? backend.archive : null

    property string activeTab: "compress" // "compress" or "extract"
    property bool hasResult: false
    property bool lastResultIsExtract: false
    property string errorMessage: ""

    implicitWidth: 360
    color: Theme.panelBackground
    clip: true

    function openForArchive(path) {
        activeTab = "extract"
        hasResult = false
        errorMessage = ""
        if (extractView) {
            extractView.setArchive(path)
        }
    }

    function openForSources(sources) {
        activeTab = "compress"
        hasResult = false
        errorMessage = ""
        if (compressView) {
            compressView.addPaths(sources)
        }
    }

    Shortcut {
        sequence: StandardKey.Open
        onActivated: {
            if (root.activeTab === "compress" && compressView) {
                compressView.openFileDialog()
            } else if (extractView) {
                extractView.openFileDialog()
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (archiveBackend && archiveBackend.isBusy) {
                archiveBackend.cancelCurrentOperation()
            } else if (root.hasResult) {
                root.hasResult = false
            }
        }
    }

    Connections {
        target: archiveBackend
        function onArchiveFinished(success, msg, res) {
            if (success) {
                root.hasResult = true
                root.lastResultIsExtract = false
                root.errorMessage = ""
            } else {
                root.errorMessage = msg || "Archive creation failed"
            }
        }
        function onExtractFinished(success, msg, res) {
            if (success) {
                root.hasResult = true
                root.lastResultIsExtract = true
                root.errorMessage = ""
            } else {
                root.errorMessage = msg || "Extraction failed"
            }
        }
        function onOperationError(title, msg, details) {
            root.errorMessage = msg || title
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space3
        spacing: Theme.space3

        // -------------------------------------------------------------
        // Header with Mode Switcher (Compress | Extract)
        // -------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space2

            AppIcon {
                name: "archive"
                implicitWidth: 20
                implicitHeight: 20
                iconColor: Theme.accent
            }

            Label {
                text: I18n.t("archive.title")
                font.pixelSize: Theme.fontSizeLg
                font.weight: Font.Bold
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            RowLayout {
                spacing: 2
                AppButton {
                    text: I18n.t("archive.compress")
                    implicitHeight: 28
                    checked: root.activeTab === "compress"
                    onClicked: {
                        root.activeTab = "compress"
                        root.hasResult = false
                    }
                }
                AppButton {
                    text: I18n.t("archive.extract")
                    implicitHeight: 28
                    checked: root.activeTab === "extract"
                    onClicked: {
                        root.activeTab = "extract"
                        root.hasResult = false
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Theme.borderMuted
        }

        Rectangle {
            visible: !!archiveBackend
            Layout.fillWidth: true
            implicitHeight: toolStatusRow.implicitHeight + Theme.space2 * 2
            radius: Theme.radiusSm
            color: (archiveBackend && archiveBackend.has7z && archiveBackend.hasRar) ? Theme.successSoft : Theme.warningSoft
            border.width: 1
            border.color: (archiveBackend && archiveBackend.has7z && archiveBackend.hasRar) ? Theme.statusSuccess : Theme.accentWarn

            RowLayout {
                id: toolStatusRow
                anchors.fill: parent
                anchors.margins: Theme.space2
                spacing: Theme.space3
                Label { text: "7-Zip: " + (archiveBackend && archiveBackend.has7z ? I18n.t("tool_ready") : I18n.t("tool_missing")); color: archiveBackend && archiveBackend.has7z ? Theme.statusSuccess : Theme.accentWarn; font.pixelSize: Theme.fontMeta }
                Label { text: "RAR: " + (archiveBackend && archiveBackend.hasRar ? I18n.t("tool_ready") : I18n.t("tool_missing")); color: archiveBackend && archiveBackend.hasRar ? Theme.statusSuccess : Theme.accentWarn; font.pixelSize: Theme.fontMeta }
                Item { Layout.fillWidth: true }
                SecondaryButton {
                    text: I18n.t("configure")
                    implicitHeight: 28
                    onClicked: root.appRoot && root.appRoot.openSidebarSection(5, "app_update", root.appRoot.navIndexFor(5, "app_update"))
                }
            }
        }

        // -------------------------------------------------------------
        // Error banner if any
        // -------------------------------------------------------------
        Rectangle {
            visible: root.errorMessage.length > 0
            Layout.fillWidth: true
            implicitHeight: errRow.implicitHeight + Theme.space2 * 2
            radius: Theme.radiusSm
            color: Qt.rgba(1.0, 0.2, 0.2, 0.15)
            border.width: 1
            border.color: Qt.rgba(1.0, 0.2, 0.2, 0.3)

            RowLayout {
                id: errRow
                anchors.fill: parent
                anchors.margins: Theme.space2
                spacing: Theme.space2

                AppIcon {
                    name: "close"
                    implicitWidth: 16
                    implicitHeight: 16
                    iconColor: Theme.danger
                }
                Label {
                    Layout.fillWidth: true
                    text: root.errorMessage
                    color: Theme.danger
                    font.pixelSize: Theme.fontSizeXs
                    wrapMode: Text.Wrap
                }
                AppIconButton {
                    iconName: "close"
                    implicitWidth: 16
                    implicitHeight: 16
                    onClicked: root.errorMessage = ""
                }
            }
        }

        // -------------------------------------------------------------
        // Active Content Area
        // -------------------------------------------------------------
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: {
                if (archiveBackend && archiveBackend.isBusy) return 2 // Progress
                if (root.hasResult) return 3 // Result
                if (root.activeTab === "extract") return 1 // Extract
                return 0 // Compress
            }

            ArchiveCompressView {
                id: compressView
                archiveBackend: root.archiveBackend
                onArchiveDropped: function(path) {
                    root.openForArchive(path)
                }
            }

            ArchiveExtractView {
                id: extractView
                archiveBackend: root.archiveBackend
            }

            ArchiveProgressView {
                id: progressView
                archiveBackend: root.archiveBackend
                title: root.activeTab === "compress" ? I18n.t("archive.creating_archive") : I18n.t("archive.extracting_archive")
            }

            ArchiveResultView {
                id: resultView
                archiveBackend: root.archiveBackend
                isExtract: root.lastResultIsExtract
                onDoneClicked: {
                    root.hasResult = false
                }
            }
        }
    }
}
