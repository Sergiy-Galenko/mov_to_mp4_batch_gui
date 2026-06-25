import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property bool compact: false
    property bool dragging: dropArea.containsDrag
    property real dashOffset: 0
    signal filesDropped(var urls)
    signal clicked()

    implicitHeight: compact ? 108 : 220
    radius: Theme.radiusPanel
    color: dragging ? Qt.rgba(0.239, 0.557, 1.0, 0.10) : Theme.bgSurface
    border.width: 0

    Canvas {
        id: borderCanvas
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.lineWidth = 1.5
            ctx.strokeStyle = root.dragging ? Theme.accentPrimary : Theme.bgBorder
            ctx.setLineDash([8, 7])
            ctx.lineDashOffset = -root.dashOffset
            var pad = 1
            var r = Theme.radiusPanel
            var w = width - pad * 2
            var h = height - pad * 2
            var x = pad
            var y = pad
            ctx.beginPath()
            ctx.moveTo(x + r, y)
            ctx.lineTo(x + w - r, y)
            ctx.quadraticCurveTo(x + w, y, x + w, y + r)
            ctx.lineTo(x + w, y + h - r)
            ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
            ctx.lineTo(x + r, y + h)
            ctx.quadraticCurveTo(x, y + h, x, y + h - r)
            ctx.lineTo(x, y + r)
            ctx.quadraticCurveTo(x, y, x + r, y)
            ctx.stroke()
        }
    }

    NumberAnimation on dashOffset {
        from: 0
        to: 30
        duration: 900
        loops: Animation.Infinite
        running: root.dragging
    }

    onDraggingChanged: borderCanvas.requestPaint()
    onDashOffsetChanged: borderCanvas.requestPaint()
    onWidthChanged: borderCanvas.requestPaint()
    onHeightChanged: borderCanvas.requestPaint()

    DropArea {
        id: dropArea
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.hasUrls)
                root.filesDropped(drop.urls)
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.clicked()
        cursorShape: Qt.PointingHandCursor
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 520)
        spacing: 8

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "+"
            color: root.dragging ? Theme.accentPrimary : Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: root.compact ? 26 : 34
            font.bold: true
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: I18n.t("drag_drop")
            color: Theme.textPrimary
            font.family: Theme.bodyFont
            font.pixelSize: root.compact ? 13 : 16
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: I18n.t("formats_hint")
            color: Theme.textMuted
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }
}
