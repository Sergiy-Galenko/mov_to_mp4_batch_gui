import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property string presetName: ""
    property string shortLabel: ""
    property string details: ""
    property bool active: false
    signal clicked()

    implicitWidth: Math.max(96, chipRow.implicitWidth + Theme.space5)
    implicitHeight: 34
    radius: Theme.radiusPill
    color: active ? Theme.accent : (mouse.containsMouse ? Theme.overlayHover : Theme.transparent)
    border.width: 1
    border.color: active ? Theme.accent : Theme.borderSubtle

    RowLayout {
        id: chipRow
        anchors.fill: parent
        anchors.leftMargin: Theme.space3
        anchors.rightMargin: Theme.space3
        spacing: Theme.space2

        Label {
            text: root.shortLabel
            color: root.active ? Theme.textOnAccent : Theme.accent
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontSizeXs
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: root.presetName
            color: root.active ? Theme.textOnAccent : Theme.textSecondary
            font.pixelSize: Theme.fontSizeXs
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.clicked()
    }

    ToolTip.visible: mouse.containsMouse && root.details.length > 0
    ToolTip.delay: 350
    ToolTip.text: root.details
}
