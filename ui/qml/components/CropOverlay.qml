import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Item {
    id: root
    anchors.fill: parent

    property bool active: true
    property int nativeWidth: 1920
    property int nativeHeight: 1080

    property string aspectRatioPreset: "free" // "free", "1:1", "4:3", "16:9", "9:16"

    property real cropX: 0
    property real cropY: 0
    property real cropWidth: width
    property real cropHeight: height

    signal cropChanged(int x, int y, int w, int h)
    signal resetRequested()

    visible: active

    readonly property var aspectRatios: ({
        "free": 0.0,
        "1:1": 1.0,
        "4:3": 4.0 / 3.0,
        "16:9": 16.0 / 9.0,
        "9:16": 9.0 / 16.0
    })

    function getTargetRatio() {
        return aspectRatios[root.aspectRatioPreset] || 0.0
    }

    function resetCrop() {
        cropBox.x = 0
        cropBox.y = 0
        cropBox.width = root.width
        cropBox.height = root.height
        applyAspectRatioConstraint()
        emitNativeCrop()
        resetRequested()
    }

    function setNativeCrop(nx, ny, nw, nh) {
        if (root.width <= 0 || root.height <= 0 || root.nativeWidth <= 0 || root.nativeHeight <= 0) return
        var scaleX = root.width / root.nativeWidth
        var scaleY = root.height / root.nativeHeight

        cropBox.x = Math.max(0, Math.min(root.width - 24, Math.round(nx * scaleX)))
        cropBox.y = Math.max(0, Math.min(root.height - 24, Math.round(ny * scaleY)))
        cropBox.width = Math.max(24, Math.min(root.width - cropBox.x, Math.round(nw * scaleX)))
        cropBox.height = Math.max(24, Math.min(root.height - cropBox.y, Math.round(nh * scaleY)))
        applyAspectRatioConstraint()
    }

    function applyAspectRatioConstraint() {
        var ratio = getTargetRatio()
        if (ratio <= 0.0) return

        var curW = cropBox.width
        var curH = curW / ratio
        if (cropBox.y + curH > root.height) {
            curH = root.height - cropBox.y
            curW = curH * ratio
        }
        if (cropBox.x + curW > root.width) {
            curW = root.width - cropBox.x
            curH = curW / ratio
        }
        cropBox.width = Math.max(24, Math.round(curW))
        cropBox.height = Math.max(24, Math.round(curH))
        emitNativeCrop()
    }

    function emitNativeCrop() {
        if (root.width <= 0 || root.height <= 0) return
        var scaleX = (root.nativeWidth > 0 ? root.nativeWidth : root.width) / root.width
        var scaleY = (root.nativeHeight > 0 ? root.nativeHeight : root.height) / root.height

        var nx = Math.max(0, Math.round(cropBox.x * scaleX))
        var ny = Math.max(0, Math.round(cropBox.y * scaleY))
        var nw = Math.min(root.nativeWidth - nx, Math.round(cropBox.width * scaleX))
        var nh = Math.min(root.nativeHeight - ny, Math.round(cropBox.height * scaleY))

        root.cropChanged(nx, ny, nw, nh)
    }

    onAspectRatioPresetChanged: applyAspectRatioConstraint()

    onWidthChanged: {
        if (cropBox.width <= 0 || cropBox.width > root.width) cropBox.width = root.width
    }
    onHeightChanged: {
        if (cropBox.height <= 0 || cropBox.height > root.height) cropBox.height = root.height
    }

    // 1. Shaded mask outside crop box (4 sides)
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(0, cropBox.y)
        color: Theme.modalScrim
    }
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: cropBox.bottom
        anchors.bottom: parent.bottom
        color: Theme.modalScrim
    }
    Rectangle {
        anchors.left: parent.left
        anchors.right: cropBox.left
        y: cropBox.y
        height: cropBox.height
        color: Theme.modalScrim
    }
    Rectangle {
        anchors.left: cropBox.right
        anchors.right: parent.right
        y: cropBox.y
        height: cropBox.height
        color: Theme.modalScrim
    }

    // 2. The Crop Box
    Item {
        id: cropBox
        x: root.cropX > 0 ? root.cropX : 0
        y: root.cropY > 0 ? root.cropY : 0
        width: root.cropWidth > 0 ? Math.min(root.width, root.cropWidth) : root.width
        height: root.cropHeight > 0 ? Math.min(root.height, root.cropHeight) : root.height

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 2
            border.color: Theme.accentPrimary

            // Rule-of-thirds grid lines (2 vertical, 2 horizontal)
            Rectangle {
                x: parent.width / 3
                y: 0
                width: 1
                height: parent.height
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.45)
            }
            Rectangle {
                x: (parent.width * 2) / 3
                y: 0
                width: 1
                height: parent.height
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.45)
            }
            Rectangle {
                x: 0
                y: parent.height / 3
                width: parent.width
                height: 1
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.45)
            }
            Rectangle {
                x: 0
                y: (parent.height * 2) / 3
                width: parent.width
                height: 1
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.45)
            }
        }

        // Drag the whole crop box
        MouseArea {
            anchors.fill: parent
            anchors.margins: 14
            cursorShape: Qt.SizeAllCursor
            drag.target: cropBox
            drag.axis: Drag.XAndYAxis
            drag.minimumX: 0
            drag.maximumX: root.width - cropBox.width
            drag.minimumY: 0
            drag.maximumY: root.height - cropBox.height

            onPositionChanged: {
                if (drag.active) root.emitNativeCrop()
            }
        }

        // Crop size readout badge
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 6
            height: 20
            width: readoutText.implicitWidth + 12
            radius: 3
            color: Theme.mediaOverlay

            Text {
                id: readoutText
                anchors.centerIn: parent
                text: {
                    var scaleX = (root.nativeWidth > 0 ? root.nativeWidth : root.width) / root.width
                    var scaleY = (root.nativeHeight > 0 ? root.nativeHeight : root.height) / root.height
                    var nw = Math.round(cropBox.width * scaleX)
                    var nh = Math.round(cropBox.height * scaleY)
                    return nw + " × " + nh
                }
                color: Theme.textOnMedia
                font.pixelSize: 10
                font.family: Theme.monoFont
            }
        }

        // 8 Control Resize Handles:
        // Handle Size
        readonly property int hSize: 10
        readonly property int halfH: 5

        // 1. Top-Left Corner
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: -parent.halfH; y: -parent.halfH
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeFDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newX = Math.max(0, Math.min(cropBox.x + mouse.x, cropBox.x + cropBox.width - 24))
                        var newY = Math.max(0, Math.min(cropBox.y + mouse.y, cropBox.y + cropBox.height - 24))
                        var newW = cropBox.width + (cropBox.x - newX)
                        var newH = cropBox.height + (cropBox.y - newY)
                        var ratio = root.getTargetRatio()
                        if (ratio > 0.0) newH = newW / ratio
                        cropBox.x = newX
                        cropBox.y = newY
                        cropBox.width = newW
                        cropBox.height = newH
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 2. Top-Center Edge
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: (parent.width / 2) - parent.halfH; y: -parent.halfH
            color: Theme.accentPrimary
            visible: root.getTargetRatio() <= 0.0
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeVerCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newY = Math.max(0, Math.min(cropBox.y + mouse.y, cropBox.y + cropBox.height - 24))
                        cropBox.height += (cropBox.y - newY)
                        cropBox.y = newY
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 3. Top-Right Corner
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: parent.width - parent.halfH; y: -parent.halfH
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeBDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newY = Math.max(0, Math.min(cropBox.y + mouse.y, cropBox.y + cropBox.height - 24))
                        var newW = Math.max(24, Math.min(root.width - cropBox.x, mouse.x))
                        var newH = cropBox.height + (cropBox.y - newY)
                        var ratio = root.getTargetRatio()
                        if (ratio > 0.0) newH = newW / ratio
                        cropBox.y = newY
                        cropBox.width = newW
                        cropBox.height = newH
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 4. Middle-Right Edge
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: parent.width - parent.halfH; y: (parent.height / 2) - parent.halfH
            color: Theme.accentPrimary
            visible: root.getTargetRatio() <= 0.0
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeHorCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        cropBox.width = Math.max(24, Math.min(root.width - cropBox.x, mouse.x))
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 5. Bottom-Right Corner
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: parent.width - parent.halfH; y: parent.height - parent.halfH
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeFDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newW = Math.max(24, Math.min(root.width - cropBox.x, mouse.x))
                        var newH = Math.max(24, Math.min(root.height - cropBox.y, mouse.y))
                        var ratio = root.getTargetRatio()
                        if (ratio > 0.0) newH = newW / ratio
                        cropBox.width = newW
                        cropBox.height = newH
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 6. Bottom-Center Edge
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: (parent.width / 2) - parent.halfH; y: parent.height - parent.halfH
            color: Theme.accentPrimary
            visible: root.getTargetRatio() <= 0.0
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeVerCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        cropBox.height = Math.max(24, Math.min(root.height - cropBox.y, mouse.y))
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 7. Bottom-Left Corner
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: -parent.halfH; y: parent.height - parent.halfH
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeBDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newX = Math.max(0, Math.min(cropBox.x + mouse.x, cropBox.x + cropBox.width - 24))
                        var newW = cropBox.width + (cropBox.x - newX)
                        var newH = Math.max(24, Math.min(root.height - cropBox.y, mouse.y))
                        var ratio = root.getTargetRatio()
                        if (ratio > 0.0) newH = newW / ratio
                        cropBox.width = newW
                        cropBox.x = newX
                        cropBox.height = newH
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // 8. Middle-Left Edge
        Rectangle {
            width: parent.hSize; height: parent.hSize
            x: -parent.halfH; y: (parent.height / 2) - parent.halfH
            color: Theme.accentPrimary
            visible: root.getTargetRatio() <= 0.0
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeHorCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newX = Math.max(0, Math.min(cropBox.x + mouse.x, cropBox.x + cropBox.width - 24))
                        cropBox.width += (cropBox.x - newX)
                        cropBox.x = newX
                        root.emitNativeCrop()
                    }
                }
            }
        }
    }
}
