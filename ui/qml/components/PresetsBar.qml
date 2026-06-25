import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Item {
    id: root
    property var model: null
    property string activePreset: ""
    signal presetSelected(string name)

    implicitHeight: 42

    function iconFor(name) {
        if (name.indexOf("YouTube") >= 0) return "YT"
        if (name.indexOf("TikTok") >= 0) return "TT"
        if (name.indexOf("Instagram") >= 0) return "IG"
        if (name.indexOf("Telegram") >= 0) return "TG"
        if (name.indexOf("WhatsApp") >= 0) return "WA"
        if (name.indexOf("Twitter") >= 0 || name.indexOf("X/") >= 0) return "X"
        if (name.indexOf("LinkedIn") >= 0) return "IN"
        if (name.indexOf("Discord") >= 0) return "DC"
        if (name.indexOf("AV1") >= 0) return "A1"
        if (name.indexOf("H.265") >= 0) return "H5"
        if (name.indexOf("H.264") >= 0) return "H4"
        return "FF"
    }

    function detailsFor(name) {
        if (name.indexOf("X/Twitter") >= 0) return "H.264, 1080p, 160k audio"
        if (name.indexOf("LinkedIn") >= 0) return "H.264, 1080p, 192k audio"
        if (name.indexOf("Discord") >= 0) return "H.264, 720p compact"
        if (name.indexOf("YouTube") >= 0) return "H.264, 1080p, 192k audio"
        if (name.indexOf("TikTok") >= 0 || name.indexOf("Reels") >= 0) return "H.264, 9:16 vertical"
        if (name.indexOf("VP9") >= 0) return "WebM, VP9"
        if (name.indexOf("AV1") >= 0) return "AV1 target"
        return I18n.t("click_load_preset")
    }

    ListView {
        anchors.fill: parent
        orientation: ListView.Horizontal
        model: root.model
        spacing: 8
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        cacheBuffer: 180

        delegate: Rectangle {
            id: chip
            property string presetName: model.display || modelData || ""
            width: Math.max(92, label.implicitWidth + 44)
            height: 32
            radius: Theme.radiusPill
            color: root.activePreset === presetName ? Theme.accentPrimary : (mouse.containsMouse ? Theme.bgElevated : "transparent")
            border.width: 1
            border.color: root.activePreset === presetName ? Theme.accentPrimary : Theme.bgBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 7

                Label {
                    text: root.iconFor(chip.presetName)
                    color: root.activePreset === chip.presetName ? "#FFFFFF" : Theme.accentPrimary
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontMeta
                    font.bold: true
                }

                Label {
                    id: label
                    Layout.fillWidth: true
                    text: chip.presetName
                    color: root.activePreset === chip.presetName ? "#FFFFFF" : Theme.textSecondary
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideRight
                }
            }

            MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked: root.presetSelected(chip.presetName)
            }

            ToolTip.visible: mouse.containsMouse
            ToolTip.delay: 350
            ToolTip.text: root.detailsFor(chip.presetName)
        }
    }
}
