import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

CheckBox {
    id: control
    Layout.fillWidth: true
    implicitHeight: Math.max(32, contentItem.implicitHeight + 8)
    implicitWidth: contentItem.implicitWidth + indicator.width + 20
    leftPadding: 0; rightPadding: indicator.width + 12
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true
    opacity: enabled ? 1 : 0.5
    indicator: Rectangle {
        x: control.width - width
        y: (control.height - height) / 2
        width: Theme.isMac ? 38 : 40
        height: 22
        radius: height / 2
        color: control.checked ? Theme.accent : Theme.panelSecondary
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? Theme.focusRing : control.checked ? Theme.accent : Theme.borderDefault
        Rectangle {
            x: control.checked ? parent.width - width - 2 : 2
            y: 2
            width: 18; height: 18; radius: 9
            color: control.checked ? Theme.textOnAccent : Theme.textSecondary
            Behavior on x { enabled: !Theme.reducedMotion; NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
        Behavior on color { enabled: !Theme.reducedMotion; ColorAnimation { duration: 120 } }
    }
    contentItem: Label {
        text: control.text
        color: Theme.textPrimary
        font.family: Theme.bodyFont
        font.pixelSize: Theme.fontSizeSm
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
}
