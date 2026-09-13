import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property var appRoot
    implicitWidth: 328
    color: Theme.panelBackground
    border.width: 1
    border.color: Theme.borderMuted
    clip: true

    property bool cropModeEnabled: false
    readonly property bool batchSelection: appRoot && appRoot.selectedPaths.length > 1
    readonly property bool hasSelection: appRoot && appRoot.selectedPath.length > 0

    function syncEditorValues() {
        var details = appRoot ? appRoot.selectedDetails : ({})
        trimStartSpin.value = Math.round(Number(details.trimStart || 0))
        trimEndSpin.value = Math.round(Number(details.trimEnd || 0))
        timelineTrim.trimStart = trimStartSpin.value
        timelineTrim.trimEnd = trimEndSpin.value
        fastCopyCheck.checked = !!details.fastCopy
    }

    Connections {
        target: appRoot
        function onSelectedDetailsChanged() { root.syncEditorValues() }
    }
    Component.onCompleted: syncEditorValues()

    ScrollView {
        id: inspectorScroll
        contentWidth: availableWidth
        contentHeight: inspectorContent.implicitHeight
        anchors.fill: parent
        anchors.margins: Theme.space3
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            id: inspectorContent
            width: inspectorScroll.availableWidth
            spacing: Theme.space3

            RowLayout {
                Layout.fillWidth: true; Layout.minimumWidth: 0
                Label {
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    text: root.batchSelection ? I18n.t("selected") + " · " + appRoot.selectedPaths.length : I18n.t("selected_file")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeMd
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                AppIconButton {
                    iconName: "close"
                    accessibleLabel: I18n.t("cancel")
                    onClicked: appRoot.clearQueueSelection()
                }
            }

            Rectangle {
                visible: !root.batchSelection && appRoot && appRoot.selectedMediaType !== "text"
                Layout.fillWidth: true; Layout.minimumWidth: 0
                Layout.preferredHeight: 164
                radius: Theme.radiusMd
                color: Theme.panelSecondary
                border.width: 1
                border.color: Theme.borderMuted
                clip: true

                Image {
                    id: selectedThumbnail
                    anchors.fill: parent
                    anchors.margins: 8
                    source: appRoot ? appRoot.selectedThumbnailSource : ""
                    sourceSize: Qt.size(960, 640)
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    visible: source.toString().length > 0
                }

                AppIcon {
                    anchors.centerIn: parent
                    visible: selectedThumbnail.status !== Image.Ready
                    name: "file"
                    iconColor: Theme.textMuted
                    width: 36
                    height: 36
                }

                CropOverlay {
                    id: cropOverlay
                    active: root.cropModeEnabled && selectedThumbnail.visible
                    nativeWidth: {
                        var res = backend ? (backend.infoRes || "") : ""
                        var m = res.match(/(\d+)\s*[x×]\s*(\d+)/)
                        return m ? parseInt(m[1]) : 1920
                    }
                    nativeHeight: {
                        var res = backend ? (backend.infoRes || "") : ""
                        var m = res.match(/(\d+)\s*[x×]\s*(\d+)/)
                        return m ? parseInt(m[2]) : 1080
                    }
                    onCropChanged: function(x, y, w, h) {
                        if (backend && appRoot.selectedPath.length > 0) {
                            backend.updateTaskOverrideByPath(appRoot.selectedPath, {
                                crop_x: x,
                                crop_y: y,
                                crop_w: w,
                                crop_h: h
                            })
                        }
                    }
                    onResetRequested: {
                        if (backend && appRoot.selectedPath.length > 0) {
                            backend.updateTaskOverrideByPath(appRoot.selectedPath, {
                                crop_x: null,
                                crop_y: null,
                                crop_w: null,
                                crop_h: null
                            })
                        }
                    }
                }

                // Toggle Crop button in top-right of preview
                Button {
                    visible: selectedThumbnail.visible && (appRoot.selectedMediaType === "video" || appRoot.selectedMediaType === "image")
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 6
                    text: root.cropModeEnabled ? "✓ Готово" : "✂ Crop"
                    implicitHeight: 24
                    onClicked: root.cropModeEnabled = !root.cropModeEnabled
                }
            }

            ScrollView {
                objectName: "selectedTextPreview"
                visible: !root.batchSelection && appRoot && appRoot.selectedMediaType === "text"
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredHeight: 220
                contentWidth: availableWidth
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                TextArea {
                    width: parent.width
                    text: appRoot ? appRoot.selectedTextPreview : ""
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    textFormat: TextEdit.PlainText
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeSm
                    background: Rectangle { color: Theme.panelSecondary; radius: Theme.radiusMd }
                }
            }

            Label {
                visible: !root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                text: appRoot ? (appRoot.selectedName || appRoot.selectedPath) : ""
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeMd
                font.weight: Font.DemiBold
                maximumLineCount: 2
                elide: Text.ElideMiddle
                wrapMode: Text.Wrap
            }

            Label {
                visible: !root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                text: appRoot ? appRoot.selectedPath : ""
                color: Theme.textMuted
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                elide: Text.ElideMiddle
            }

            GridLayout {
                visible: !root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                columns: 2
                columnSpacing: Theme.space2
                rowSpacing: 7

                Label { text: I18n.t("media_type"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; Layout.minimumWidth: 0; text: appRoot ? String(appRoot.selectedMediaType || "—").toUpperCase() : "—"; color: Theme.textSecondary; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("resolution"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; Layout.minimumWidth: 0; text: backend ? backend.infoRes || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("queue_show_duration"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; Layout.minimumWidth: 0; text: backend ? backend.infoDuration || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("codec"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; Layout.minimumWidth: 0; text: backend ? backend.infoCodec || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
                Label { text: I18n.t("source_size"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                Label { Layout.fillWidth: true; Layout.minimumWidth: 0; text: backend ? backend.infoSize || "—" : "—"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
            }

            Label { visible: !root.batchSelection; text: I18n.t("output_format"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }

            AppComboBox {
                id: formatCombo
                visible: !root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                model: appRoot ? appRoot.formatOptionsFor(appRoot.selectedMediaType) : []
                currentIndex: appRoot ? Math.max(0, find(appRoot.selectedPreviewFormat)) : 0
                onActivated: if (appRoot) appRoot.selectedPreviewFormat = currentText
            }

            Rectangle { Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredHeight: 1; color: Theme.borderMuted }

            // Visual Trim In / Out Section for Video and Audio
            ColumnLayout {
                visible: !root.batchSelection && (appRoot && (appRoot.selectedMediaType === "video" || appRoot.selectedMediaType === "audio"))
                Layout.fillWidth: true; Layout.minimumWidth: 0
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    Label {
                        Layout.fillWidth: true; Layout.minimumWidth: 0
                        text: "✂ " + I18n.t("trim")
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeSm
                        font.weight: Font.DemiBold
                    }
                    Button {
                        text: I18n.t("reset")
                        implicitHeight: 22
                        onClicked: {
                            trimStartSpin.value = 0
                            trimEndSpin.value = 0
                            timelineTrim.trimStart = 0
                            timelineTrim.trimEnd = 0
                            if (backend && appRoot.selectedPath.length > 0) {
                                backend.updateTaskOverrideByPath(appRoot.selectedPath, { trim_start: null, trim_end: null })
                            }
                        }
                    }
                }

                // Interactive Timeline Trim Slider
                TimelineTrimSlider {
                    id: timelineTrim
                    Layout.fillWidth: true
                    totalDuration: {
                        var d = appRoot && appRoot.selectedDetails ? Number(appRoot.selectedDetails.durationSec || 0) : 0
                        return d > 0 ? d : 120.0
                    }
                    trimStart: trimStartSpin.value
                    trimEnd: trimEndSpin.value
                    onTrimModified: function(start, end) {
                        trimStartSpin.value = start
                        trimEndSpin.value = end
                        if (backend && appRoot.selectedPath.length > 0) {
                            backend.updateTaskOverrideByPath(appRoot.selectedPath, {
                                trim_start: start > 0 ? start : null,
                                trim_end: end > 0 ? end : null
                            })
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    spacing: 6
                    Label { text: I18n.t("trim_in"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                    AppSpinBox {
                        id: trimStartSpin
                        objectName: "inspectorTrimStart"
                        Layout.preferredWidth: 1
                        Layout.fillWidth: true; Layout.minimumWidth: 0
                        from: 0
                        to: 999999
                        value: 0
                        onValueModified: {
                            timelineTrim.trimStart = value
                            if (backend && appRoot.selectedPath.length > 0) {
                                backend.updateTaskOverrideByPath(appRoot.selectedPath, { trim_start: value > 0 ? value : null })
                            }
                        }
                    }
                    Label { text: I18n.t("trim_out"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta }
                    AppSpinBox {
                        id: trimEndSpin
                        objectName: "inspectorTrimEnd"
                        Layout.preferredWidth: 1
                        Layout.fillWidth: true; Layout.minimumWidth: 0
                        from: 0
                        to: 999999
                        value: 0
                        onValueModified: {
                            timelineTrim.trimEnd = value
                            if (backend && appRoot.selectedPath.length > 0) {
                                backend.updateTaskOverrideByPath(appRoot.selectedPath, { trim_end: value > 0 ? value : null })
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    Label {
                        text: I18n.t("lossless_fast_copy")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontMeta
                    }
                    Item { Layout.fillWidth: true; Layout.minimumWidth: 0 }
                    AppCheckBox {
                        id: fastCopyCheck
                        objectName: "inspectorFastCopy"
                        checked: false
                        onToggled: {
                            if (backend && appRoot.selectedPath.length > 0) {
                                backend.updateTaskOverrideByPath(appRoot.selectedPath, { fast_copy: checked })
                            }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredHeight: 1; color: Theme.borderMuted }

            Label {
                visible: root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                text: root.batchSelection ? appRoot.selectedPaths.length + " " + I18n.t("files") + " " + I18n.t("selected").toLowerCase() : ""
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSm
                wrapMode: Text.WordWrap
            }

            Button {
                visible: root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                implicitHeight: Theme.buttonHeight
                enabled: root.batchSelection
                text: I18n.t("batch_override")
                onClicked: appRoot && appRoot.openSidebarSection(5, "selected_override", appRoot.navIndexFor(5, "selected_override"))
            }

            Button {
                visible: root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                implicitHeight: Theme.buttonHeight
                enabled: root.batchSelection && backend && !backend.isRunning
                text: I18n.t("convert_selected")
                onClicked: appRoot && appRoot.convertSelectedPaths()
            }

            Button {
                visible: root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                implicitHeight: Theme.buttonHeight
                enabled: root.batchSelection
                text: I18n.t("batch_remove")
                onClicked: appRoot && appRoot.removeSelectedPaths()
            }

            Button {
                visible: !root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                implicitHeight: Theme.buttonHeight
                enabled: root.hasSelection && backend && !backend.isRunning
                text: I18n.t("convert_this_file")
                onClicked: appRoot && appRoot.convertSelectedFormat(formatCombo.currentText)
            }

            Button {
                visible: !root.batchSelection
                Layout.fillWidth: true; Layout.minimumWidth: 0
                implicitHeight: Theme.buttonHeight
                enabled: root.hasSelection
                text: I18n.t("change")
                onClicked: appRoot && appRoot.openSelectedSettings()
            }
        }
    }
}
