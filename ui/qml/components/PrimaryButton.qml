import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: control
    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(96, contentItem.implicitWidth + 24)
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    hoverEnabled: true
    font.weight: Font.DemiBold
    opacity: enabled ? 1 : 0.65

    background: Rectangle {
        radius: Theme.radiusSm
        color: !control.enabled ? Theme.disabledBg : control.down ? Theme.accentPressed : control.hovered ? Theme.accentHover : Theme.accent
        border.width: 1
        border.color: control.activeFocus ? Theme.focusRing : Theme.transparent

        Behavior on color { ColorAnimation { duration: 120 } }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? Theme.textOnAccent : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.DemiBold
        font.pixelSize: Theme.fontSizeSm
        elide: Text.ElideRight
        clip: true
    }
}
