import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

Rectangle {
    default property alias content: panelColumn.data
    property string title: ""
    Layout.fillWidth: true
    radius: Theme.radiusMd
    color: Theme.bgSecondary
    border.width: 1
    border.color: Theme.borderSubtle
    implicitHeight: panelColumn.implicitHeight + 26

    ColumnLayout {
        id: panelColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        Label {
            visible: parent.parent.title.length > 0
            text: parent.parent.title
            color: Theme.textPrimary
            font.family: Theme.displayFont
            font.pixelSize: Theme.fontSizeLg
            font.bold: true
        }
    }
}
