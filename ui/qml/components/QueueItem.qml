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
    property string predictedSizeText: ""
    property string compressionText: ""
    property int exitCode: -1
    property bool hasOverride: false
    property bool selected: false
    property bool highLoadMode: false
    property bool showThumbnail: true
    property bool showMetrics: true
    property bool showActions: true
    property real shimmerPhase: 0
    property int itemIndex: -1

    signal selectedRequested(string path, int modifiers)
    signal moveRequested(string path, int targetIndex)
    signal retryRequested(string path)
    signal skipRequested(string path)
    signal removeRequested(string path)
    signal overrideRequested(string path)
    signal quickConvertRequested(string path, string name, string mediaType)

    function canonicalStatus() {
        if (status === "success")
            return "done"
        if (status === "running" || status === "paused")
            return "processing"
        if (status === "queued" || status === "ready" || status === "analyzing")
            return "pending"
        return status
    }

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

    function iconText() {
        var state = canonicalStatus()
        if (state === "done") return "\u2713"
        if (state === "failed") return "\u2715"
        if (state === "skipped") return "-"
        if (state === "processing") return "\u25CF"
        return mediaType === "audio" ? "A" : mediaType === "image" ? "I" : mediaType === "subtitle" ? "S" : "V"
    }

    function topErrorLines() {
        var text = errorText || ""
        var lines = text.split(/\r?\n/).filter(function(line) { return line.trim().length > 0 })
        return lines.slice(Math.max(0, lines.length - 5)).join("\n") || text
    }

    function fallbackExtension() {
        if (mediaType === "image") return "jpg"
        if (mediaType === "audio") return "mp3"
        if (mediaType === "subtitle") return "srt"
        return "mp4"
    }

    function outputExtension() {
        var path = root.outputPath || ""
        var dot = path.lastIndexOf(".")
        if (dot >= 0 && dot < path.length - 1)
            return path.slice(dot + 1).toLowerCase()
        return fallbackExtension()
    }

    width: ListView.view ? ListView.view.width : 720
    implicitHeight: details.visible ? 174 : 126
    radius: Theme.radiusMd
    color: selected ? Theme.selection : (mouse.containsMouse ? Theme.bgElevated : Theme.bgSecondary)
    border.width: 1
    border.color: selected ? Theme.accent : Theme.borderSubtle
    opacity: canonicalStatus() === "pending" ? 0.76 : 1
    clip: true
    layer.enabled: false
    Drag.active: dragHandler.active
    Drag.source: root
    Drag.hotSpot.x: width / 2
    Drag.hotSpot.y: height / 2
    Drag.supportedActions: Qt.MoveAction

    Behavior on color {
        enabled: !highLoadMode
        ColorAnimation { duration: 120 }
    }

    DragHandler {
        id: dragHandler
        target: null
        acceptedButtons: Qt.LeftButton
    }

    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.source && drop.source.filePath && drop.source.filePath !== root.filePath) {
                root.moveRequested(drop.source.filePath, root.itemIndex)
                drop.acceptProposedAction()
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        color: canonicalStatus() === "done" ? Theme.statusSuccess
             : canonicalStatus() === "failed" ? Theme.statusError
             : canonicalStatus() === "processing" ? Theme.statusRunning
             : Theme.transparent
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouseEvent) {
            if (mouseEvent.button === Qt.RightButton)
                root.quickConvertRequested(root.filePath, root.fileName, root.mediaType)
            else
                root.selectedRequested(root.filePath, mouseEvent.modifiers)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space3
        anchors.leftMargin: Theme.space4
        spacing: Theme.space2

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: "::"
                color: Theme.textMuted
                font.family: Theme.monoFont
                font.pixelSize: 18
                Layout.preferredWidth: 18
                horizontalAlignment: Text.AlignHCenter
            }

            Rectangle {
                visible: root.showThumbnail
                Layout.preferredWidth: 38
                Layout.preferredHeight: 38
                radius: Theme.radiusSm
                color: Theme.input
                border.width: 1
                border.color: Theme.borderSubtle
                clip: true

                Image {
                    anchors.fill: parent
                    anchors.margins: 1
                    source: root.thumbnailSource
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: source.toString().length > 0
                    cache: true
                }

                Label {
                    anchors.centerIn: parent
                    visible: root.thumbnailSource.length === 0
                    text: root.iconText()
                    color: Theme.statusColor(root.status)
                    font.family: Theme.monoFont
                    font.pixelSize: 15
                    font.bold: true
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        Layout.fillWidth: true
                        text: root.fileName
                        color: canonicalStatus() === "skipped" ? Theme.textMuted : Theme.textPrimary
                        font.family: Theme.bodyFont
                        font.pixelSize: Theme.fontSizeMd
                        font.strikeout: canonicalStatus() === "skipped"
                        elide: Text.ElideMiddle
                    }

                    Label {
                        visible: root.showMetrics
                        text: (root.mediaType || "media").toUpperCase() + " -> " + root.outputExtension()
                        color: Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                    }

                    Label {
                        visible: root.showMetrics
                        text: root.sizeText + (root.durationText ? " / " + root.durationText : "")
                        color: Theme.textDisabled
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: Theme.borderSubtle
                }
            }

            StatusBadge {
                Layout.preferredWidth: 96
                status: root.status
                label: root.statusLabel()
            }
        }

        ProgressRow {
            Layout.fillWidth: true
            visible: canonicalStatus() !== "pending"
            value: canonicalStatus() === "done" ? 1 : root.progress
            active: canonicalStatus() === "processing"
            highLoadMode: root.highLoadMode
            shimmerPhase: root.shimmerPhase
            fillColor: canonicalStatus() === "done" ? Theme.accentSuccess
                     : canonicalStatus() === "failed" ? Theme.accentError
                     : canonicalStatus() === "skipped" ? Theme.textDisabled
                     : Theme.accentPrimary
            etaText: root.etaText ? I18n.t("eta") + " " + root.etaText : ""
            speedText: root.speedText || ""
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: Math.round(Math.max(0, Math.min(root.progress, 1)) * 100) + "%"
                color: Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: false
            }

            Label {
                text: root.etaText ? I18n.t("eta") + " " + root.etaText : I18n.t("eta") + " --"
                color: Theme.accentWarn
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: false
            }

            Label {
                text: root.speedText || "--"
                color: Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: false
            }

            Label {
                text: root.predictedSizeText ? I18n.t("predicted_size") + " " + root.predictedSizeText : ""
                color: Theme.textDisabled
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: root.showMetrics && root.predictedSizeText.length > 0 && canonicalStatus() !== "processing"
            }

            Label {
                text: root.compressionText ? I18n.t("compression") + " " + root.compressionText : ""
                color: Theme.statusSuccess
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: root.showMetrics && root.compressionText.length > 0
            }

            Item { Layout.fillWidth: true }

            GhostButton {
                text: root.hasOverride ? I18n.t("override") + " *" : I18n.t("override")
                visible: root.showActions
                Layout.fillWidth: false
                flat: true
                onClicked: root.overrideRequested(root.filePath)
            }
            GhostButton {
                text: I18n.t("retry")
                visible: root.showActions && canonicalStatus() === "failed"
                Layout.fillWidth: false
                flat: true
                onClicked: root.retryRequested(root.filePath)
            }
            GhostButton {
                text: I18n.t("skip")
                visible: root.showActions
                enabled: canonicalStatus() === "processing"
                Layout.fillWidth: false
                flat: true
                onClicked: root.skipRequested(root.filePath)
            }
            GhostButton {
                text: I18n.t("remove")
                visible: root.showActions
                Layout.fillWidth: false
                flat: true
                onClicked: root.removeRequested(root.filePath)
            }
        }

        Rectangle {
            id: details
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            visible: canonicalStatus() === "failed" && root.selected
            radius: Theme.radiusSm
            color: Theme.input
            border.width: 1
            border.color: Theme.dangerSoft

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 10

                Label {
                    Layout.fillWidth: true
                    text: I18n.t("exit_code") + " " + root.exitCode + " | " + root.topErrorLines()
                    color: Theme.textSecondary
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideRight
                }

                SecondaryButton { Layout.fillWidth: false; text: I18n.t("retry"); onClicked: root.retryRequested(root.filePath) }
                SecondaryButton { Layout.fillWidth: false; text: I18n.t("change"); onClicked: root.overrideRequested(root.filePath) }
                SecondaryButton { Layout.fillWidth: false; text: I18n.t("skip"); onClicked: root.skipRequested(root.filePath) }
            }
        }
    }
}
