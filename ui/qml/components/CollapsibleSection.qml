import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    default property alias content: body.data
    property string title: ""
    property string subtitle: ""
    property bool expanded: false

    Layout.fillWidth: true
    implicitHeight: header.implicitHeight + (expanded ? body.implicitHeight + Theme.space3 : 0) + Theme.space3
    radius: Theme.radiusMd
    color: Theme.bgSecondary
    border.width: 1
    border.color: Theme.borderSubtle
    clip: true

    Behavior on implicitHeight {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space3
        spacing: Theme.space3

        RowLayout {
            id: header
            Layout.fillWidth: true
            spacing: Theme.space2

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space1

                Label {
                    Layout.fillWidth: true
                    text: root.title
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeMd
                    font.bold: true
                    elide: Text.ElideRight
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.subtitle.length > 0
                    text: root.subtitle
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSizeXs
                    elide: Text.ElideRight
                }
            }

            SecondaryButton {
                Layout.fillWidth: false
                Layout.preferredWidth: 88
                text: root.expanded ? I18n.t("collapse") : I18n.t("expand")
                onClicked: root.expanded = !root.expanded
            }
        }

        ColumnLayout {
            id: body
            Layout.fillWidth: true
            visible: root.expanded
            spacing: Theme.space2
            opacity: root.expanded ? 1 : 0

            Behavior on opacity {
                NumberAnimation { duration: 160 }
            }
        }
    }
}
