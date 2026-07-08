import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

Button {
    id: modeButton
    property string mode: ""
    Layout.fillWidth: false
    Layout.preferredWidth: Math.max(96, modeLabel.implicitWidth + 22)
    Layout.preferredHeight: 36
    hoverEnabled: true
    onClicked: root.openTopMode(mode)

    background: Rectangle {
        radius: Theme.radiusButton
        color: root.topModeActive(modeButton.mode) ? Theme.accentSoft : (modeButton.hovered ? Theme.overlayHover : Theme.bgElevated)
        border.width: 1
        border.color: root.topModeActive(modeButton.mode) ? Theme.accent : Theme.borderSubtle
    }

    contentItem: Label {
        id: modeLabel
        text: modeButton.text
        color: root.topModeActive(modeButton.mode) ? Theme.textPrimary : Theme.textSecondary
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: Theme.fontSizeSm
        font.bold: root.topModeActive(modeButton.mode)
        elide: Text.ElideRight
    }
}
