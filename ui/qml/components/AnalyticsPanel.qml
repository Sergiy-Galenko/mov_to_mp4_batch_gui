import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property var speedHistory: []
    property var fileTimings: []
    property var codecDistribution: ({})
    property int activeTab: 0

    radius: Theme.radiusPanel
    color: Theme.bgSurface
    border.width: 1
    border.color: Theme.bgBorder
    clip: true

    function timingMax() {
        var maxValue = 1
        for (var i = 0; i < fileTimings.length; ++i)
            maxValue = Math.max(maxValue, Number(fileTimings[i].duration || 0))
        return maxValue
    }

    function statusColor(status) {
        if (status === "success" || status === "done") return Theme.accentSuccess
        if (status === "failed") return Theme.accentError
        if (status === "running" || status === "processing") return Theme.accentWarn
        return Theme.textMuted
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Label {
                Layout.fillWidth: true
                text: I18n.t("analytics")
                color: Theme.textPrimary
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }

            Repeater {
                model: ["throughput", "per_file", "codecs"]
                delegate: Rectangle {
                    width: Math.max(82, tabLabel.implicitWidth + 18)
                    height: 28
                    radius: Theme.radiusButton
                    color: root.activeTab === index ? Theme.accentPrimary : (mouse.containsMouse ? Theme.bgElevated : "transparent")
                    border.width: 1
                    border.color: root.activeTab === index ? Theme.accentPrimary : Theme.bgBorder

                    Label {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: I18n.t(modelData)
                        color: root.activeTab === index ? "#FFFFFF" : Theme.textSecondary
                        font.pixelSize: Theme.fontMeta
                        font.family: Theme.monoFont
                    }

                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.activeTab = index
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.activeTab

            Item {
                Canvas {
                    id: throughputCanvas
                    anchors.fill: parent
                    antialiasing: true
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        var padL = 42
                        var padT = 16
                        var padR = 14
                        var padB = 28
                        var w = width - padL - padR
                        var h = height - padT - padB
                        ctx.strokeStyle = Theme.bgBorder
                        ctx.lineWidth = 1
                        ctx.setLineDash([4, 5])
                        for (var g = 0; g <= 4; ++g) {
                            var gy = padT + h * g / 4
                            ctx.beginPath()
                            ctx.moveTo(padL, gy)
                            ctx.lineTo(padL + w, gy)
                            ctx.stroke()
                        }
                        ctx.setLineDash([])
                        ctx.fillStyle = Theme.textMuted
                        ctx.font = Theme.fontMeta + "px " + Theme.monoFont
                        ctx.fillText(I18n.t("speed_x"), 6, padT + 8)
                        var data = root.speedHistory || []
                        if (data.length < 2) {
                            ctx.fillStyle = Theme.textMuted
                            ctx.fillText(I18n.t("waiting_speed"), padL, padT + h / 2)
                            return
                        }
                        var maxT = Math.max(1, Number(data[data.length - 1].time || 1))
                        var maxS = 1
                        for (var i = 0; i < data.length; ++i)
                            maxS = Math.max(maxS, Number(data[i].speed || 0))
                        function px(point) { return padL + (Number(point.time || 0) / maxT) * w }
                        function py(point) { return padT + h - (Number(point.speed || 0) / maxS) * h }
                        var fill = ctx.createLinearGradient(0, padT, 0, padT + h)
                        fill.addColorStop(0, Qt.rgba(0.239, 0.557, 1.0, 0.26))
                        fill.addColorStop(1, Qt.rgba(0.239, 0.557, 1.0, 0.0))
                        ctx.beginPath()
                        ctx.moveTo(px(data[0]), padT + h)
                        for (i = 0; i < data.length; ++i)
                            ctx.lineTo(px(data[i]), py(data[i]))
                        ctx.lineTo(px(data[data.length - 1]), padT + h)
                        ctx.closePath()
                        ctx.fillStyle = fill
                        ctx.fill()
                        ctx.beginPath()
                        for (i = 0; i < data.length; ++i) {
                            if (i === 0) ctx.moveTo(px(data[i]), py(data[i]))
                            else ctx.lineTo(px(data[i]), py(data[i]))
                        }
                        ctx.strokeStyle = Theme.accentPrimary
                        ctx.lineWidth = 2
                        ctx.stroke()
                        ctx.fillStyle = Theme.accentPrimary
                        for (i = 0; i < data.length; ++i) {
                            ctx.beginPath()
                            ctx.arc(px(data[i]), py(data[i]), 3.5, 0, Math.PI * 2)
                            ctx.fill()
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    Repeater {
                        model: (root.fileTimings || []).slice(0, 10)
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 24
                            spacing: 8

                            Label {
                                Layout.preferredWidth: 180
                                text: modelData.name || "file"
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontMeta
                                elide: Text.ElideMiddle
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 10
                                radius: 5
                                color: "#10141C"
                                border.width: 1
                                border.color: Theme.bgBorder

                                Rectangle {
                                    id: bar
                                    height: parent.height
                                    radius: parent.radius
                                    color: root.statusColor(modelData.status || "")
                                    width: parent.width * Math.min(1, Number(modelData.duration || 0) / root.timingMax())
                                    Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                                }
                            }

                            Label {
                                Layout.preferredWidth: 54
                                text: Number(modelData.duration || 0).toFixed(1) + "s"
                                color: Theme.textMuted
                                font.family: Theme.monoFont
                                font.pixelSize: Theme.fontMeta
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }

                    Label {
                        Layout.alignment: Qt.AlignHCenter
                        visible: !root.fileTimings || root.fileTimings.length === 0
                        text: I18n.t("no_timings")
                        color: Theme.textMuted
                        font.pixelSize: Theme.fontMeta
                    }
                }
            }

            Item {
                id: donutPane
                property int hoveredSegment: -1

                RowLayout {
                    anchors.fill: parent
                    spacing: 16

                    Canvas {
                        id: donutCanvas
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        antialiasing: true
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            var keys = Object.keys(root.codecDistribution || {})
                            var total = 0
                            for (var i = 0; i < keys.length; ++i)
                                total += Number(root.codecDistribution[keys[i]] || 0)
                            var cx = width / 2
                            var cy = height / 2
                            var outer = Math.min(width, height) * 0.38
                            var inner = outer * 0.4
                            var colors = [Theme.accentPrimary, Theme.accentPurple, Theme.accentSuccess, Theme.accentWarn, "#EC4899", "#14B8A6"]
                            if (total <= 0) {
                                ctx.strokeStyle = Theme.bgBorder
                                ctx.lineWidth = outer - inner
                                ctx.beginPath()
                                ctx.arc(cx, cy, (outer + inner) / 2, 0, Math.PI * 2)
                                ctx.stroke()
                                ctx.fillStyle = Theme.textMuted
                                ctx.font = Theme.fontMeta + "px " + Theme.monoFont
                                ctx.textAlign = "center"
                                ctx.fillText("0 " + I18n.t("files"), cx, cy + 4)
                                return
                            }
                            var angle = -Math.PI / 2
                            for (i = 0; i < keys.length; ++i) {
                                var count = Number(root.codecDistribution[keys[i]] || 0)
                                var slice = (count / total) * Math.PI * 2
                                var radius = outer + (donutPane.hoveredSegment === i ? 4 : 0)
                                ctx.beginPath()
                                ctx.moveTo(cx, cy)
                                ctx.arc(cx, cy, radius, angle, angle + slice)
                                ctx.closePath()
                                ctx.fillStyle = colors[i % colors.length]
                                ctx.fill()
                                angle += slice
                            }
                            ctx.globalCompositeOperation = "destination-out"
                            ctx.beginPath()
                            ctx.arc(cx, cy, inner, 0, Math.PI * 2)
                            ctx.fill()
                            ctx.globalCompositeOperation = "source-over"
                            ctx.fillStyle = Theme.bgSurface
                            ctx.beginPath()
                            ctx.arc(cx, cy, inner - 1, 0, Math.PI * 2)
                            ctx.fill()
                            ctx.fillStyle = Theme.textPrimary
                            ctx.font = "bold " + Theme.fontTitle + "px " + Theme.monoFont
                            ctx.textAlign = "center"
                            ctx.fillText(String(total), cx, cy - 2)
                            ctx.fillStyle = Theme.textMuted
                            ctx.font = Theme.fontMeta + "px " + Theme.monoFont
                                ctx.fillText(I18n.t("files"), cx, cy + 15)
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onPositionChanged: {
                                var keys = Object.keys(root.codecDistribution || {})
                                var total = 0
                                for (var i = 0; i < keys.length; ++i)
                                    total += Number(root.codecDistribution[keys[i]] || 0)
                                if (total <= 0) {
                                    donutPane.hoveredSegment = -1
                                    return
                                }
                                var dx = mouse.x - donutCanvas.width / 2
                                var dy = mouse.y - donutCanvas.height / 2
                                var angle = Math.atan2(dy, dx) + Math.PI / 2
                                if (angle < 0) angle += Math.PI * 2
                                var start = 0
                                donutPane.hoveredSegment = -1
                                for (i = 0; i < keys.length; ++i) {
                                    var slice = (Number(root.codecDistribution[keys[i]] || 0) / total) * Math.PI * 2
                                    if (angle >= start && angle <= start + slice) {
                                        donutPane.hoveredSegment = i
                                        break
                                    }
                                    start += slice
                                }
                                donutCanvas.requestPaint()
                            }
                            onExited: { donutPane.hoveredSegment = -1; donutCanvas.requestPaint() }
                        }
                    }

                    ColumnLayout {
                        Layout.preferredWidth: 150
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 7
                        Repeater {
                            model: Object.keys(root.codecDistribution || {})
                            delegate: RowLayout {
                                spacing: 7
                                Rectangle {
                                    width: 10
                                    height: 10
                                    radius: 2
                                    color: [Theme.accentPrimary, Theme.accentPurple, Theme.accentSuccess, Theme.accentWarn, "#EC4899", "#14B8A6"][index % 6]
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData + " (" + root.codecDistribution[modelData] + ")"
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontMeta
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    onSpeedHistoryChanged: throughputCanvas.requestPaint()
    onCodecDistributionChanged: donutCanvas.requestPaint()
}
