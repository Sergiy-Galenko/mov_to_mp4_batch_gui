import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

AppComboBox {
    id: control

    Layout.fillWidth: true
    implicitHeight: Theme.inputHeight
    font.pixelSize: 13
    leftPadding: 13
    rightPadding: 34
    textRole: "label"
    valueRole: "code"
    model: backend ? backend.availableLanguages : []
    hoverEnabled: true

    Component.onCompleted: syncFromBackend()
    onActivated: {
        if (backend)
            backend.setLanguage(currentValue)
    }

    Connections {
        target: backend
        function onLanguageChanged() {
            control.syncFromBackend()
        }
    }

    function syncFromBackend() {
        if (!backend || !model)
            return
        for (var i = 0; i < model.length; ++i) {
            if (model[i].code === backend.currentLanguage) {
                currentIndex = i
                return
            }
        }
        currentIndex = 0
    }

}
