import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property string status: "queued"
    property string label: ""

    function canonicalStatus() {
        if (status === "success")
            return "done"
        if (status === "running" || status === "paused")
            return "processing"
        if (status === "queued" || status === "ready" || status === "analyzing")
            return "pending"
        return status
    }

    function iconText() {
        var state = canonicalStatus()
        if (state === "done") return "OK"
        if (state === "failed") return "!"
        if (state === "skipped") return "--"
        if (state === "processing") return ">>"
        return ".."
    }

    implicitHeight: Theme.buttonHeight - 8
    implicitWidth: Math.max(82, badgeRow.implicitWidth + Theme.space4)
    radius: Theme.radiusSm
    color: Theme.statusFill(canonicalStatus())
    border.width: 1
    border.color: Theme.statusColor(canonicalStatus())

    RowLayout {
        id: badgeRow
        anchors.fill: parent
        anchors.leftMargin: Theme.space2
        anchors.rightMargin: Theme.space2
        spacing: Theme.space1

        Label {
            text: root.iconText()
            color: Theme.statusColor(root.canonicalStatus())
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontSizeXs
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: root.label.length > 0 ? root.label : root.canonicalStatus()
            color: Theme.statusColor(root.canonicalStatus())
            font.pixelSize: Theme.fontSizeXs
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
