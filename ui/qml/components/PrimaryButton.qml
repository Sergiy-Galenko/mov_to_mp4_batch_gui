import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Button {
    id: control
    implicitHeight: Theme.buttonHeight
    implicitWidth: Math.max(104, contentItem.implicitWidth + 28)
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    hoverEnabled: true
    font.weight: Font.DemiBold
    opacity: enabled ? 1 : 0.72

    background: Rectangle {
        id: bgRect
        property color startColor: !control.enabled ? Theme.disabledBg : control.down ? Theme.accent2 : control.hovered ? Theme.accentHover : Theme.accent
        property color endColor: !control.enabled ? Theme.disabledBg : control.down ? Theme.accent : Theme.accent2
        radius: Theme.radiusInput
        border.width: 0
        scale: control.down ? 0.982 : control.hovered ? 1.01 : 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: bgRect.startColor }
            GradientStop { position: 1.0; color: bgRect.endColor }
        }

        Behavior on startColor { ColorAnimation { duration: 120 } }
        Behavior on endColor { ColorAnimation { duration: 120 } }
        Behavior on scale { NumberAnimation { duration: 120 } }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.width: control.activeFocus ? 1 : 0
            border.color: Theme.focusRing
        }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? "#FFFFFF" : Theme.disabledText
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.weight: Font.DemiBold
        font.pixelSize: 13
        elide: Text.ElideRight
        clip: true
    }
}
