import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

AppButton {
    id: modeButton
    property string mode: ""
    Layout.fillWidth: false
    Layout.preferredWidth: Math.max(96, implicitWidth)
    Layout.preferredHeight: 36
    hoverEnabled: true
    highlighted: root.topModeActive(modeButton.mode)
    onClicked: root.openTopMode(mode)

}
