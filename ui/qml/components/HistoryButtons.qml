import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

RowLayout {
    id: root
    property var history
    property var targetWindow
    readonly property bool textEditing: targetWindow && targetWindow.activeFocusItem
        && typeof targetWindow.activeFocusItem.undo === "function"
    spacing: 4
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
    AppButton {
        objectName: "undoButton"
        text: "↶"
        enabled: !!root.history && root.history.canUndo
        Accessible.name: I18n.t("history.undo")
        ToolTip.visible: hovered
        ToolTip.text: I18n.t("history.undo")
        onClicked: root.history.undo()
    }
    AppButton {
        objectName: "redoButton"
        text: "↷"
        enabled: !!root.history && root.history.canRedo
        Accessible.name: I18n.t("history.redo")
        ToolTip.visible: hovered
        ToolTip.text: I18n.t("history.redo")
        onClicked: root.history.redo()
    }
}
