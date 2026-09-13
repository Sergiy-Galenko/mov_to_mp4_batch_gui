import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"

Rectangle {
    id: root
    property string fileName: ""
    property string filePath: ""
    property string mediaType: ""
    property string status: "queued"
    property string errorText: ""
    property string outputPath: ""
    property string durationText: ""
    property string sizeText: ""
    property string thumbnailSource: ""
    property real progress: 0
    property string etaText: ""
    property string speedText: ""
    property bool selected: false
    property bool compact: false
    property int itemIndex: -1

    signal selectedRequested(string path, int modifiers)
    signal retryRequested(string path)
    signal skipRequested(string path)
    signal removeRequested(string path)
    signal quickConvertRequested(string path, string name, string mediaType, int itemIndex)
    signal moveRequested(string path, int targetIndex)
    signal openOutputRequested(string path)

    implicitHeight: compact ? 56 : 64
    color: selected ? Theme.selectionBackground : mouse.containsMouse ? Theme.overlayHover : Theme.panelBackground
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: fileName + ", " + statusLabel()
    Accessible.selected: selected
    Accessible.onPressAction: root.selectedRequested(root.filePath, Qt.NoModifier)
    Keys.onSpacePressed: root.selectedRequested(root.filePath, Qt.ControlModifier)
    Keys.onReturnPressed: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex)
    Keys.onEnterPressed: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex)
    border.width: selected || activeFocus ? 1 : 0
    border.color: activeFocus ? Theme.focusRing : selected ? Theme.accentPrimary : Theme.transparent
    clip: true
    Drag.active: dragHandler.active
    Drag.source: root
    Drag.hotSpot.x: width / 2
    Drag.hotSpot.y: height / 2
    Drag.supportedActions: Qt.MoveAction

    function statusLabel() {
        if (status === "queued") return I18n.t("status.pending")
        if (status === "analyzing") return I18n.t("status.analyzing")
        if (status === "ready") return I18n.t("status.ready")
        if (status === "running") return I18n.t("status.processing")
        if (status === "paused") return I18n.t("status.paused")
        if (status === "success") return I18n.t("status.done")
        if (status === "failed") return I18n.t("status.failed")
        if (status === "skipped") return I18n.t("status.skipped")
        if (status === "cancelled") return I18n.t("status.cancelled")
        return status
    }

    function fileExtension() {
        var name = fileName || filePath
        var dot = name.lastIndexOf(".")
        return dot >= 0 ? name.slice(dot + 1).toUpperCase() : String(mediaType || "FILE").toUpperCase()
    }

    DragHandler { id: dragHandler; target: null; acceptedButtons: Qt.LeftButton }

    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.source && drop.source.filePath && drop.source.filePath !== root.filePath) {
                root.moveRequested(drop.source.filePath, root.itemIndex)
                drop.acceptProposedAction()
            }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(event) {
            root.forceActiveFocus()
            if (event.button === Qt.RightButton)
                rowMenu.open()
            else
                root.selectedRequested(root.filePath, event.modifiers)
        }
        onDoubleClicked: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space2
        anchors.rightMargin: Theme.space2
        spacing: Theme.space2

        AppCheckBox {
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            checked: root.selected
            Accessible.name: I18n.t("select_file") + ": " + root.fileName
            onToggled: if (checked !== root.selected) root.selectedRequested(root.filePath, Qt.ControlModifier)
        }

        Rectangle {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            radius: Theme.radiusSm
            color: Theme.panelSecondary
            border.width: 1
            border.color: Theme.borderMuted
            clip: true
            Image { id: thumbnail; anchors.fill: parent; source: root.thumbnailSource; sourceSize: Qt.size(64, 64); fillMode: Image.PreserveAspectCrop; asynchronous: true; visible: source.toString().length > 0 }
            AppIcon { anchors.centerIn: parent; visible: thumbnail.status !== Image.Ready; name: root.mediaType === "video" ? "film" : root.mediaType === "audio" ? "music" : root.mediaType === "image" ? "image" : "file"; iconColor: Theme.textSecondary; width: 16; height: 16 }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            spacing: 2
            Label {
                Layout.fillWidth: true
                text: root.fileName
                color: root.status === "skipped" ? Theme.textMuted : Theme.textPrimary
                font.pixelSize: Theme.fontSizeSm
                font.weight: root.selected ? Font.DemiBold : Font.Normal
                font.strikeout: root.status === "skipped"
                elide: Text.ElideMiddle
            }
            Label {
                Layout.fillWidth: true
                text: root.filePath
                color: Theme.textMuted
                font.family: Theme.monoFont
                font.pixelSize: 11
                elide: Text.ElideMiddle
            }
        }

        Label {
            visible: !root.compact
            Layout.preferredWidth: 64
            text: root.fileExtension()
            color: Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
        }

        Label {
            visible: !root.compact
            Layout.preferredWidth: 140
            text: (root.sizeText || "—") + (root.durationText ? " · " + root.durationText : "")
            color: Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
        }

        ColumnLayout {
            visible: !root.compact
            opacity: root.status === "running" || root.status === "paused" ? 1 : 0
            Layout.preferredWidth: 112
            Layout.minimumWidth: 112
            Layout.maximumWidth: 112
            Layout.fillWidth: false
            spacing: 3
            AppProgressBar { Layout.fillWidth: true; value: Math.max(0, Math.min(1, root.progress)) }
            Label { Layout.fillWidth: true; text: root.speedText || Math.round(root.progress * 100) + "%"; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: 10; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
        }

        Rectangle {
            visible: root.compact && (root.status === "running" || root.status === "paused")
            Layout.preferredWidth: 42
            Layout.preferredHeight: 24
            color: Theme.transparent
            Label { anchors.centerIn: parent; text: Math.round(root.progress * 100) + "%"; color: Theme.textSecondary; font.pixelSize: Theme.fontMeta }
        }

        StatusBadge {
            Layout.preferredWidth: 112
            status: root.status
            label: root.statusLabel()
        }

        AppIconButton {
            Layout.preferredWidth: 32
            iconName: "more"
            accessibleLabel: I18n.t("quick_convert")
            onClicked: rowMenu.open()
        }
    }

    Menu {
        id: rowMenu
        width: 188
        padding: 4
        background: Rectangle { color: Theme.panelBackground; border.width: 1; border.color: Theme.borderDefault; radius: Theme.radiusMd }
        MenuItem { text: I18n.t("quick_convert"); onTriggered: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex) }
        MenuItem { text: I18n.t("retry"); enabled: root.status === "failed" || root.status === "cancelled"; onTriggered: root.retryRequested(root.filePath) }
        MenuItem { text: I18n.t("skip"); enabled: root.status === "running"; onTriggered: root.skipRequested(root.filePath) }
        MenuItem { text: I18n.t("open_output"); enabled: root.outputPath.length > 0; onTriggered: root.openOutputRequested(root.filePath) }
        MenuSeparator {}
        MenuItem { text: I18n.t("remove"); onTriggered: root.removeRequested(root.filePath) }
    }
}
