import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

Label {
    id: root
    property string helpText: ""
    color: Theme.textSecondary
    font.family: Theme.bodyFont
    font.pixelSize: Theme.fontSizeSm
    Layout.fillWidth: true
    MouseArea {
        id: helpHover
        anchors.fill: parent
        hoverEnabled: root.helpText.length > 0
    }
    ToolTip.visible: helpHover.containsMouse && helpText.length > 0
    ToolTip.delay: 450
    ToolTip.text: helpText
}
