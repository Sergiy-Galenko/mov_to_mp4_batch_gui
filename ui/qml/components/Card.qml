import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: card
    property string title: ""
    default property alias content: contentLayout.data

    radius: Theme.radiusCard
    color: Theme.panel
    border.width: 1
    border.color: Theme.border
    implicitWidth: contentLayout.implicitWidth + Theme.space3 * 2
    implicitHeight: contentLayout.implicitHeight + Theme.space3 * 2
    Layout.fillWidth: true

    gradient: Gradient {
        GradientStop { position: 0.0; color: Qt.rgba(0.09, 0.16, 0.26, 0.98) }
        GradientStop { position: 1.0; color: Qt.rgba(0.06, 0.11, 0.19, 0.98) }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: Qt.rgba(1, 1, 1, 0.08)
    }

    Rectangle {
        width: 160
        height: 160
        radius: 80
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: -68
        anchors.rightMargin: -42
        color: Qt.rgba(1, 0.45, 0.27, 0.10)
    }

    Rectangle {
        visible: card.title.length > 0
        width: 64
        height: 4
        radius: 2
        anchors.left: parent.left
        anchors.leftMargin: Theme.space3
        anchors.top: parent.top
        anchors.topMargin: Theme.space3 - 10
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.accent }
            GradientStop { position: 1.0; color: Theme.accent2 }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space3
        spacing: Theme.space2

        RowLayout {
            visible: title.length > 0
            spacing: Theme.space2

            Label {
                text: card.title
                color: Theme.text
                font.weight: Font.DemiBold
                font.pixelSize: 15
                font.letterSpacing: 0.2
            }

            Item { Layout.fillWidth: true }
        }

        ColumnLayout {
            id: contentLayout
            spacing: Theme.space2
        }
    }
}
