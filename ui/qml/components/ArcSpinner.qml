import QtQuick 2.15
import App 1.0

Item {
    id: root
    property real progress: 0
    property bool indeterminate: false
    property int arcSize: 48
    property color arcColor: Theme.accentPrimary
    property color trackColor: Theme.bgBorder

    width: arcSize
    height: arcSize

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true
        rotation: root.indeterminate ? 0 : -90

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var line = Math.max(3, root.width * 0.09)
            var radius = Math.min(width, height) / 2 - line
            var cx = width / 2
            var cy = height / 2
            ctx.lineWidth = line
            ctx.lineCap = "round"
            ctx.strokeStyle = root.trackColor
            ctx.beginPath()
            ctx.arc(cx, cy, radius, 0, Math.PI * 2, false)
            ctx.stroke()
            var start = -Math.PI / 2
            var end = root.indeterminate ? start + Math.PI * 1.35 : start + Math.PI * 2 * Math.max(0, Math.min(root.progress, 1))
            ctx.strokeStyle = root.arcColor
            ctx.beginPath()
            ctx.arc(cx, cy, radius, start, end, false)
            ctx.stroke()
        }
    }

    RotationAnimator {
        target: canvas
        from: 0
        to: 360
        duration: 1200
        loops: Animation.Infinite
        running: root.indeterminate
    }

    onProgressChanged: canvas.requestPaint()
    onIndeterminateChanged: canvas.requestPaint()
    onArcColorChanged: canvas.requestPaint()
    onTrackColorChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()
}
