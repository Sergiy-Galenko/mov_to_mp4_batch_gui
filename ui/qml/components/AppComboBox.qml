import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ComboBox {
    id: control
    font.pixelSize: 13
    implicitHeight: 36
    leftPadding: 10
    rightPadding: 28
    Layout.fillWidth: true

    contentItem: Label {
        text: control.displayText
        color: control.enabled ? Theme.text : Theme.disabledText
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Item {
        width: 18
        height: 18
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        Text {
            anchors.centerIn: parent
            text: "v"
            color: Theme.muted
            font.pixelSize: 12
        }
    }

    background: Rectangle {
        radius: 10
        color: control.enabled ? Theme.input : Theme.disabledBg
        border.color: Theme.border
    }

    delegate: ItemDelegate {
        width: control.width
        contentItem: Label {
            text: modelData
            color: Theme.text
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: highlighted ? Theme.hover : "transparent"
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight, 240)
        background: Rectangle {
            color: Theme.panel
            border.color: Theme.border
            radius: 10
        }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
        }
    }
}
