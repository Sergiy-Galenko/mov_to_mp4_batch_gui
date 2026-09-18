import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Item {
    id: root

    property bool isOut: false
    property real timeValue: 0.0
    property real totalDuration: 1.0
    property real trackWidth: 100.0
    property real frameStep: 1.0 / 30.0
    property real minBound: 0.0
    property real maxBound: totalDuration
    property bool isSelected: false

    signal valueChangedByUser(real newValue)
    signal selected()
    signal editingStarted()
    signal editingFinished()

    width: 16
    height: parent ? parent.height : 48
    z: isSelected ? 15 : 10

    // Position mapping: center of vertical line aligns with calculated time
    x: {
        var ratio = root.totalDuration > 0 ? (root.timeValue / root.totalDuration) : 0.0
        return Math.round(ratio * root.trackWidth) - (root.isOut ? width : 0)
    }

    focus: true

    Keys.onLeftPressed: function(event) {
        var step = (event.modifiers & Qt.ShiftModifier) ? (root.frameStep * 10) : root.frameStep
        var next = Math.max(root.minBound, root.timeValue - step)
        next = snap(next)
        root.valueChangedByUser(next)
        event.accepted = true
    }

    Keys.onRightPressed: function(event) {
        var step = (event.modifiers & Qt.ShiftModifier) ? (root.frameStep * 10) : root.frameStep
        var next = Math.min(root.maxBound, root.timeValue + step)
        next = snap(next)
        root.valueChangedByUser(next)
        event.accepted = true
    }

    function snap(val) {
        if (root.frameStep > 0) {
            val = Math.round(val / root.frameStep) * root.frameStep
        }
        return Math.max(root.minBound, Math.min(root.maxBound, val))
    }

    readonly property color markerColor: root.isOut ? Theme.accentSecondary : Theme.accentPrimary

    // Top Flag / Grip Handle
    Rectangle {
        id: handleGrip
        width: 16
        height: 20
        anchors.top: parent.top
        x: root.isOut ? 0 : 0
        radius: 2
        color: root.isSelected ? Theme.accentHover : root.markerColor
        border.width: 1
        border.color: Theme.borderStrong

        // Arrow indicator pointing inward
        Text {
            anchors.centerIn: parent
            text: root.isOut ? "◀" : "▶"
            font.pixelSize: 9
            color: Theme.textOnMedia
        }
    }

    // Vertical line reaching down the track
    Rectangle {
        id: line
        width: 2
        anchors.top: handleGrip.bottom
        anchors.bottom: parent.bottom
        x: root.isOut ? (root.width - 2) : 0
        color: root.isSelected ? Theme.accentHover : root.markerColor
    }

    MouseArea {
        onReleased: root.editingFinished()
        onCanceled: root.editingFinished()
        id: dragArea
        anchors.fill: parent
        anchors.margins: -4
        cursorShape: Qt.SizeHorCursor
        hoverEnabled: true

        property real startX: 0
        property real startTime: 0

        onPressed: function(mouse) {
            root.editingStarted()
            root.forceActiveFocus()
            root.selected()
            startX = mouse.x
            startTime = root.timeValue
        }

        onPositionChanged: function(mouse) {
            if (pressed && root.trackWidth > 0 && root.totalDuration > 0) {
                var deltaPixels = mouse.x - startX
                var deltaTime = (deltaPixels / root.trackWidth) * root.totalDuration
                var targetTime = startTime + deltaTime
                targetTime = root.snap(targetTime)
                root.valueChangedByUser(targetTime)
            }
        }
    }
}

