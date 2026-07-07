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
    property string smartRecommendation: ""
    property bool pinned: false
    property int priority: 0
    property int exitCode: -1
    property bool hasOverride: false
    property bool selected: false
    property bool highLoadMode: false
    property bool showThumbnail: true
    property bool showMetrics: true
    property bool showActions: true
    property bool showSize: true
    property bool showDuration: true
    property bool showCodec: true
    property bool showOutput: true
    property bool showProgress: true
    property real shimmerPhase: 0
    property int itemIndex: -1

    signal selectedRequested(string path, int modifiers)
    signal moveRequested(string path, int targetIndex)
    signal retryRequested(string path)
    signal skipRequested(string path)
    signal removeRequested(string path)
    signal overrideRequested(string path)
    signal openOutputRequested(string path)
    signal quickConvertRequested(string path, string name, string mediaType)
    signal pinnedRequested(string path)
    signal priorityRequested(string path, int priority)

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

    function topErrorLines() {
        var text = errorText || ""
        var lines = text.split(/\r?\n/).filter(function(line) { return line.trim().length > 0 })
        return lines.slice(Math.max(0, lines.length - 5)).join("\n") || text
    }

    function fallbackExtension() {
        if (mediaType === "image") return "jpg"
        if (mediaType === "audio") return "mp3"
        if (mediaType === "subtitle") return "srt"
        if (mediaType === "text") return "txt"
        return "mp4"
    }

    function outputExtension() {
        var path = root.outputPath || ""
        var dot = path.lastIndexOf(".")
        if (dot >= 0 && dot < path.length - 1)
            return path.slice(dot + 1).toLowerCase()
        return fallbackExtension()
    }

    function inputExtension() {
        var path = root.fileName || root.filePath || ""
        var slash = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"))
        if (slash >= 0)
            path = path.slice(slash + 1)
        var dot = path.lastIndexOf(".")
        if (dot >= 0 && dot < path.length - 1)
            return path.slice(dot + 1).toLowerCase()
        return fallbackExtension()
    }

    width: ListView.view ? ListView.view.width : 720
    implicitHeight: (details.visible ? 204 : (showOutput && outputPath.length > 0 ? 140 : 110)) + (smartRecommendation.length > 0 ? 24 : 0)
    radius: Theme.radiusMd
    color: selected ? Theme.selection : (mouse.containsMouse ? Theme.overlayHover : Theme.bgElevated)
    border.width: 1
    border.color: selected ? Theme.accent : (mouse.containsMouse ? Theme.borderStrong : Theme.transparent)
    opacity: canonicalStatus() === "pending" ? 0.85 : 1
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
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                radius: Theme.radiusSm
                color: Theme.input
                border.width: 0
                clip: true

                Image {
                    anchors.fill: parent
                    source: root.thumbnailSource
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: source.toString().length > 0
                    cache: true
                }

                MediaTypeIcon {
                    anchors.fill: parent
                    visible: root.thumbnailSource.length === 0
                    mediaType: root.mediaType
                    status: root.status
                    extension: root.inputExtension()
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        visible: root.pinned
                        text: "📌"
                        color: Theme.accentPrimary
                        font.pixelSize: Theme.fontMeta
                    }

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
                        visible: root.showCodec
                        text: (root.mediaType || "media").toUpperCase() + " -> " + root.outputExtension()
                        color: Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                    }

                    Label {
                        visible: root.showSize || root.showDuration
                        text: (root.showSize ? root.sizeText : "") + (root.showSize && root.showDuration && root.durationText ? " / " : "") + (root.showDuration ? root.durationText : "")
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

                Label {
                    Layout.fillWidth: true
                    visible: root.showOutput && root.outputPath.length > 0
                    text: "Output: " + root.outputPath
                    color: Theme.textSecondary
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideMiddle
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.smartRecommendation.length > 0
                    text: "🧠 " + root.smartRecommendation
                    color: Theme.accentPrimary
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideRight
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
            visible: root.showProgress && canonicalStatus() !== "pending"
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
                text: root.pinned ? "📌" : "Pin"
                visible: root.showActions
                Layout.fillWidth: false
                flat: true
                onClicked: root.pinnedRequested(root.filePath)
            }
            GhostButton {
                text: root.priority > 0 ? "⚑ " + root.priority : "⚑"
                visible: root.showActions
                Layout.fillWidth: false
                flat: true
                onClicked: root.priorityRequested(root.filePath, (root.priority + 1) % 4)
            }
            GhostButton {
                text: root.hasOverride ? I18n.t("override") + " *" : I18n.t("override")
                visible: root.showActions
                Layout.fillWidth: false
                flat: true
                onClicked: root.overrideRequested(root.filePath)
            }
            GhostButton {
                text: I18n.t("open_output")
                visible: root.showActions && root.outputPath.length > 0
                Layout.fillWidth: false
                flat: true
                onClicked: root.openOutputRequested(root.filePath)
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
