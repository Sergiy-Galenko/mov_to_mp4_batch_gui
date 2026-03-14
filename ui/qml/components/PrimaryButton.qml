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

    background: Rectangle {
        radius: Theme.radiusInput
        border.width: 0
        scale: control.down ? 0.985 : 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: control.enabled ? (control.hovered ? Theme.accentHover : Theme.accent) : Theme.disabledBg }
            GradientStop { position: 1.0; color: control.enabled ? Theme.accent2 : Theme.disabledBg }
        }

        Behavior on scale { NumberAnimation { duration: 120 } }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? "#FFFFFF" : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.DemiBold
        font.pixelSize: 12
        elide: Text.ElideRight
        clip: true
    }
}
