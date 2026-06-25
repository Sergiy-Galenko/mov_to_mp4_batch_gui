import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Item {
    id: cell
    property string label: ""
    property string value: ""
    property color accent: Theme.textSecondary

    Layout.fillWidth: true
    Layout.preferredHeight: 18

    RowLayout {
        anchors.fill: parent
        spacing: 6

        Label {
            text: cell.label + ":"
            color: Theme.textMuted
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
        }

        Label {
            Layout.fillWidth: true
            text: cell.value
            color: cell.accent
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
            elide: Text.ElideRight
        }
    }
}
