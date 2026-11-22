import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

Item {
    id: root
    default property alias content: panelColumn.data
    property string title: ""
    property string iconName: ""
    property color iconTint: Theme.accent
    Layout.fillWidth: true
    implicitHeight: heading.height + (heading.visible ? 10 : 0) + panelColumn.implicitHeight + Theme.sectionPadding * 2

    RowLayout {
        id: heading
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 4
        visible: root.title.length > 0
        height: visible ? Math.max(titleLabel.implicitHeight, root.iconName ? 28 : 0) : 0
        spacing: 9
        NavigationIcon {
            visible: root.iconName.length > 0
            name: root.iconName
            tint: root.iconTint
            Layout.preferredWidth: 28; Layout.preferredHeight: 28
        }
        Label {
            id: titleLabel
            Layout.fillWidth: true
            text: root.title
            color: Theme.textPrimary
            font.family: Theme.bodyFont
            font.pixelSize: Theme.fontSizeMd
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
    }
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: heading.height + (heading.visible ? 10 : 0)
        height: panelColumn.implicitHeight + Theme.sectionPadding * 2
        radius: Theme.radiusPanel
        color: Theme.panelBackground
        border.width: Theme.panelBorderWidth
        border.color: Theme.borderMuted
        ColumnLayout {
            id: panelColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.sectionPadding
            spacing: Theme.space3
        }
    }
}
