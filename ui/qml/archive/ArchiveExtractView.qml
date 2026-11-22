import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import App 1.0
import "../components"

Rectangle {
    id: root
    property var archiveBackend
    property string archivePath: ""
    property string password: ""
    property string destinationMode: "subfolder" // "subfolder", "here", "custom"
    property string customDestination: ""
    property string overwriteMode: "replace" // "replace", "skip", "keep_both"
    property string searchText: ""

    property var archiveItems: []
    property var selectedItemPaths: []
    property int totalFiles: 0
    property int totalBytes: 0
    property bool isPasswordRequired: false

    color: Theme.panelBackground
    clip: true

    function openFileDialog() {
        archiveFileDialog.open()
    }

    function setArchive(path) {
        var clean = String(path).replace("file://", "").trim()
        if (clean.length === 0) return
        archivePath = clean
        archiveItems = []
        selectedItemPaths = []
        isPasswordRequired = false
        if (archiveBackend) {
            archiveBackend.listArchive(archivePath, password)
        }
    }

    Connections {
        target: archiveBackend
        function onArchiveContentsReady(path, items, fCount, bCount) {
            if (path === root.archivePath) {
                root.archiveItems = items || []
                root.totalFiles = fCount
                root.totalBytes = bCount
                // Select all by default
                var allPaths = []
                for (var i = 0; i < root.archiveItems.length; ++i) {
                    allPaths.push(root.archiveItems[i].path)
                }
                root.selectedItemPaths = allPaths
            }
        }
        function onOperationError(title, msg, details) {
            if (String(msg).toLowerCase().indexOf("password") >= 0) {
                root.isPasswordRequired = true
            }
        }
    }

    function toggleSelectAll() {
        if (selectedItemPaths.length === archiveItems.length) {
            selectedItemPaths = []
        } else {
            var all = []
            for (var i = 0; i < archiveItems.length; ++i) {
                all.push(archiveItems[i].path)
            }
            selectedItemPaths = all
        }
    }

    function isSelected(path) {
        return selectedItemPaths.indexOf(path) >= 0
    }

    function toggleItem(path) {
        var list = selectedItemPaths.slice()
        var idx = list.indexOf(path)
        if (idx >= 0) {
            list.splice(idx, 1)
        } else {
            list.push(path)
        }
        selectedItemPaths = list
    }

    function getFinalDestination() {
        var p = archivePath
        var lastSlash = Math.max(p.lastIndexOf("/"), p.lastIndexOf("\\"))
        var parentDir = lastSlash >= 0 ? p.substring(0, lastSlash) : "."
        var baseName = lastSlash >= 0 ? p.substring(lastSlash + 1) : p
        var dotIdx = baseName.indexOf(".")
        var stem = dotIdx >= 0 ? baseName.substring(0, dotIdx) : baseName

        if (destinationMode === "subfolder") {
            return parentDir + "/" + stem
        } else if (destinationMode === "here") {
            return parentDir
        } else {
            return customDestination.length > 0 ? customDestination : parentDir
        }
    }

    function startExtracting() {
        if (!archivePath || !archiveBackend) return
        var dest = getFinalDestination()
        var filesToExtract = selectedItemPaths.length < archiveItems.length ? selectedItemPaths : []

        archiveBackend.extractArchive(
            archivePath,
            dest,
            filesToExtract,
            password,
            overwriteMode
        )
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: scroll.availableWidth
            spacing: Theme.space3

            // -------------------------------------------------------------
            // Drop Area / Archive Selector
            // -------------------------------------------------------------
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.archivePath.length === 0 ? 110 : 70
                radius: Theme.radiusMd
                color: extractDrop.containsDrag ? Theme.panelHover : Theme.panelSecondary
                border.width: extractDrop.containsDrag ? 2 : 1
                border.color: extractDrop.containsDrag ? Theme.accent : Theme.borderMuted

                DropArea {
                    id: extractDrop
                    anchors.fill: parent
                    onEntered: function(drag) {
                        if (drag.hasUrls) drag.acceptProposedAction()
                    }
                    onDropped: function(drop) {
                        if (drop.urls.length > 0) {
                            root.setArchive(drop.urls[0])
                        }
                        drop.acceptProposedAction()
                    }
                }

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: Theme.space2

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.space2
                        AppIcon {
                            name: "archive"
                            implicitWidth: 20
                            implicitHeight: 20
                            iconColor: Theme.accent
                        }
                        Label {
                            text: root.archivePath.length === 0 ? I18n.t("archive.drop_archive") : I18n.t("archive.selected_archive")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeSm
                        }
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.space2

                        AppButton {
                            text: I18n.t("archive.select_archive")
                            implicitHeight: 28
                            onClicked: archiveFileDialog.open()
                        }
                        AppButton {
                            visible: root.archivePath.length > 0
                            text: I18n.t("archive.change")
                            implicitHeight: 28
                            onClicked: archiveFileDialog.open()
                        }
                    }
                }
            }

            // -------------------------------------------------------------
            // Archive Details Card
            // -------------------------------------------------------------
            Rectangle {
                visible: root.archivePath.length > 0
                Layout.fillWidth: true
                implicitHeight: arcInfoCol.implicitHeight + Theme.space3 * 2
                radius: Theme.radiusSm
                color: Theme.panelSecondary
                border.width: 1
                border.color: Theme.borderMuted

                ColumnLayout {
                    id: arcInfoCol
                    anchors.fill: parent
                    anchors.margins: Theme.space3
                    spacing: Theme.space1

                    Label {
                        Layout.fillWidth: true
                        text: {
                            var parts = root.archivePath.split(/[\\\/]/)
                            return parts[parts.length - 1] || root.archivePath
                        }
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                        elide: Text.ElideMiddle
                    }
                    Label {
                        text: root.totalFiles + " " + I18n.t("archive.files")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeXs
                    }
                }
            }

            // Password Prompt (if needed)
            ColumnLayout {
                visible: root.isPasswordRequired || (root.archivePath.length > 0 && root.archiveItems.length === 0)
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    text: I18n.t("archive.password_required")
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.warning
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppTextField {
                        id: unlockPass
                        Layout.fillWidth: true
                        placeholderText: I18n.t("archive.enter_password")
                        echoMode: TextInput.Password
                        text: root.password
                        onTextChanged: root.password = text
                    }

                    AppButton {
                        text: I18n.t("archive.unlock")
                        implicitHeight: 32
                        onClicked: {
                            if (archiveBackend && root.archivePath) {
                                archiveBackend.listArchive(root.archivePath, root.password)
                            }
                        }
                    }
                }
            }

            // -------------------------------------------------------------
            // Content Preview & Selective Extraction
            // -------------------------------------------------------------
            ColumnLayout {
                visible: root.archiveItems.length > 0
                Layout.fillWidth: true
                spacing: Theme.space2

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: I18n.t("archive.contents") + " (" + root.archiveItems.length + ")"
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    AppButton {
                        text: root.selectedItemPaths.length === root.archiveItems.length ? I18n.t("archive.deselect_all") : I18n.t("archive.select_all")
                        implicitHeight: 24
                        onClicked: root.toggleSelectAll()
                    }
                }

                // Search field
                AppTextField {
                    Layout.fillWidth: true
                    placeholderText: "🔍 " + I18n.t("archive.search_files")
                    text: root.searchText
                    onTextChanged: root.searchText = text
                }

                // File list
                ListView {
                    id: previewList
                    Layout.fillWidth: true
                    implicitHeight: Math.min(180, count * 34)
                    clip: true
                    model: {
                        if (!root.searchText || root.searchText.trim().length === 0) return root.archiveItems
                        var needle = root.searchText.toLowerCase().trim()
                        return root.archiveItems.filter(function(item) {
                            return String(item.name).toLowerCase().indexOf(needle) >= 0 || String(item.path).toLowerCase().indexOf(needle) >= 0
                        })
                    }

                    delegate: Rectangle {
                        width: previewList.width
                        height: 32
                        radius: Theme.radiusSm
                        color: index % 2 === 0 ? Theme.panelSecondary : Theme.panelBackground
                        border.width: 1
                        border.color: Theme.borderMuted

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space2
                            anchors.rightMargin: Theme.space2
                            spacing: Theme.space2

                            AppCheckBox {
                                checked: root.isSelected(modelData.path)
                                onToggled: root.toggleItem(modelData.path)
                            }

                            AppIcon {
                                name: modelData.iconType || "file"
                                implicitWidth: 16
                                implicitHeight: 16
                                iconColor: Theme.accent
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1

                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.name || modelData.path
                                    color: Theme.textPrimary
                                    font.pixelSize: Theme.fontSizeSm
                                    elide: Text.ElideMiddle
                                }

                                Label {
                                    visible: {
                                        var p = String(modelData.path || "")
                                        return p.indexOf("/") >= 0 || p.indexOf("\\") >= 0
                                    }
                                    Layout.fillWidth: true
                                    text: {
                                        var p = String(modelData.path || "")
                                        var idx = Math.max(p.lastIndexOf("/"), p.lastIndexOf("\\"))
                                        return idx >= 0 ? p.substring(0, idx) : ""
                                    }
                                    color: Theme.textSecondary
                                    font.pixelSize: 10
                                    elide: Text.ElideMiddle
                                }
                            }

                            Label {
                                text: modelData.sizeFormatted || ""
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontSizeXs
                                font.family: Theme.monoFont
                            }
                        }
                    }
                }
            }

            // -------------------------------------------------------------
            // Destination Options
            // -------------------------------------------------------------
            ColumnLayout {
                visible: root.archivePath.length > 0
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    text: I18n.t("archive.extract_to")
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.subfolder")
                        implicitHeight: 30
                        checked: root.destinationMode === "subfolder"
                        onClicked: root.destinationMode = "subfolder"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.extract_here")
                        implicitHeight: 30
                        checked: root.destinationMode === "here"
                        onClicked: root.destinationMode = "here"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.custom")
                        implicitHeight: 30
                        checked: root.destinationMode === "custom"
                        onClicked: {
                            root.destinationMode = "custom"
                            extractFolderDialog.open()
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: root.getFinalDestination()
                    font.pixelSize: Theme.fontSizeXs
                    color: Theme.textSecondary
                    elide: Text.ElideMiddle
                }
            }

            // -------------------------------------------------------------
            // Collision Mode (Replace / Skip / Keep Both)
            // -------------------------------------------------------------
            ColumnLayout {
                visible: root.archivePath.length > 0
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    text: I18n.t("archive.if_file_exists")
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.replace")
                        implicitHeight: 28
                        checked: root.overwriteMode === "replace"
                        onClicked: root.overwriteMode = "replace"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.skip")
                        implicitHeight: 28
                        checked: root.overwriteMode === "skip"
                        onClicked: root.overwriteMode = "skip"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.keep_both")
                        implicitHeight: 28
                        checked: root.overwriteMode === "keep_both"
                        onClicked: root.overwriteMode = "keep_both"
                    }
                }
            }

            Item { Layout.preferredHeight: Theme.space2 }

            // -------------------------------------------------------------
            // Extract Action Button
            // -------------------------------------------------------------
            PrimaryButton {
                Layout.fillWidth: true
                implicitHeight: 40
                text: root.selectedItemPaths.length < root.archiveItems.length && root.selectedItemPaths.length > 0
                    ? I18n.t("archive.extract_selected") + " (" + root.selectedItemPaths.length + ")"
                    : I18n.t("archive.extract_all")
                enabled: root.archivePath.length > 0
                onClicked: root.startExtracting()
            }
        }
    }

    // Dialogs
    FileDialog {
        id: archiveFileDialog
        title: I18n.t("archive.select_archive")
        onAccepted: {
            if (selectedFile) root.setArchive(selectedFile)
        }
    }

    FolderDialog {
        id: extractFolderDialog
        title: I18n.t("archive.select_destination")
        onAccepted: root.customDestination = String(selectedFolder).replace("file://", "").trim()
    }
}
