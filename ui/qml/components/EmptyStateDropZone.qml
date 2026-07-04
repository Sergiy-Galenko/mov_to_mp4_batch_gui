import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property bool compact: false
    property bool dragging: dropArea.containsDrag
    signal filesDropped(var urls)
    signal clicked()

    implicitWidth: compact ? 420 : 620
    implicitHeight: compact ? 140 : 260
    width: implicitWidth
    height: implicitHeight
    radius: Theme.radiusLg
    color: dragging ? Theme.accentSoft : Theme.bgSecondary
    border.width: 1
    border.color: dragging ? Theme.accent : Theme.borderSubtle
    scale: dragging ? 1.01 : 1

    Behavior on color { ColorAnimation { duration: 120 } }
    Behavior on border.color { ColorAnimation { duration: 120 } }
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }

    DropArea {
        id: dropArea
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.hasUrls) {
                root.filesDropped(drop.urls)
                drop.acceptProposedAction()
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - Theme.space6, 560)
        spacing: Theme.space3

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.compact ? 44 : 56
            Layout.preferredHeight: width
            radius: Theme.radiusMd
            color: Theme.bgElevated
            border.width: 1
            border.color: root.dragging ? Theme.accent : Theme.borderStrong

            Label {
                anchors.centerIn: parent
                text: "+"
                color: root.dragging ? Theme.accent : Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: root.compact ? Theme.fontSizeXl : 26
                font.bold: true
            }
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            text: I18n.t("drag_drop")
            color: Theme.textPrimary
            font.pixelSize: root.compact ? Theme.fontSizeMd : Theme.fontSizeLg
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            text: I18n.t("formats_hint")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeSm
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        SecondaryButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: false
            Layout.preferredWidth: 168
            text: I18n.t("add_files")
            onClicked: root.clicked()
        }
    }
}
