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
    implicitHeight: compact ? 160 : 340
    width: implicitWidth
    height: implicitHeight
    radius: Theme.radiusLg
    color: dragging ? Theme.accentSoft : Theme.bgElevated
    border.width: 1
    border.color: dragging ? Theme.accent : Theme.borderSubtle
    scale: dragging ? 1.02 : 1

    Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutSine } }
    Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutSine } }
    Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }

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
        spacing: Theme.space4

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "📥"
            font.pixelSize: root.compact ? 48 : 82
            opacity: root.dragging ? 1.0 : 0.8
            Behavior on opacity { NumberAnimation { duration: 150 } }
            Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBounce } }
            scale: root.dragging ? 1.1 : 1.0
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.space1

            Label {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: "Перетягни файли або папку сюди"
                color: Theme.textPrimary
                font.pixelSize: root.compact ? Theme.fontSizeLg : Theme.fontDisplay
                font.family: Theme.displayFont
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: "Підтримуються відео, аудіо, зображення та субтитри"
                color: Theme.textSecondary
                font.pixelSize: root.compact ? Theme.fontSizeSm : Theme.fontSizeMd
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.space3
            
            PrimaryButton {
                Layout.preferredWidth: 200
                Layout.preferredHeight: 44
                text: "Обрати файли..."
                font.pixelSize: Theme.fontSizeMd
                font.bold: true
                onClicked: root.clicked()
            }
            
            SecondaryButton {
                Layout.preferredWidth: 200
                Layout.preferredHeight: 44
                text: "📖 Як користуватися"
                font.pixelSize: Theme.fontSizeMd
                onClicked: tutorialPopup.open()
            }
        }
    }
}
