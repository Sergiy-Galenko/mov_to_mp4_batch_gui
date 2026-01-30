import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: section
    property string title: ""
    default property alias content: bodyLayout.data

    color: Theme.section
    border.color: Theme.border
    radius: Theme.radiusSection
    implicitWidth: bodyLayout.implicitWidth + Theme.space2 * 2
    implicitHeight: bodyLayout.implicitHeight + Theme.space2 * 2 + titleLabel.implicitHeight
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space2
        spacing: Theme.space1

        Label {
            id: titleLabel
            text: section.title
            color: Theme.text
            font.weight: Font.DemiBold
            font.pixelSize: 13
        }

        ColumnLayout {
            id: bodyLayout
            spacing: Theme.space1
        }
    }
}
