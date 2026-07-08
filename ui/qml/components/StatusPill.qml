import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

Rectangle {
    property alias text: pillText.text
    property color accent: Theme.textSecondary
    property int maxWidth: 120
    Layout.maximumWidth: maxWidth
    Layout.preferredHeight: 24
    Layout.preferredWidth: Math.min(maxWidth, pillText.implicitWidth + 18)
    radius: Theme.radiusPill
    color: Theme.subtleFill
    border.width: 1
    border.color: Theme.borderSubtle
    Label {
        id: pillText
        anchors.centerIn: parent
        width: parent.width - 14
        elide: Text.ElideRight
        color: parent.accent
        font.family: Theme.monoFont
        font.pixelSize: Theme.fontMeta
        horizontalAlignment: Text.AlignHCenter
    }
}
