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
    property int exitCode: -1
    property bool hasOverride: false
    property bool selected: false
    property bool highLoadMode: false
    property real shimmerPhase: 0

    signal selectedRequested(string path)
    signal retryRequested(string path)
    signal skipRequested(string path)
    signal removeRequested(string path)
    signal overrideRequested(string path)

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

    width: ListView.view ? ListView.view.width : 720
    implicitHeight: details.visible ? 172 : 128
    radius: Theme.radiusPanel
    color: selected ? "#1B2637" : (mouse.containsMouse ? Theme.bgElevated : Theme.bgSurface)
    border.width: 1
    border.color: selected ? Theme.accentPrimary : Theme.bgBorder
    opacity: canonicalStatus() === "pending" ? 0.76 : 1
    clip: true
    layer.enabled: false

    Behavior on color {
        enabled: !highLoadMode
        ColorAnimation { duration: 120 }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        color: canonicalStatus() === "done" ? Theme.accentSuccess
             : canonicalStatus() === "failed" ? Theme.accentError
             : canonicalStatus() === "processing" ? Theme.accentPrimary
             : "transparent"
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        onClicked: root.selectedRequested(root.filePath)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        anchors.leftMargin: 14
        spacing: 8

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
                Layout.preferredWidth: 38
                Layout.preferredHeight: 38
                radius: 8
                color: "#10141C"
                border.width: 1
                border.color: Theme.bgBorder
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
                        font.pixelSize: 14
                        font.strikeout: canonicalStatus() === "skipped"
                        elide: Text.ElideMiddle
                    }

                    Label {
                        text: (root.mediaType || "media").toUpperCase() + " -> " + (root.outputPath ? root.outputPath.split(".").pop() : "mp4")
                        color: Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                    }

                    Label {
                        text: root.sizeText + (root.durationText ? " / " + root.durationText : "")
                        color: Theme.textMuted
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: Theme.bgBorder
                }
            }

            Rectangle {
                Layout.preferredWidth: 78
                Layout.preferredHeight: 24
                radius: Theme.radiusButton
                color: Qt.rgba(1, 1, 1, 0.03)
                border.width: 1
                border.color: Theme.statusColor(root.status)
                Label {
                    anchors.centerIn: parent
                    text: root.statusLabel()
                    color: Theme.statusColor(root.status)
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideRight
                }
            }
        }

        ShimmerBar {
            Layout.fillWidth: true
            Layout.preferredHeight: 10
            visible: canonicalStatus() !== "pending"
            value: canonicalStatus() === "done" ? 1 : root.progress
            active: canonicalStatus() === "processing"
            highLoadMode: root.highLoadMode
            shimmerPhase: root.shimmerPhase
            fillColor: canonicalStatus() === "done" ? Theme.accentSuccess
                     : canonicalStatus() === "failed" ? Theme.accentError
                     : canonicalStatus() === "skipped" ? Theme.textMuted
                     : Theme.accentPrimary
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label {
                text: Math.round(Math.max(0, Math.min(root.progress, 1)) * 100) + "%"
                color: Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: canonicalStatus() !== "pending"
            }

            Label {
                text: root.etaText ? I18n.t("eta") + " " + root.etaText : I18n.t("eta") + " --"
                color: Theme.accentWarn
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: canonicalStatus() === "processing"
            }

            Label {
                text: root.speedText || "--"
                color: Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                visible: canonicalStatus() === "processing"
            }

            Item { Layout.fillWidth: true }

            Button {
                text: root.hasOverride ? I18n.t("override") + " *" : I18n.t("override")
                flat: true
                onClicked: root.overrideRequested(root.filePath)
            }
            Button {
                text: I18n.t("retry")
                visible: canonicalStatus() === "failed"
                flat: true
                onClicked: root.retryRequested(root.filePath)
            }
            Button {
                text: I18n.t("skip")
                enabled: canonicalStatus() === "processing"
                flat: true
                onClicked: root.skipRequested(root.filePath)
            }
            Button {
                text: I18n.t("remove")
                flat: true
                onClicked: root.removeRequested(root.filePath)
            }
        }

        Rectangle {
            id: details
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            visible: canonicalStatus() === "failed" && root.selected
            radius: Theme.radiusButton
            color: "#10141C"
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

                Button { text: I18n.t("retry"); onClicked: root.retryRequested(root.filePath) }
                Button { text: I18n.t("change"); onClicked: root.overrideRequested(root.filePath) }
                Button { text: I18n.t("skip"); onClicked: root.skipRequested(root.filePath) }
            }
        }
    }
}
