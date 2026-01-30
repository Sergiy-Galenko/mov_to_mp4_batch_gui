import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: card
    property string title: ""
    default property alias content: contentLayout.data

    color: Theme.panel
    border.color: Theme.border
    radius: Theme.radiusCard
    implicitWidth: contentLayout.implicitWidth + Theme.space3 * 2
    implicitHeight: contentLayout.implicitHeight + Theme.space3 * 2
    Layout.fillWidth: true

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
                font.pixelSize: 14
            }
            Item { Layout.fillWidth: true }
        }

        ColumnLayout {
            id: contentLayout
            spacing: Theme.space2
        }
    }
}
