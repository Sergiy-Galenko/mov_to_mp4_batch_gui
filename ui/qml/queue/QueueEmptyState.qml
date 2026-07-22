import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Item {
    id: root
    property bool dragging: dropArea.containsDrag
    signal filesDropped(var urls)
    signal addFilesRequested()
    signal addFolderRequested()
    objectName: "queueDropZone"
    implicitHeight: 330

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

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 520)
        height: 236
        color: root.dragging ? Theme.accentSoft : Theme.transparent
        border.width: 1
        border.color: root.dragging ? Theme.accentPrimary : Theme.borderDefault
        radius: Theme.radiusMd

        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: Theme.space3
            AppIcon { Layout.alignment: Qt.AlignHCenter; name: "folder"; iconColor: root.dragging ? Theme.accentPrimary : Theme.textMuted; width: 36; height: 36 }
            Label { Layout.fillWidth: true; text: I18n.t("drop_start"); color: Theme.textPrimary; font.pixelSize: Theme.fontSizeLg; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
            Label { Layout.fillWidth: true; text: I18n.t("drop_choose"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; horizontalAlignment: Text.AlignHCenter }
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.space2
                Button { text: I18n.t("add_files"); onClicked: root.addFilesRequested() }
                Button { text: I18n.t("add_folder"); onClicked: root.addFolderRequested() }
            }
            Label { Layout.fillWidth: true; text: I18n.t("formats_hint"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
        }
    }
}
