import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"
Button {
    id: control
    property string iconName: ""
    property string variant: primary ? "primary" : iconOnly ? "icon" : checked ? "toggle" : "secondary"
    property bool primary: false
    property bool iconOnly: false
    property string hint: text
    property string shortcut: ""
    readonly property bool isPrimary: variant === "primary"
    readonly property bool isDanger: variant === "danger"
    readonly property bool isSegmented: variant === "segmented"
    readonly property bool isGhost: variant === "ghost" || variant === "icon" || variant === "tab"
    readonly property bool selected: checked || highlighted
    readonly property color foreground: !enabled ? EditorTheme.textDisabled
        : isPrimary ? EditorTheme.textPrimary
        : isDanger ? EditorTheme.danger : EditorTheme.textPrimary
    implicitHeight: isPrimary ? EditorTheme.primaryHeight : EditorTheme.controlHeight
    implicitWidth: iconOnly ? implicitHeight : contentRow.implicitWidth + leftPadding + rightPadding
    leftPadding: iconOnly ? 6 : 10
    rightPadding: iconOnly ? 6 : 10
    topPadding: 4
    bottomPadding: 4
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.family: Theme.bodyFont
    font.pixelSize: EditorTheme.fontSize
    Accessible.name: hint || text
    ToolTip.visible: hovered && (iconOnly || shortcut.length > 0)
    ToolTip.text: shortcut.length > 0 ? (hint || text) + " · " + shortcut : (hint || text)
    ToolTip.delay: 450
    background: Rectangle {
        radius: EditorTheme.radiusControl
        color: !control.enabled ? EditorTheme.bgElevated
            : control.down ? (control.isPrimary ? EditorTheme.accentPressed : EditorTheme.bgHover)
            : control.isPrimary ? EditorTheme.accent
            : control.selected ? (control.variant === "tab" ? EditorTheme.bgPanel : EditorTheme.bgHover)
            : control.hovered ? EditorTheme.bgHover
            : control.isGhost || control.isSegmented ? "transparent" : EditorTheme.bgElevated
        border.width: control.variant === "tab" ? 0 : (control.isGhost && !control.selected ? 0 : 1)
        border.color: control.isDanger ? EditorTheme.danger
            : control.selected ? EditorTheme.accent : EditorTheme.borderSubtle
        Rectangle {
            visible: control.variant === "tab" && control.selected
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            height: 2; color: EditorTheme.accent
        }
        Rectangle {
            visible: control.visualFocus
            anchors.fill: parent; anchors.margins: -2
            radius: EditorTheme.radiusControl + 2
            color: "transparent"; border.width: 2; border.color: EditorTheme.accentHover
        }
        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }
    contentItem: RowLayout {
        id: contentRow
        spacing: iconName.length > 0 && !iconOnly ? 8 : 0
        AppIcon { visible: control.iconName.length > 0; name: control.iconName; iconColor: control.foreground; strokeWidth: 1.75; Layout.preferredWidth: 16; Layout.preferredHeight: 16; Layout.alignment: Qt.AlignVCenter }
        Label { visible: !control.iconOnly; text: control.text; font: control.font; color: control.foreground; elide: Text.ElideNone; wrapMode: Text.NoWrap; Layout.alignment: Qt.AlignVCenter }
    }
}
