import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Panel {
    id: panel
    property var service
    property var settingsProvider
    signal presetSelected(string name)
    title: I18n.t("presets")
    iconName: "sliders"
    iconTint: "#AF52DE"

    AppComboBox {
        id: category
        objectName: "presetCategoryCombo"
        model: [I18n.t("presets_builtin"), I18n.t("presets_custom")]
    }
    AppComboBox {
        id: choices
        objectName: "presetSelectionCombo"
        model: panel.service ? (category.currentIndex === 0 ? panel.service.builtinPresetNames : panel.service.customPresetNames) : []
        onCurrentTextChanged: nameField.text = currentText.length > 0 ? currentText + " (" + I18n.t("presets_copy") + ")" : ""
    }
    FieldLabel { text: I18n.t("preset_name") }
    AppTextField {
        id: nameField
        objectName: "presetNameField"
        placeholderText: I18n.t("preset_name")
    }
    Flow {
        Layout.fillWidth: true
        spacing: Theme.space2
        SecondaryButton {
            text: I18n.t("load"); iconName: "folder"
            enabled: choices.currentText.length > 0
            onClicked: { panel.presetSelected(choices.currentText); panel.service.loadPreset(choices.currentText) }
        }
        SecondaryButton {
            text: I18n.t("save"); iconName: "save"
            enabled: category.currentIndex === 1 && choices.currentText.length > 0
            onClicked: panel.service.savePreset(choices.currentText, panel.settingsProvider())
        }
        SecondaryButton {
            text: I18n.t("presets_save_as"); iconName: "save"
            enabled: nameField.text.trim().length > 0
            onClicked: {
                panel.service.savePreset(nameField.text.trim(), panel.settingsProvider())
                category.currentIndex = 1
            }
        }
        SecondaryButton {
            text: I18n.t("delete"); iconName: "trash"
            enabled: category.currentIndex === 1 && choices.currentText.length > 0
            onClicked: panel.service.deletePreset(choices.currentText)
        }
        SecondaryButton { text: I18n.t("presets_import"); iconName: "folder"; onClicked: panel.service.importPresets() }
        SecondaryButton { text: I18n.t("presets_export"); iconName: "save"; onClicked: panel.service.exportPresets() }
    }
}
