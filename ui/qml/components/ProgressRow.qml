import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ColumnLayout {
    id: root
    property real value: 0
    property bool active: false
    property bool highLoadMode: false
    property real shimmerPhase: 0
    property color fillColor: Theme.statusRunning
    property string percentText: ""
    property string etaText: ""
    property string speedText: ""

    spacing: Theme.space1

    ShimmerBar {
        Layout.fillWidth: true
        Layout.preferredHeight: 8
        value: root.value
        active: root.active
        highLoadMode: root.highLoadMode
        shimmerPhase: root.shimmerPhase
        fillColor: root.fillColor
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space2

        Label {
            text: root.percentText.length > 0 ? root.percentText : Math.round(Math.max(0, Math.min(root.value, 1)) * 100) + "%"
            color: Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontSizeXs
        }

        Label {
            text: root.etaText
            visible: root.etaText.length > 0
            color: Theme.statusWarning
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontSizeXs
            elide: Text.ElideRight
        }

        Item { Layout.fillWidth: true }

        Label {
            text: root.speedText
            visible: root.speedText.length > 0
            color: Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontSizeXs
            elide: Text.ElideRight
        }
    }
}
