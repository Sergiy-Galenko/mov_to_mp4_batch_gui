import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ComboBox {
    id: control

    property string translationPrefix: ""
    property int popupMaxHeight: 300
    property int popupEdgeMargin: 8
    property int optionHorizontalPadding: 10
    property int optionVerticalPadding: 7
    readonly property real _windowX: mapToItem(null, 0, 0).x
    readonly property real _windowY: mapToItem(null, 0, height).y

    function labelFor(value) {
        return translationPrefix.length > 0
            ? I18n.t(translationPrefix + String(value))
            : String(value === undefined || value === null ? "" : value)
    }
    function optionText(index) { return labelFor(textAt(index)) }
    function popupXFor(popupWidth) {
        var sceneX = mapToItem(null, 0, 0).x
        return Math.max(popupEdgeMargin - sceneX,
                        Math.min(0, Window.width - popupEdgeMargin - popupWidth - sceneX))
    }

    font.pixelSize: Theme.fontSizeSm
    implicitHeight: Theme.inputHeight
    leftPadding: 10
    rightPadding: 34
    Layout.fillWidth: true
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: labelFor(displayText)

    contentItem: Label {
        text: control.labelFor(control.displayText)
        color: control.enabled ? Theme.text : Theme.disabledText
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        maximumLineCount: 1
        clip: true
        rightPadding: 8
    }

    indicator: Canvas {
        width: 12; height: 8
        anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
        opacity: control.enabled ? 1 : 0.5
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = Theme.muted; ctx.lineWidth = 1.5; ctx.lineCap = "round"; ctx.lineJoin = "round"
            ctx.beginPath(); ctx.moveTo(1, 2); ctx.lineTo(width / 2, height - 1); ctx.lineTo(width - 1, 2); ctx.stroke()
        }
    }

    background: Rectangle {
        radius: Theme.radiusInput
        color: control.enabled ? (control.hovered ? Theme.panelHover : Theme.panelSecondary) : Theme.disabledBg
        border.width: control.activeFocus || control.popup.visible ? 2 : 1
        border.color: control.activeFocus || control.popup.visible ? Theme.focusRing : control.hovered ? Theme.borderStrong : Theme.border
        Behavior on color { ColorAnimation { duration: 120 } }
    }

    delegate: ItemDelegate {
        id: option
        required property int index
        required property var model
        width: ListView.view ? ListView.view.width : control.width
        height: Math.max(Theme.buttonHeight + 2, optionLabel.implicitHeight + control.optionVerticalPadding * 2)
        leftPadding: control.optionHorizontalPadding
        rightPadding: control.optionHorizontalPadding
        topPadding: control.optionVerticalPadding
        bottomPadding: control.optionVerticalPadding
        text: control.optionText(index)
        font: control.font
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        Accessible.name: text

        contentItem: Label {
            id: optionLabel
            text: option.text
            color: Theme.text
            font: option.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            maximumLineCount: 1
            clip: true
        }
        background: Rectangle {
            color: option.down ? Theme.overlayPressed : option.highlighted || option.hovered ? Theme.hover : Theme.transparent
            radius: Theme.radiusSm
        }
    }

    popup: Popup {
        id: dropdownPopup
        objectName: control.objectName.length > 0 ? control.objectName + "Popup" : "appComboPopup"
        readonly property int desiredHeight: Math.min(control.popupMaxHeight, optionList.contentHeight + topPadding + bottomPadding)
        readonly property int availableBelow: Math.max(0, control.Window.height - control._windowY - control.popupEdgeMargin)
        readonly property int availableAbove: Math.max(0, control._windowY - control.height - control.popupEdgeMargin)
        readonly property bool opensAbove: desiredHeight > availableBelow && availableAbove > availableBelow

        x: 0
        y: opensAbove ? -height - 4 : control.height + 4
        width: Math.min(Math.max(control.width, 120), Math.max(120, control.Window.width - control.popupEdgeMargin * 2))
        height: Math.max(0, Math.min(desiredHeight, opensAbove ? availableAbove : availableBelow))
        padding: 6
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside | Popup.CloseOnReleaseOutside
        onAboutToShow: x = control.popupXFor(width)
        onOpened: optionList.currentIndex = control.highlightedIndex

        background: Rectangle {
            color: Theme.panelAlt
            border.width: 1
            border.color: Theme.borderStrong
            radius: Theme.radiusInput + 2
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
