import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"
Button {
    id: control
    property string iconName: ""
    property bool primary: false
    property bool iconOnly: false
    property string hint: text
    implicitHeight: EditorTheme.controlHeight
    implicitWidth: iconOnly ? implicitHeight : label.implicitWidth + (iconName ? 22 : 0) + 20
    padding: 6
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.family: Theme.bodyFont
    font.pixelSize: EditorTheme.fontSize
    Accessible.name: text || hint
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.text: hint
    ToolTip.delay: 500
    background: Rectangle {
        radius: 5
        color: !control.enabled ? EditorTheme.panel : control.down ? "#184f86"
            : control.primary || control.checked || control.highlighted ? EditorTheme.accent
            : control.hovered ? EditorTheme.hover : EditorTheme.raised
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? "#ffffff" : control.checked || control.primary ? EditorTheme.accent : EditorTheme.border
        opacity: control.enabled ? 1 : 0.55
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    contentItem: RowLayout {
        spacing: 6
        AppIcon { visible: control.iconName.length > 0; name: control.iconName; iconColor: control.enabled ? EditorTheme.text : EditorTheme.muted; Layout.preferredWidth: 16; Layout.preferredHeight: 16; Layout.alignment: Qt.AlignHCenter }
        Label { id: label; visible: !control.iconOnly; text: control.text; font: control.font; color: control.enabled ? EditorTheme.text : EditorTheme.muted; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
    }
}
