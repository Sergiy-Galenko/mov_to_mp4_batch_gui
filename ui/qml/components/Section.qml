import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: section
    property string title: ""
    default property alias content: bodyLayout.data

    color: Theme.section
    border.width: 1
    border.color: Qt.rgba(0.22, 0.34, 0.50, 0.95)
    radius: Theme.radiusSection
    implicitWidth: bodyLayout.implicitWidth + Theme.space2 * 2
    implicitHeight: bodyLayout.implicitHeight + Theme.space2 * 2 + titleLabel.implicitHeight
    Layout.fillWidth: true

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.02)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space2
        spacing: Theme.space1

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space1

            Rectangle {
                width: 8
                height: 8
                radius: 4
                color: Theme.accent
            }

            Label {
                id: titleLabel
                text: section.title
                color: Theme.text
                font.weight: Font.DemiBold
                font.pixelSize: 13
            }

            Item { Layout.fillWidth: true }
        }

        ColumnLayout {
            id: bodyLayout
            spacing: Theme.space1
        }
    }
}
