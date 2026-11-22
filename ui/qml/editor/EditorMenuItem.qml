import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

MenuItem {
    id: control
    property string iconName: ""
    readonly property color foreground: enabled ? EditorTheme.textPrimary : EditorTheme.textDisabled

    leftPadding: 12
    rightPadding: 12
    font.family: Theme.bodyFont
    font.pixelSize: EditorTheme.fontSize

    contentItem: RowLayout {
        spacing: 10
        AppIcon {
            name: control.iconName
            iconColor: control.foreground
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            Layout.alignment: Qt.AlignVCenter
        }
        Label {
            text: control.text
            font: control.font
            color: control.foreground
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
        }
    }
}
