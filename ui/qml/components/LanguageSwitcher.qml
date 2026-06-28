import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ComboBox {
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

    contentItem: Label {
        text: control.displayText
        color: control.enabled ? Theme.text : Theme.disabledText
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        leftPadding: 0
        rightPadding: 8
    }

    indicator: Item {
        width: 18
        height: 18
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            text: "v"
            color: Theme.muted
            font.pixelSize: 12
        }
    }

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.inputHover : Theme.input) : Theme.disabledBg
        border.width: 1
        border.color: control.activeFocus ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color { ColorAnimation { duration: 120 } }
    }

    delegate: ItemDelegate {
        width: control.width
        height: 38

        contentItem: Label {
            text: modelData.label || ""
            color: Theme.text
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            color: highlighted ? Theme.hover : "transparent"
            radius: 10
        }
    }

    popup: Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight, 260)
        padding: 8
        background: Rectangle {
            color: Theme.panelAlt
            border.width: 1
            border.color: Theme.borderStrong
            radius: Theme.radiusInput + 2
        }

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            spacing: 4
        }
    }
}
