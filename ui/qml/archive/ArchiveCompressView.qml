import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import App 1.0
import "../components"

Rectangle {
    id: root
    property var archiveBackend
    property var selectedSources: []
    property string selectedFormat: "zip"
    property string compressionPreset: "balanced"
    property string archiveName: "Archive"
    property string outputMode: "same"
    property string customOutputDir: ""
    property bool encryptArchive: false
    property string passwordText: ""
    property string confirmPasswordText: ""
    property bool showPassword: false
    property bool advancedExpanded: false
    property bool solidMode: true
    property string splitVolume: "off"
    property bool encryptFilenames: false

    property var sourceAnalysis: ({})
    signal archiveDropped(string archivePath)

    color: Theme.panelBackground
    clip: true

    function addPaths(paths) {
        if (!paths || paths.length === 0) return
        var list = selectedSources.slice()
        for (var i = 0; i < paths.length; ++i) {
            var raw = String(paths[i]).replace("file://", "").trim()
            if (raw.length === 0) continue
            // Check if archive dropped - switch to extract mode
            var lower = raw.toLowerCase()
            if (list.length === 0 && (lower.endsWith(".zip") || lower.endsWith(".7z") || lower.endsWith(".rar") ||
                lower.endsWith(".tar") || lower.endsWith(".tar.gz") || lower.endsWith(".tgz") ||
                lower.endsWith(".tar.bz2") || lower.endsWith(".tar.xz"))) {
                root.archiveDropped(raw)
                return
            }
            if (list.indexOf(raw) < 0) {
                list.push(raw)
            }
        }
        selectedSources = list
        updateAnalysis()
    }

    function removePath(index) {
        var list = selectedSources.slice()
        list.splice(index, 1)
        selectedSources = list
        updateAnalysis()
    }

    function clearAll() {
        selectedSources = []
        sourceAnalysis = {}
        archiveName = "Archive"
    }

    function updateAnalysis() {
        if (!archiveBackend || selectedSources.length === 0) {
            sourceAnalysis = {}
            return
        }
        var res = archiveBackend.analyzeSources(selectedSources)
        sourceAnalysis = res
        if (res.suggestedOutputName && (archiveName === "Archive" || archiveName.length === 0)) {
            archiveName = res.suggestedOutputName
        }
        if (res.suggestedPreset && res.isMostlyCompressed) {
            compressionPreset = "fast"
        }
    }

    function getFinalOutputPath() {
        var baseDir = ""
        if (outputMode === "custom" && customOutputDir.length > 0) {
            baseDir = customOutputDir
        } else if (archiveBackend && selectedSources.length > 0) {
            baseDir = archiveBackend.getDefaultOutputFolder(selectedSources)
        } else {
            baseDir = "."
        }

        var ext = "." + selectedFormat
        var name = (archiveName && archiveName.trim().length > 0) ? archiveName.trim() : "Archive"
        if (name.toLowerCase().endsWith(ext.toLowerCase())) {
            return baseDir + "/" + name
        }
        return baseDir + "/" + name + ext
    }

    function startArchiving() {
        if (selectedSources.length === 0) return
        if (encryptArchive && passwordText !== confirmPasswordText) return

        var outPath = getFinalOutputPath()
        var splitMb = 0
        if (splitVolume !== "off") {
            splitMb = parseInt(splitVolume) || 0
        }

        if (archiveBackend) {
            archiveBackend.createArchive(
                selectedSources,
                outPath,
                selectedFormat,
                compressionPreset,
                encryptArchive ? passwordText : "",
                encryptFilenames,
                splitMb,
                solidMode
            )
        }
    }

    function formatOptions() {
        return [
            { id: "zip", label: "ZIP", description: I18n.t("archive.zip_desc"), available: true },
            { id: "7z", label: "7Z", description: I18n.t("archive.sevenz_desc"), available: !!(archiveBackend && archiveBackend.has7z) },
            { id: "rar", label: "RAR", description: archiveBackend && archiveBackend.hasRar ? "RAR: сумісний формат WinRAR із підтримкою паролів." : "RAR потребує встановленого WinRAR (команда rar).", available: !!(archiveBackend && archiveBackend.hasRar) },
            { id: "tar.gz", label: "TAR.GZ", description: I18n.t("archive.targz_desc"), available: true },
            { id: "tar.bz2", label: "TAR.BZ2", description: "TAR.BZ2 забезпечує краще стиснення для тексту та даних.", available: true },
            { id: "tar.xz", label: "TAR.XZ", description: "TAR.XZ забезпечує високе стиснення для резервних копій.", available: true },
            { id: "tar", label: "TAR", description: "TAR швидко об’єднує файли без стиснення.", available: true },
            { id: "gz", label: "GZ", description: "GZ стискає один файл і добре підходить для журналів та тексту.", available: true, singleFile: true },
            { id: "bz2", label: "BZ2", description: "BZ2 стискає один файл із пріоритетом на менший розмір.", available: true, singleFile: true },
            { id: "xz", label: "XZ", description: "XZ стискає один файл із максимальним ступенем стиснення.", available: true, singleFile: true }
        ]
    }

    function selectedFormatInfo() {
        var formats = formatOptions()
        for (var i = 0; i < formats.length; ++i) {
            if (formats[i].id === selectedFormat)
                return formats[i]
        }
        return formats[0]
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
            // Drop Area & File Selection
            // -------------------------------------------------------------
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.selectedSources.length === 0 ? 110 : 80
                radius: Theme.radiusMd
                color: dropArea.containsDrag ? Theme.panelHover : Theme.panelSecondary
                border.width: dropArea.containsDrag ? 2 : 1
                border.color: dropArea.containsDrag ? Theme.accent : Theme.borderMuted

                DropArea {
                    id: dropArea
                    anchors.fill: parent
                    onEntered: function(drag) {
                        if (drag.hasUrls) drag.acceptProposedAction()
                    }
                    onDropped: function(drop) {
                        var urls = []
                        for (var i = 0; i < drop.urls.length; ++i) {
                            urls.push(drop.urls[i])
                        }
                        root.addPaths(urls)
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
                            text: root.selectedSources.length === 0 ? I18n.t("archive.drop_prompt") : I18n.t("archive.add_more_drop")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeSm
                        }
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.space2

                        AppButton {
                            text: "+ " + I18n.t("archive.add_files")
                            implicitHeight: 28
                            onClicked: fileDialog.open()
                        }
                        AppButton {
                            text: "+ " + I18n.t("archive.add_folder")
                            implicitHeight: 28
                            onClicked: folderDialog.open()
                        }
                        AppButton {
                            visible: root.selectedSources.length > 0
                            text: I18n.t("archive.clear_all")
                            implicitHeight: 28
                            onClicked: root.clearAll()
                        }
                    }
                }
            }

            // -------------------------------------------------------------
            // Selected Items List
            // -------------------------------------------------------------
            ColumnLayout {
                visible: root.selectedSources.length > 0
                Layout.fillWidth: true
                spacing: Theme.space2

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: root.selectedSources.length + " " + I18n.t("archive.items_selected") + (root.sourceAnalysis.totalSizeFormatted ? " · " + root.sourceAnalysis.totalSizeFormatted : "")
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                }

                ListView {
                    id: fileList
                    Layout.fillWidth: true
                    implicitHeight: Math.min(160, count * 36)
                    clip: true
                    model: root.selectedSources

                    delegate: Rectangle {
                        width: fileList.width
                        height: 34
                        radius: Theme.radiusSm
                        color: index % 2 === 0 ? Theme.surfaceBackground : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space2
                            anchors.rightMargin: Theme.space2
                            spacing: Theme.space2

                            AppIcon {
                                name: "file"
                                implicitWidth: 16
                                implicitHeight: 16
                                iconColor: Theme.accent
                            }

                            Label {
                                Layout.fillWidth: true
                                text: {
                                    var p = String(modelData)
                                    var parts = p.split(/[\\\/]/)
                                    return parts[parts.length - 1] || p
                                }
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeSm
                                elide: Text.ElideMiddle
                            }

                            AppIconButton {
                                iconName: "close"
                                implicitWidth: 20
                                implicitHeight: 20
                                onClicked: root.removePath(index)
                            }
                        }
                    }
                }
            }

            // Smart compression notice
            Rectangle {
                visible: !!root.sourceAnalysis && !!root.sourceAnalysis.notice
                Layout.fillWidth: true
                implicitHeight: noticeCol.implicitHeight + Theme.space3 * 2
                radius: Theme.radiusSm
                color: Qt.rgba(1.0, 0.6, 0.0, 0.12)
                border.width: 1
                border.color: Qt.rgba(1.0, 0.6, 0.0, 0.3)

                RowLayout {
                    id: noticeCol
                    anchors.fill: parent
                    anchors.margins: Theme.space3
                    spacing: Theme.space2

                    AppIcon {
                        name: "info"
                        implicitWidth: 16
                        implicitHeight: 16
                        iconColor: Theme.warning
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.sourceAnalysis.notice || ""
                        color: Theme.warning
                        font.pixelSize: Theme.fontSizeXs
                        wrapMode: Text.Wrap
                    }
                }
            }

            // -------------------------------------------------------------
            // Format Selector
            // -------------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    text: I18n.t("archive.format")
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                Flow {
                    id: formatFlow
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Repeater {
                        model: root.formatOptions()

                        AppButton {
                            required property var modelData
                            width: Math.max(110, (formatFlow.width - formatFlow.spacing * 2) / 3)
                            text: modelData.label
                            implicitHeight: 32
                            checked: root.selectedFormat === modelData.id
                            enabled: modelData.available && (!modelData.singleFile || root.selectedSources.length <= 1)
                            ToolTip.text: !modelData.available
                                ? modelData.description
                                : modelData.singleFile && root.selectedSources.length > 1
                                    ? "Цей формат підтримує лише один файл."
                                    : modelData.description
                            onClicked: if (enabled) root.selectedFormat = modelData.id
                        }
                    }
                }

                // Format description / recommendation
                Label {
                    Layout.fillWidth: true
                    text: root.selectedFormatInfo().description
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeXs
                    wrapMode: Text.Wrap
                }
            }

            // -------------------------------------------------------------
            // Compression Preset
            // -------------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space1

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: I18n.t("archive.compression_level")
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        visible: root.compressionPreset === "balanced"
                        text: I18n.t("archive.recommended")
                        font.pixelSize: Theme.fontSizeXs
                        color: Theme.accent
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.fast")
                        implicitHeight: 30
                        checked: root.compressionPreset === "fast"
                        onClicked: root.compressionPreset = "fast"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.balanced")
                        implicitHeight: 30
                        checked: root.compressionPreset === "balanced"
                        onClicked: root.compressionPreset = "balanced"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.maximum")
                        implicitHeight: 30
                        checked: root.compressionPreset === "maximum"
                        onClicked: root.compressionPreset = "maximum"
                    }
                }
            }

            // -------------------------------------------------------------
            // Archive Name
            // -------------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    text: I18n.t("archive.archive_name")
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppTextField {
                        id: nameInput
                        Layout.fillWidth: true
                        text: root.archiveName
                        placeholderText: "Archive"
                        onTextChanged: root.archiveName = text
                    }

                    Label {
                        text: "." + root.selectedFormat
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeSm
                        font.family: Theme.monoFont
                    }
                }
            }

            // -------------------------------------------------------------
            // Output Location
            // -------------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    text: I18n.t("archive.output_location")
                    font.pixelSize: Theme.fontSizeSm
                    font.weight: Font.DemiBold
                    color: Theme.textPrimary
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.same_folder")
                        implicitHeight: 30
                        checked: root.outputMode === "same"
                        onClicked: root.outputMode = "same"
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: I18n.t("archive.custom_folder")
                        implicitHeight: 30
                        checked: root.outputMode === "custom"
                        onClicked: {
                            root.outputMode = "custom"
                            outputFolderDialog.open()
                        }
                    }
                }

                Label {
                    visible: root.outputMode === "custom" && root.customOutputDir.length > 0
                    Layout.fillWidth: true
                    text: root.customOutputDir
                    font.pixelSize: Theme.fontSizeXs
                    color: Theme.textSecondary
                    elide: Text.ElideMiddle
                }
            }

            // -------------------------------------------------------------
            // Simple Password Encryption
            // -------------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space2

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: I18n.t("archive.encrypt_archive")
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    AppSwitch {
                        checked: root.encryptArchive
                        onToggled: root.encryptArchive = checked
                    }
                }

                ColumnLayout {
                    visible: root.encryptArchive
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space2

                        AppTextField {
                            id: passField
                            Layout.fillWidth: true
                            placeholderText: I18n.t("archive.password")
                            echoMode: root.showPassword ? TextInput.Normal : TextInput.Password
                            text: root.passwordText
                            onTextChanged: root.passwordText = text
                        }

                        AppIconButton {
                            iconName: root.showPassword ? "eye" : "lock"
                            onClicked: root.showPassword = !root.showPassword
                        }
                    }

                    AppTextField {
                        Layout.fillWidth: true
                        placeholderText: I18n.t("archive.confirm_password")
                        echoMode: root.showPassword ? TextInput.Normal : TextInput.Password
                        text: root.confirmPasswordText
                        onTextChanged: root.confirmPasswordText = text
                    }

                    Label {
                        visible: root.encryptArchive && root.passwordText.length > 0 && root.confirmPasswordText.length > 0 && root.passwordText !== root.confirmPasswordText
                        text: I18n.t("archive.passwords_do_not_match")
                        color: Theme.danger
                        font.pixelSize: Theme.fontSizeXs
                    }

                    RowLayout {
                        visible: root.selectedFormat === "7z"
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: I18n.t("archive.encrypt_filenames")
                            font.pixelSize: Theme.fontSizeXs
                            color: Theme.textSecondary
                        }
                        AppSwitch {
                            checked: root.encryptFilenames
                            onToggled: root.encryptFilenames = checked
                        }
                    }
                }
            }

            // -------------------------------------------------------------
            // Collapsible Advanced Settings
            // -------------------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space2

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 30
                    radius: Theme.radiusSm
                    color: Theme.panelSecondary

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.advancedExpanded = !root.advancedExpanded
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space2
                        anchors.rightMargin: Theme.space2

                        Label {
                            text: (root.advancedExpanded ? "▼ " : "▶ ") + I18n.t("archive.advanced_settings")
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                            color: Theme.textSecondary
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                ColumnLayout {
                    visible: root.advancedExpanded
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.space2
                    Layout.rightMargin: Theme.space2
                    spacing: Theme.space2

                    // Solid Archive Toggle
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: I18n.t("archive.solid_archive")
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                        }
                        AppSwitch {
                            checked: root.solidMode
                            onToggled: root.solidMode = checked
                        }
                    }

                    // Split Archive
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: I18n.t("archive.split_archive")
                            font.pixelSize: Theme.fontSizeSm
                            color: Theme.textPrimary
                        }
                        Item { Layout.fillWidth: true }
                        AppComboBox {
                            implicitWidth: 120
                            model: ["off", "100 MB", "500 MB", "1024 MB", "2048 MB", "4096 MB"]
                            onActivated: function(index) {
                                var val = model[index]
                                if (val === "off") root.splitVolume = "off"
                                else root.splitVolume = parseInt(val).toString()
                            }
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: Theme.space2 }

            // -------------------------------------------------------------
            // Main Action Button
            // -------------------------------------------------------------
            PrimaryButton {
                Layout.fillWidth: true
                implicitHeight: 40
                text: I18n.t("archive.create_archive")
                enabled: root.selectedSources.length > 0 && (!root.encryptArchive || (root.passwordText.length > 0 && root.passwordText === root.confirmPasswordText))
                onClicked: root.startArchiving()
            }
        }
    }

    // Dialogs
    FileDialog {
        id: fileDialog
        title: I18n.t("archive.select_files")
        onAccepted: {
            var urls = []
            for (var i = 0; i < selectedFiles.length; ++i) {
                urls.push(selectedFiles[i])
            }
            root.addPaths(urls)
        }
    }

    FolderDialog {
        id: folderDialog
        title: I18n.t("archive.select_folder")
        onAccepted: root.addPaths([selectedFolder])
    }

    FolderDialog {
        id: outputFolderDialog
        title: I18n.t("archive.select_output_folder")
        onAccepted: root.customOutputDir = String(selectedFolder).replace("file://", "").trim()
    }
}
