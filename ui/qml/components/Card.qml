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
    implicitWidth: contentLayout.implicitWidth + Theme.cardPadding * 2
    implicitHeight: contentLayout.implicitHeight + Theme.cardPadding * 2
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.cardPadding
        spacing: Theme.space2

        Label {
            visible: card.title.length > 0
            text: card.title
            color: Theme.text
            font.weight: Font.DemiBold
            font.pixelSize: 13
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        ColumnLayout {
            id: contentLayout
            spacing: Theme.space2
        }
    }
}
