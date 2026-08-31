import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

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
    property int itemIndex: -1

    signal selectedRequested(string path, int modifiers)
    signal retryRequested(string path)
    signal skipRequested(string path)
    signal removeRequested(string path)
    signal quickConvertRequested(string path, string name, string mediaType, int itemIndex)
    signal moveRequested(string path, int targetIndex)
    signal openOutputRequested(string path)

    width: 210
    height: 230
    radius: Theme.radiusMd
    color: selected ? Theme.selectionBackground : mouse.containsMouse ? Theme.overlayHover : Theme.panelBackground
    border.width: selected ? 2 : 1
    border.color: selected ? Theme.accentPrimary : (mouse.containsMouse ? Theme.borderStrong : Theme.borderMuted)
    clip: true

    function fileExtension() {
        var name = fileName || filePath
        var dot = name.lastIndexOf(".")
        return dot >= 0 ? name.slice(dot + 1).toUpperCase() : String(mediaType || "FILE").toUpperCase()
    }

    function statusText() {
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

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(event) {
            if (event.button === Qt.RightButton)
                cardMenu.open()
            else
                root.selectedRequested(root.filePath, event.modifiers)
        }
        onDoubleClicked: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Thumbnail / Media Preview area
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 128
            color: Theme.panelSecondary
            clip: true

            Image {
                anchors.fill: parent
                source: root.thumbnailSource
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                visible: source.toString().length > 0
            }

            AppIcon {
                anchors.centerIn: parent
                visible: root.thumbnailSource.length === 0
                name: root.mediaType === "video" ? "film" : (root.mediaType === "audio" ? "music" : (root.mediaType === "image" ? "image" : "file"))
                iconColor: Theme.textMuted
                width: 42
                height: 42
            }

            // Top-left Checkbox
            AppCheckBox {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 6
                checked: root.selected
                onToggled: if (checked !== root.selected) root.selectedRequested(root.filePath, Qt.ControlModifier)
            }

            // Top-right Format Badge
            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 6
                height: 20
                width: badgeLabel.implicitWidth + 10
                radius: Theme.radiusSm
                color: Theme.panelBackground
                opacity: 0.92
                Label {
                    id: badgeLabel
                    anchors.centerIn: parent
                    text: root.fileExtension()
                    color: Theme.textPrimary
                    font.family: Theme.monoFont
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
            }

            // Bottom-right Duration / Size
            Rectangle {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 6
                visible: root.durationText.length > 0 && root.durationText !== "—"
                height: 18
                width: durLabel.implicitWidth + 8
                radius: Theme.radiusSm
                color: "#000000"
                opacity: 0.75
                Label {
                    id: durLabel
                    anchors.centerIn: parent
                    text: root.durationText
                    color: "#FFFFFF"
                    font.family: Theme.monoFont
                    font.pixelSize: 10
                }
            }
        }

        // Progress bar line if processing or completed
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 3
            color: Theme.borderMuted
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * Math.max(0, Math.min(1, root.progress))
                color: Theme.statusColor(root.status)
            }
        }

        // Card info body
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 8
            spacing: 2

            Label {
                Layout.fillWidth: true
                text: root.fileName
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeSm
                font.weight: Font.DemiBold
                elide: Text.ElideMiddle
                maximumLineCount: 1
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                StatusPill {
                    text: root.statusText()
                    accent: Theme.statusColor(root.status)
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: root.sizeText || ""
                    color: Theme.textMuted
                    font.family: Theme.monoFont
                    font.pixelSize: 11
                }
            }

            // Hover quick actions row
            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                visible: mouse.containsMouse

                AppIconButton {
                    visible: root.status === "failed"
                    iconName: "refresh"
                    accessibleLabel: I18n.t("retry")
                    onClicked: root.retryRequested(root.filePath)
                }
                AppIconButton {
                    visible: root.status === "success" && root.outputPath.length > 0
                    iconName: "folder"
                    accessibleLabel: I18n.t("open_output")
                    onClicked: root.openOutputRequested(root.filePath)
                }
                AppIconButton {
                    iconName: "sliders"
                    accessibleLabel: I18n.t("quick_convert")
                    onClicked: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex)
                }
                Item { Layout.fillWidth: true }
                AppIconButton {
                    iconName: "close"
                    accessibleLabel: I18n.t("remove")
                    onClicked: root.removeRequested(root.filePath)
                }
            }
        }
    }

    Menu {
        id: cardMenu
        MenuItem { text: I18n.t("quick_convert"); onTriggered: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex) }
        MenuItem { text: I18n.t("convert_this_file"); onTriggered: root.quickConvertRequested(root.filePath, root.fileName, root.mediaType, root.itemIndex) }
        MenuItem { text: I18n.t("open_output"); enabled: root.status === "success" && root.outputPath.length > 0; onTriggered: root.openOutputRequested(root.filePath) }
        MenuItem { text: I18n.t("retry"); visible: root.status === "failed"; onTriggered: root.retryRequested(root.filePath) }
        MenuSeparator {}
        MenuItem { text: I18n.t("remove"); onTriggered: root.removeRequested(root.filePath) }
    }
}
