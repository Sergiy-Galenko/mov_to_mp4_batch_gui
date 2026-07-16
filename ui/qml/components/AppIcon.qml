import QtQuick 2.15

Canvas {
    id: root
    property string name: "dot"
    property color iconColor: Theme.textSecondary
    property real strokeWidth: 1.65
    implicitWidth: 18
    implicitHeight: 18
    antialiasing: true

    onNameChanged: requestPaint()
    onIconColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        var s = Math.min(width, height)
        var p = (Math.max(width, height) - s) / 2
        var u = s / 24
        function pt(v) { return p + v * u }
        function line(x1, y1, x2, y2) {
            ctx.beginPath(); ctx.moveTo(pt(x1), pt(y1)); ctx.lineTo(pt(x2), pt(y2)); ctx.stroke()
        }
        function rect(x, y, w, h, r) {
            ctx.beginPath()
            ctx.roundedRect(pt(x), pt(y), w * u, h * u, r * u, r * u)
            ctx.stroke()
        }

        ctx.clearRect(0, 0, width, height)
        ctx.strokeStyle = iconColor
        ctx.fillStyle = iconColor
        ctx.lineWidth = Math.max(1, strokeWidth * u)
        ctx.lineCap = "round"
        ctx.lineJoin = "round"

        if (name === "queue") {
            rect(3, 4, 18, 16, 2); line(7, 9, 17, 9); line(7, 13, 17, 13); line(7, 17, 13, 17)
        } else if (name === "download") {
            line(12, 3, 12, 15); line(8, 11, 12, 15); line(16, 11, 12, 15); line(4, 20, 20, 20)
        } else if (name === "sliders") {
            line(4, 7, 20, 7); line(4, 12, 20, 12); line(4, 17, 20, 17)
            ctx.beginPath(); ctx.arc(pt(9), pt(7), 2 * u, 0, Math.PI * 2); ctx.fill()
            ctx.beginPath(); ctx.arc(pt(15), pt(12), 2 * u, 0, Math.PI * 2); ctx.fill()
            ctx.beginPath(); ctx.arc(pt(11), pt(17), 2 * u, 0, Math.PI * 2); ctx.fill()
        } else if (name === "chart") {
            line(4, 20, 20, 20); line(4, 20, 4, 4); line(7, 16, 11, 12); line(11, 12, 14, 14); line(14, 14, 20, 7)
        } else if (name === "settings") {
            ctx.save()
            ctx.translate(pt(12), pt(12))
            for (var a = 0; a < 8; ++a) {
                ctx.save()
                ctx.rotate(a * Math.PI / 4)
                ctx.fillRect(-1.55 * u, -10 * u, 3.1 * u, 4.4 * u)
                ctx.restore()
            }
            ctx.restore()
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 6.7 * u, 0, Math.PI * 2); ctx.stroke()
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 2.65 * u, 0, Math.PI * 2); ctx.stroke()
        } else if (name === "folder") {
            ctx.beginPath(); ctx.moveTo(pt(3), pt(7)); ctx.lineTo(pt(9), pt(7)); ctx.lineTo(pt(11), pt(9)); ctx.lineTo(pt(21), pt(9)); ctx.lineTo(pt(19), pt(19)); ctx.lineTo(pt(3), pt(19)); ctx.closePath(); ctx.stroke()
        } else if (name === "file") {
            ctx.beginPath(); ctx.moveTo(pt(6), pt(3)); ctx.lineTo(pt(14), pt(3)); ctx.lineTo(pt(19), pt(8)); ctx.lineTo(pt(19), pt(21)); ctx.lineTo(pt(6), pt(21)); ctx.closePath(); ctx.stroke(); line(14, 3, 14, 8); line(14, 8, 19, 8)
        } else if (name === "search") {
            ctx.beginPath(); ctx.arc(pt(10), pt(10), 5.5 * u, 0, Math.PI * 2); ctx.stroke(); line(14, 14, 20, 20)
        } else if (name === "bell") {
            ctx.beginPath(); ctx.arc(pt(12), pt(18.5), 1.2 * u, 0, Math.PI * 2); ctx.fill()
            ctx.beginPath(); ctx.moveTo(pt(5), pt(17)); ctx.lineTo(pt(7), pt(15)); ctx.lineTo(pt(7), pt(10)); ctx.bezierCurveTo(pt(7), pt(4), pt(17), pt(4), pt(17), pt(10)); ctx.lineTo(pt(17), pt(15)); ctx.lineTo(pt(19), pt(17)); ctx.closePath(); ctx.stroke()
        } else if (name === "sun") {
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 4.4 * u, 0, Math.PI * 2); ctx.stroke()
            for (var ray = 0; ray < 8; ++ray) {
                var rayAngle = ray * Math.PI / 4
                line(12 + Math.cos(rayAngle) * 7.3, 12 + Math.sin(rayAngle) * 7.3,
                     12 + Math.cos(rayAngle) * 10, 12 + Math.sin(rayAngle) * 10)
            }
        } else if (name === "moon") {
            ctx.beginPath()
            ctx.arc(pt(10.5), pt(12), 7.5 * u, Math.PI * .28, Math.PI * 1.72, false)
            ctx.arc(pt(15.2), pt(8.8), 6.5 * u, Math.PI * 1.68, Math.PI * .38, true)
            ctx.closePath()
            ctx.fill()
        } else if (name === "language") {
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 8 * u, 0, Math.PI * 2); ctx.stroke(); line(4, 12, 20, 12); line(12, 4, 12, 20)
            ctx.beginPath(); ctx.ellipse(pt(12), pt(12), 3.5 * u, 8 * u, 0, 0, Math.PI * 2); ctx.stroke()
        } else if (name === "more") {
            for (var i = 0; i < 3; ++i) { ctx.beginPath(); ctx.arc(pt(6 + i * 6), pt(12), 1.35 * u, 0, Math.PI * 2); ctx.fill() }
        } else if (name === "plus") {
            line(12, 5, 12, 19); line(5, 12, 19, 12)
        } else if (name === "chevron") {
            line(8, 5, 15, 12); line(15, 12, 8, 19)
        } else if (name === "play") {
            ctx.beginPath(); ctx.moveTo(pt(8), pt(5)); ctx.lineTo(pt(19), pt(12)); ctx.lineTo(pt(8), pt(19)); ctx.closePath(); ctx.fill()
        } else if (name === "pause") {
            ctx.fillRect(pt(7), pt(5), 3 * u, 14 * u); ctx.fillRect(pt(14), pt(5), 3 * u, 14 * u)
        } else if (name === "stop") {
            ctx.fillRect(pt(6), pt(6), 12 * u, 12 * u)
        } else if (name === "close") {
            line(6, 6, 18, 18); line(18, 6, 6, 18)
        } else if (name === "sort") {
            line(5, 7, 19, 7); line(5, 12, 15, 12); line(5, 17, 10, 17)
        } else if (name === "info") {
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 8 * u, 0, Math.PI * 2); ctx.stroke(); line(12, 11, 12, 17); ctx.beginPath(); ctx.arc(pt(12), pt(7.5), 1 * u, 0, Math.PI * 2); ctx.fill()
        } else if (name === "history") {
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 8 * u, Math.PI * .72, Math.PI * 2.15); ctx.stroke(); line(12, 7, 12, 12); line(12, 12, 16, 14); line(4, 7, 4, 12); line(4, 7, 8, 7)
        } else {
            ctx.beginPath(); ctx.arc(pt(12), pt(12), 2 * u, 0, Math.PI * 2); ctx.fill()
        }
    }
}
