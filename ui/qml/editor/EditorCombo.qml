import QtQuick 2.15
import QtQuick.Controls 2.15
import App 1.0

ComboBox {
    id: control

    property int popupMaxHeight: 320
    property int popupEdgeMargin: 8
    readonly property real _windowX: mapToItem(null, 0, 0).x
    readonly property real _windowY: mapToItem(null, 0, height).y
    function optionText(index) { return String(textAt(index)) }
    function popupXFor(popupWidth) {
        var sceneX = mapToItem(null, 0, 0).x
        return Math.max(popupEdgeMargin - sceneX,
                        Math.min(0, Window.width - popupEdgeMargin - popupWidth - sceneX))
    }

    implicitHeight: EditorTheme.controlHeight
    implicitWidth: 120
    font.pixelSize: EditorTheme.fontSize
    leftPadding: 8
    rightPadding: 28
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: displayText

    contentItem: Label {
        text: control.displayText
        font: control.font
        color: control.enabled ? EditorTheme.text : EditorTheme.muted
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        maximumLineCount: 1
        rightPadding: 6
    }
    indicator: Canvas {
        width: 12; height: 8
        anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
        opacity: control.enabled ? 1 : 0.5
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = EditorTheme.secondary; ctx.lineWidth = 1.5; ctx.lineCap = "round"; ctx.lineJoin = "round"
            ctx.beginPath(); ctx.moveTo(1, 2); ctx.lineTo(width / 2, height - 1); ctx.lineTo(width - 1, 2); ctx.stroke()
        }
    }
    background: Rectangle {
        color: EditorTheme.raised
        radius: 4
        border.width: control.activeFocus || control.popup.visible ? 2 : 1
        border.color: control.activeFocus || control.popup.visible ? EditorTheme.accent : EditorTheme.border
    }

    delegate: ItemDelegate {
        id: option
        required property int index
        required property var model
        width: ListView.view ? ListView.view.width : control.width
        height: Math.max(EditorTheme.controlHeight, optionLabel.implicitHeight + 14)
        leftPadding: 9; rightPadding: 9; topPadding: 7; bottomPadding: 7
        text: control.optionText(index)
        font: control.font
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        Accessible.name: text
        contentItem: Label {
            id: optionLabel
            text: option.text
            color: EditorTheme.text
            font: option.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            maximumLineCount: 1
            clip: true
        }
        background: Rectangle {
            color: option.down ? EditorTheme.raised : option.highlighted || option.hovered ? EditorTheme.hover : EditorTheme.panel
            radius: 3
        }
    }

    popup: Popup {
        id: dropdownPopup
        objectName: control.objectName.length > 0 ? control.objectName + "Popup" : "editorComboPopup"
        readonly property int desiredHeight: Math.min(control.popupMaxHeight, optionList.contentHeight + topPadding + bottomPadding)
        readonly property int availableBelow: Math.max(0, control.Window.height - control._windowY - control.popupEdgeMargin)
        readonly property int availableAbove: Math.max(0, control._windowY - control.height - control.popupEdgeMargin)
        readonly property bool opensAbove: desiredHeight > availableBelow && availableAbove > availableBelow
        x: 0
        y: opensAbove ? -height - 4 : control.height + 4
        width: Math.min(Math.max(control.width, 120), Math.max(120, control.Window.width - control.popupEdgeMargin * 2))
        height: Math.max(0, Math.min(desiredHeight, opensAbove ? availableAbove : availableBelow))
        padding: 5
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside | Popup.CloseOnReleaseOutside
        onAboutToShow: x = control.popupXFor(width)
        onOpened: optionList.currentIndex = control.highlightedIndex
        background: Rectangle {
            color: EditorTheme.panel
            border.width: 1
            border.color: EditorTheme.border
            radius: 5
        }
        contentItem: ListView {
            id: optionList
            focus: true
            clip: true
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationEnabled: true
            ScrollIndicator.vertical: ScrollIndicator {}
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Down) {
                    optionList.currentIndex = Math.min(control.count - 1, optionList.currentIndex + 1)
                } else if (event.key === Qt.Key_Up) {
                    optionList.currentIndex = Math.max(0, optionList.currentIndex - 1)
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                    if (optionList.currentIndex >= 0) {
                        control.currentIndex = optionList.currentIndex
                        control.activated(control.currentIndex)
                    }
                    dropdownPopup.close()
                } else if (event.key === Qt.Key_Escape) {
                    dropdownPopup.close()
                } else {
                    return
                }
                event.accepted = true
            }
        }
    }
}
