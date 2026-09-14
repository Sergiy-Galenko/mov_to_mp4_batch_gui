import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

Item {
    id: root
    anchors.fill: parent

    property bool active: true
    property int nativeWidth: 1920
    property int nativeHeight: 1080

    property real cropX: 0
    property real cropY: 0
    property real cropWidth: width
    property real cropHeight: height

    signal cropChanged(int x, int y, int w, int h)
    signal resetRequested()

    visible: active

    function resetCrop() {
        cropBox.x = 0
        cropBox.y = 0
        cropBox.width = root.width
        cropBox.height = root.height
        emitNativeCrop()
        resetRequested()
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

    // Shaded mask outside crop box
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

    // The Crop Box
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

            // Rule-of-thirds grid lines
            Rectangle {
                x: parent.width / 3
                y: 0
                width: 1
                height: parent.height
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.4)
            }
            Rectangle {
                x: (parent.width * 2) / 3
                y: 0
                width: 1
                height: parent.height
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.4)
            }
            Rectangle {
                x: 0
                y: parent.height / 3
                width: parent.width
                height: 1
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.4)
            }
            Rectangle {
                x: 0
                y: (parent.height * 2) / 3
                width: parent.width
                height: 1
                color: Qt.rgba(Theme.textOnMedia.r, Theme.textOnMedia.g, Theme.textOnMedia.b, 0.4)
            }
        }

        // Drag the whole crop box
        MouseArea {
            anchors.fill: parent
            anchors.margins: 12
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

        // Corner Resize Handles
        // Top-Left Handle
        Rectangle {
            width: 10; height: 10
            x: -5; y: -5
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeFDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newX = Math.max(0, Math.min(cropBox.x + mouse.x, cropBox.x + cropBox.width - 24))
                        var newY = Math.max(0, Math.min(cropBox.y + mouse.y, cropBox.y + cropBox.height - 24))
                        cropBox.width += (cropBox.x - newX)
                        cropBox.height += (cropBox.y - newY)
                        cropBox.x = newX
                        cropBox.y = newY
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // Top-Right Handle
        Rectangle {
            width: 10; height: 10
            x: parent.width - 5; y: -5
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeBDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newY = Math.max(0, Math.min(cropBox.y + mouse.y, cropBox.y + cropBox.height - 24))
                        var newW = Math.max(24, Math.min(root.width - cropBox.x, mouse.x))
                        cropBox.height += (cropBox.y - newY)
                        cropBox.y = newY
                        cropBox.width = newW
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // Bottom-Left Handle
        Rectangle {
            width: 10; height: 10
            x: -5; y: parent.height - 5
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeBDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        var newX = Math.max(0, Math.min(cropBox.x + mouse.x, cropBox.x + cropBox.width - 24))
                        var newH = Math.max(24, Math.min(root.height - cropBox.y, mouse.y))
                        cropBox.width += (cropBox.x - newX)
                        cropBox.x = newX
                        cropBox.height = newH
                        root.emitNativeCrop()
                    }
                }
            }
        }

        // Bottom-Right Handle
        Rectangle {
            width: 10; height: 10
            x: parent.width - 5; y: parent.height - 5
            color: Theme.accentPrimary
            MouseArea {
                anchors.fill: parent; anchors.margins: -4
                cursorShape: Qt.SizeFDiagCursor
                onPositionChanged: function(mouse) {
                    if (pressed) {
                        cropBox.width = Math.max(24, Math.min(root.width - cropBox.x, mouse.x))
                        cropBox.height = Math.max(24, Math.min(root.height - cropBox.y, mouse.y))
                        root.emitNativeCrop()
                    }
                }
            }
        }
    }
}

