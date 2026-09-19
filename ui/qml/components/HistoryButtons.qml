import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Rectangle {
    id: root
    property var history
    property var targetWindow
    readonly property bool textEditing: targetWindow && targetWindow.activeFocusItem
        && typeof targetWindow.activeFocusItem.undo === "function"
    implicitWidth: actions.implicitWidth + 8
    implicitHeight: actions.implicitHeight + 8
    radius: 16
    color: Theme.panelBackground
    border.width: 1
    border.color: Theme.borderMuted
    Shortcut {
        sequences: [StandardKey.Undo]
        enabled: root.targetWindow && root.targetWindow.active && !root.textEditing
        onActivated: if (root.history) root.history.undo()
    }
    Shortcut {
        sequences: [StandardKey.Redo]
        enabled: root.targetWindow && root.targetWindow.active && !root.textEditing
        onActivated: if (root.history) root.history.redo()
    }
    Row {
        id: actions
        anchors.centerIn: parent
        spacing: 8
        ToolbarIconButton {
            objectName: "undoButton"
            iconName: "undo"
            enabled: !!root.history && root.history.canUndo
            accessibleLabel: I18n.t("history.undo")
            onClicked: root.history.undo()
        }
        ToolbarIconButton {
            objectName: "redoButton"
            iconName: "redo"
            enabled: !!root.history && root.history.canRedo
            accessibleLabel: I18n.t("history.redo")
            onClicked: root.history.redo()
        }
    }
}
