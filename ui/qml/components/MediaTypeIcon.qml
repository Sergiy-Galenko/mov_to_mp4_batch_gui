import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Item {
    id: root

    property string mediaType: ""
    property string status: ""
    property string extension: ""

    readonly property string effectiveType: {
        var value = String(mediaType || "").toLowerCase()
        if (value === "photo")
            return "image"
        if (value === "image" || value === "video" || value === "audio" || value === "subtitle")
            return value
        return "file"
    }

    readonly property color primaryColor: effectiveType === "image" ? "#10B981"
                                      : effectiveType === "video" ? "#7C3AED"
                                      : effectiveType === "audio" ? "#F59E0B"
                                      : effectiveType === "subtitle" ? "#06B6D4"
                                      : "#94A3B8"
    readonly property color softColor: effectiveType === "image" ? (Theme.lightMode ? "#ECFDF5" : "#052E24")
                                   : effectiveType === "video" ? (Theme.lightMode ? "#F3E8FF" : "#241033")
                                   : effectiveType === "audio" ? (Theme.lightMode ? "#FFFBEB" : "#332307")
                                   : effectiveType === "subtitle" ? (Theme.lightMode ? "#ECFEFF" : "#082F35")
                                   : (Theme.lightMode ? "#F8FAFC" : "#1F2937")
    readonly property bool hasStatusDot: status === "success" || status === "done"
                                      || status === "failed" || status === "cancelled"
                                      || status === "running" || status === "processing"
                                      || status === "analyzing" || status === "paused"

    implicitWidth: 44
    implicitHeight: 44

    function shortExtension() {
        var value = String(extension || "").replace(/^\./, "").toUpperCase()
        if (!value) {
            if (effectiveType === "image")
                return "IMG"
            if (effectiveType === "video")
                return "VID"
            if (effectiveType === "audio")
                return "AUD"
            if (effectiveType === "subtitle")
                return "SUB"
            return "FILE"
        }
        return value.slice(0, 4)
    }

    function statusColor() {
        if (status === "success" || status === "done")
            return Theme.statusSuccess
        if (status === "failed" || status === "cancelled")
            return Theme.statusError
        if (status === "running" || status === "processing" || status === "analyzing" || status === "paused")
            return Theme.statusRunning
        return Theme.transparent
    }

    function roundedRect(ctx, x, y, width, height, radius) {
        ctx.beginPath()
        ctx.moveTo(x + radius, y)
        ctx.lineTo(x + width - radius, y)
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
        ctx.lineTo(x + width, y + height - radius)
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
        ctx.lineTo(x + radius, y + height)
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
        ctx.lineTo(x, y + radius)
        ctx.quadraticCurveTo(x, y, x + radius, y)
        ctx.closePath()
    }

    function drawImageIcon(ctx, width, height) {
        roundedRect(ctx, width * 0.12, height * 0.17, width * 0.76, height * 0.66, 4)
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(width * 0.70, height * 0.35, 2.4, 0, Math.PI * 2)
        ctx.fill()

        ctx.beginPath()
        ctx.moveTo(width * 0.20, height * 0.72)
        ctx.lineTo(width * 0.42, height * 0.50)
        ctx.lineTo(width * 0.56, height * 0.66)
        ctx.lineTo(width * 0.66, height * 0.55)
        ctx.lineTo(width * 0.82, height * 0.72)
        ctx.stroke()
    }

    function drawVideoIcon(ctx, width, height) {
        roundedRect(ctx, width * 0.13, height * 0.30, width * 0.74, height * 0.48, 4)
        ctx.stroke()

        roundedRect(ctx, width * 0.13, height * 0.13, width * 0.74, height * 0.22, 3)
        ctx.fill()

        ctx.strokeStyle = Theme.lightMode ? "#F3E8FF" : "#241033"
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(width * 0.32, height * 0.13)
        ctx.lineTo(width * 0.23, height * 0.35)
        ctx.moveTo(width * 0.56, height * 0.13)
        ctx.lineTo(width * 0.47, height * 0.35)
        ctx.moveTo(width * 0.80, height * 0.13)
        ctx.lineTo(width * 0.71, height * 0.35)
        ctx.stroke()

        ctx.strokeStyle = root.primaryColor
        ctx.fillStyle = root.primaryColor
        ctx.beginPath()
        ctx.moveTo(width * 0.45, height * 0.43)
        ctx.lineTo(width * 0.45, height * 0.66)
        ctx.lineTo(width * 0.66, height * 0.545)
        ctx.closePath()
        ctx.fill()
    }

    function drawAudioIcon(ctx, width, height) {
        ctx.beginPath()
        ctx.moveTo(width * 0.58, height * 0.16)
        ctx.lineTo(width * 0.58, height * 0.66)
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(width * 0.58, height * 0.18)
        ctx.lineTo(width * 0.78, height * 0.25)
        ctx.lineTo(width * 0.78, height * 0.38)
        ctx.lineTo(width * 0.58, height * 0.31)
        ctx.closePath()
        ctx.fill()

        ctx.beginPath()
        ctx.arc(width * 0.40, height * 0.70, Math.max(3, width * 0.12), 0, Math.PI * 2)
        ctx.fill()
        ctx.beginPath()
        ctx.moveTo(width * 0.52, height * 0.66)
        ctx.lineTo(width * 0.58, height * 0.66)
        ctx.stroke()
    }

    function drawSubtitleIcon(ctx, width, height) {
        roundedRect(ctx, width * 0.12, height * 0.22, width * 0.76, height * 0.50, 5)
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(width * 0.38, height * 0.72)
        ctx.lineTo(width * 0.31, height * 0.84)
        ctx.lineTo(width * 0.52, height * 0.72)
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(width * 0.28, height * 0.42)
        ctx.lineTo(width * 0.72, height * 0.42)
        ctx.moveTo(width * 0.28, height * 0.55)
        ctx.lineTo(width * 0.62, height * 0.55)
        ctx.stroke()
    }

    function drawFileIcon(ctx, width, height) {
        var x = width * 0.25
        var y = height * 0.06
        var w = width * 0.50
        var h = height * 0.72
        var fold = width * 0.16

        ctx.beginPath()
        ctx.moveTo(x, y)
        ctx.lineTo(x + w - fold, y)
        ctx.lineTo(x + w, y + fold)
        ctx.lineTo(x + w, y + h)
        ctx.lineTo(x, y + h)
        ctx.closePath()
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(x + w - fold, y)
        ctx.lineTo(x + w - fold, y + fold)
        ctx.lineTo(x + w, y + fold)
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(x + width * 0.10, y + height * 0.36)
        ctx.lineTo(x + w - width * 0.10, y + height * 0.36)
        ctx.moveTo(x + width * 0.10, y + height * 0.50)
        ctx.lineTo(x + w - width * 0.16, y + height * 0.50)
        ctx.stroke()
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: root.softColor
        border.width: 1
        border.color: root.primaryColor
    }

    Canvas {
        id: iconCanvas
        anchors.fill: parent
        anchors.leftMargin: 7
        anchors.rightMargin: 7
        anchors.topMargin: 7
        anchors.bottomMargin: root.effectiveType === "file" ? 13 : 7
        antialiasing: true

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.lineWidth = Math.max(1.6, width * 0.07)
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.strokeStyle = root.primaryColor
            ctx.fillStyle = root.primaryColor

            if (root.effectiveType === "image")
                root.drawImageIcon(ctx, width, height)
            else if (root.effectiveType === "video")
                root.drawVideoIcon(ctx, width, height)
            else if (root.effectiveType === "audio")
                root.drawAudioIcon(ctx, width, height)
            else if (root.effectiveType === "subtitle")
                root.drawSubtitleIcon(ctx, width, height)
            else
                root.drawFileIcon(ctx, width, height)
        }
    }

    Label {
        visible: root.effectiveType === "file"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 3
        width: parent.width - 6
        text: root.shortExtension()
        color: root.primaryColor
        font.family: Theme.monoFont
        font.pixelSize: 8
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        maximumLineCount: 1
    }

    Rectangle {
        visible: root.hasStatusDot
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 3
        anchors.topMargin: 3
        width: 9
        height: 9
        radius: width / 2
        color: root.statusColor()
        border.width: 1
        border.color: Theme.bgElevated
    }

    onEffectiveTypeChanged: iconCanvas.requestPaint()
    onPrimaryColorChanged: iconCanvas.requestPaint()
    onWidthChanged: iconCanvas.requestPaint()
    onHeightChanged: iconCanvas.requestPaint()
}
