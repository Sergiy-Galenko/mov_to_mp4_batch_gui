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
    border.color: Theme.border
    radius: Theme.radiusSection
    implicitWidth: bodyLayout.implicitWidth + Theme.sectionPadding * 2
    implicitHeight: bodyLayout.implicitHeight + Theme.sectionPadding * 2 + (title.length > 0 ? titleLabel.implicitHeight + Theme.space1 : 0)
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.sectionPadding
        spacing: Theme.space1

        Label {
            id: titleLabel
            visible: section.title.length > 0
            text: section.title
            color: Theme.text
            font.weight: Font.DemiBold
            font.pixelSize: 12
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        ColumnLayout {
            id: bodyLayout
            spacing: Theme.space1
        }
    }
}
