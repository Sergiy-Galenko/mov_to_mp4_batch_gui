import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs as Dialogs
import App 1.0

Dialog {
    id: root
    objectName: "themeEditorDialog"
    parent: Overlay.overlay
    width: Math.min(parent ? parent.width - 32 : 920, 980)
    height: Math.min(parent ? parent.height - 32 : 720, 800)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    modal: true
    focus: true
    padding: 16
    closePolicy: Popup.CloseOnEscape
    property string group: "surfaces"
    property string editingColorKey: ""
    readonly property var fields: backend ? backend.themeColorDefinitions.filter(function(field) { return field.group === root.group }) : []
    readonly property var modes: ["dark", "light", "obsidian", "oled", "midnight", "high_contrast", "auto"]
    title: I18n.t("appearance.title")

    Overlay.modal: Rectangle { color: Theme.modalScrim }
    background: Rectangle { color: Theme.panelBackground; radius: Theme.radiusLg; border.width: 1; border.color: Theme.borderDefault }
    header: RowLayout {
        height: 58
        Label { Layout.fillWidth: true; Layout.leftMargin: 16; text: root.title; color: Theme.textPrimary; font.pixelSize: Theme.fontHeading; font.bold: true; elide: Text.ElideRight }
        AppIconButton { Layout.rightMargin: 12; iconName: "close"; accessibleLabel: I18n.t("close"); onClicked: root.close() }
    }

    contentItem: ColumnLayout {
        spacing: 12
        Label {
            Layout.fillWidth: true
            text: I18n.t("appearance.description")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeSm
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true
                FieldLabel { text: I18n.t("theme_mode"); wrapMode: Text.WordWrap }
                AppComboBox {
                    objectName: "themeModeCombo"
                    model: root.modes
                    translationPrefix: "appearance.mode."
                    currentIndex: backend ? Math.max(0, root.modes.indexOf(backend.themeMode)) : 0
                    Accessible.name: I18n.t("theme_mode")
                    onActivated: backend.themeMode = currentText
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                FieldLabel { text: I18n.t("appearance.density"); wrapMode: Text.WordWrap }
                AppComboBox {
                    model: ["compact", "comfortable", "spacious"]
                    translationPrefix: "appearance.density."
                    currentIndex: backend ? Math.max(0, model.indexOf(backend.layoutMode)) : 1
                    Accessible.name: I18n.t("appearance.density")
                    onActivated: backend.layoutMode = currentText
                }
            }
            ColumnLayout {
                Layout.preferredWidth: root.width > 820 ? 220 : 160
                FieldLabel { text: I18n.t("appearance.text_size") + " · " + Math.round(fontSlider.value * 100) + "%"; wrapMode: Text.WordWrap }
                Slider {
                    id: fontSlider
                    objectName: "themeFontSlider"
                    Layout.fillWidth: true
                    from: 0.7; to: 1.5; stepSize: 0.05
                    value: backend ? backend.fontScale : 1
                    Accessible.name: I18n.t("appearance.text_size")
                    onPressedChanged: if (!pressed && backend) backend.fontScale = value
                    onMoved: if (!pressed && backend) backend.fontScale = value
                }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.borderMuted }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                AppComboBox {
                    objectName: "themeColorGroup"
                    model: ["surfaces", "text", "borders", "actions", "status", "media"]
                    translationPrefix: "appearance.group."
                    Accessible.name: I18n.t("appearance.colors")
                    onActivated: root.group = currentText
                }
                ListView {
                    id: colorList
                    objectName: "themeColorList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    clip: true
                    model: root.fields
                    spacing: 4
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}
                    delegate: Rectangle {
                        id: colorRow
                        width: ListView.view.width - 12
                        height: Math.max(52, Theme.inputHeight + 12)
                        color: index % 2 ? Theme.subtleFill : Theme.transparent
                        radius: Theme.radiusSm
                        readonly property string key: modelData.key
                        readonly property string value: backend ? backend.themePalette[key] : "#000000"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8
                            Button {
                                Layout.preferredWidth: 34
                                Layout.preferredHeight: 32
                                Accessible.name: I18n.t("appearance.color." + colorRow.key)
                                background: Rectangle { color: colorRow.value; radius: Theme.radiusSm; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Theme.focusRing : Theme.borderDefault }
                                onClicked: {
                                    root.editingColorKey = colorRow.key
                                    colorDialog.selectedColor = colorRow.value
                                    colorDialog.open()
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: I18n.t("appearance.color." + colorRow.key)
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeSm
                                elide: Text.ElideRight
                            }
                            AppTextField {
                                id: hexField
                                objectName: "themeHex_" + colorRow.key
                                Layout.fillWidth: false
                                Layout.preferredWidth: Math.max(112, Math.round(100 * Theme.fontScale + 26))
                                font.family: Theme.monoFont
                                maximumLength: 9
                                Accessible.name: I18n.t("appearance.color." + colorRow.key) + " HEX"
                                validator: RegularExpressionValidator { regularExpression: /#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})/ }
                                invalid: text.length > 0 && !acceptableInput
                                text: colorRow.value
                                Connections {
                                    target: colorRow
                                    function onValueChanged() { if (!hexField.activeFocus) hexField.text = colorRow.value }
                                }
                                function commitColor() {
                                    if (acceptableInput && backend) backend.setThemeColor(colorRow.key, text)
                                }
                                onEditingFinished: commitColor()

                                ToolTip.visible: hovered || (activeFocus && invalid)
                                ToolTip.text: I18n.t("appearance.hex_hint")
                            }
                            AppIconButton {
                                iconName: "refresh"
                                accessibleLabel: I18n.t("reset")
                                enabled: backend && backend.themeColorOverrides[colorRow.key] !== undefined
                                onClicked: backend.resetThemeColor(colorRow.key)
                            }
                        }
                    }
                }
            }
            Rectangle {
                visible: root.width > 820
                Layout.preferredWidth: 240
                Layout.fillHeight: true
                color: Theme.windowBackground
                radius: Theme.radiusMd
                border.width: 1; border.color: Theme.borderMuted
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12
                    BrandMark { Layout.preferredWidth: 40; Layout.preferredHeight: 40 }
                    Label { Layout.fillWidth: true; text: I18n.t("appearance.preview"); color: Theme.textPrimary; font.pixelSize: Theme.fontSizeLg; font.bold: true; wrapMode: Text.WordWrap }
                    Label { Layout.fillWidth: true; text: I18n.t("appearance.preview_detail"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; wrapMode: Text.WordWrap }
                    AppTextField { placeholderText: I18n.t("queue_search") }
                    PrimaryButton { text: I18n.t("convert_all") }
                    AppProgressBar { Layout.fillWidth: true; value: 0.65 }
                    StatusBadge { Layout.fillWidth: true; status: "success"; label: I18n.t("status.done") }
                    StatusBadge { Layout.fillWidth: true; status: "failed"; label: I18n.t("status.failed") }
                    Item { Layout.fillHeight: true }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            AppTextField { id: themeName; objectName: "themeNameField"; placeholderText: I18n.t("appearance.name"); maximumLength: 64 }
            SecondaryButton { Layout.fillWidth: false; text: I18n.t("save"); enabled: themeName.text.trim().length > 0; onClicked: backend && backend.saveNamedTheme(themeName.text) }
            AppComboBox {
                id: savedThemes
                Layout.preferredWidth: 180
                model: backend ? backend.savedThemeNames : []
                enabled: count > 0
                displayText: count ? currentText : I18n.t("appearance.saved_themes")
                Accessible.name: I18n.t("appearance.saved_themes")
                onActivated: backend.loadNamedTheme(currentText)
            }
            AppIconButton { iconName: "close"; enabled: savedThemes.count > 0; accessibleLabel: I18n.t("delete"); onClicked: backend.deleteNamedTheme(savedThemes.currentText) }
        }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { text: I18n.t("import_theme"); onClicked: backend && backend.importThemeFile() }
            SecondaryButton { text: I18n.t("export_theme"); onClicked: backend && backend.exportThemeFile() }
            SecondaryButton { text: I18n.t("appearance.reset_colors"); onClicked: backend && backend.resetThemeColors() }
        }
        Label { Layout.fillWidth: true; text: I18n.t("appearance.recovery_shortcut"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeXs; wrapMode: Text.WordWrap }
    }
    Dialogs.ColorDialog {
        id: colorDialog
        objectName: "themeColorDialog"
        title: I18n.t("appearance.color." + root.editingColorKey)
        options: Dialogs.ColorDialog.DontUseNativeDialog | Dialogs.ColorDialog.ShowAlphaChannel
        onAccepted: backend && backend.setThemeColor(root.editingColorKey, selectedColor.toString())
    }
}
