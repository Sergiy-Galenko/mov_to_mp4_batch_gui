import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: control
    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(76, contentItem.implicitWidth + 16)
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    hoverEnabled: true
    font.weight: Font.Medium

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent"
        border.width: 1
        border.color: control.hovered ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.muted : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.Medium
        font.pixelSize: 12
        elide: Text.ElideRight
        clip: true
    }
}
