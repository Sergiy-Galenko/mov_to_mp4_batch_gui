import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root

    property string mainFilePath: ""
    property string mainFileName: ""
    property real mainDuration: 0.0
    property int mainWidth: 1920
    property int mainHeight: 1080
    property real mainFps: 30.0
    property var timelineClips: []
    property string bgMusicPath: ""

    signal clipActivated(string path, string type)
    signal clipAddRequested(string path, string type)
    signal importRequested()

    property int activeFilter: 0 // 0: All, 1: Video, 2: Audio, 3: Titles
    property string searchQuery: ""
    property bool isGridView: true

    implicitWidth: 320
    implicitHeight: 320
    color: "#161618"
    radius: Theme.radiusMd
    border.width: 1
    border.color: "#27272a"
    clip: true

    function formatTime(secs) {
        if (isNaN(secs) || secs < 0) secs = 0
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s
    }

    function fileNameOf(path) {
        if (!path) return ""
        var slash = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"))
        return slash >= 0 ? path.slice(slash + 1) : path
    }

    // Consolidated media items
    readonly property var mediaItems: {
        function isImage(p) {
            if (!p) return false
            var ext = p.slice(p.lastIndexOf(".")).toLowerCase()
            return [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif", ".jxl"].indexOf(ext) >= 0
        }

        var items = []
        if (root.mainFilePath) {
            var mainIsImg = isImage(root.mainFilePath)
            items.push({
                id: "main",
                title: root.mainFileName || fileNameOf(root.mainFilePath),
                path: root.mainFilePath,
                type: mainIsImg ? "image" : "video",
                duration: root.mainDuration,
                resolution: (root.mainHeight >= 2160 ? "4K" : root.mainHeight >= 1080 ? "1080p" : "720p"),
                fps: mainIsImg ? 0 : root.mainFps,
                tagColor: mainIsImg ? "#06b6d4" : "#3b82f6" // Cyan for photos, Blue for videos
            })
        }
        for (var i = 0; i < root.timelineClips.length; i++) {
            var c = root.timelineClips[i]
            var p = c.source_path || ""
            var clipIsImg = isImage(p) || (c.media_type === "image")
            items.push({
                id: "clip_" + i,
                title: fileNameOf(p),
                path: p,
                type: clipIsImg ? "image" : "video",
                duration: (c.out_point || (clipIsImg ? 5 : 10)) - (c.in_point || 0),
                resolution: "1080p",
                fps: clipIsImg ? 0 : 30.0,
                tagColor: clipIsImg ? "#06b6d4" : "#f97316"
            })
        }
        if (root.bgMusicPath) {
            items.push({
                id: "bgm",
                title: fileNameOf(root.bgMusicPath),
                path: root.bgMusicPath,
                type: "audio",
                duration: 180,
                resolution: "Stereo",
                fps: 0,
                tagColor: "#10b981" // Green
            })
        }
        // Template title cards
        items.push({
            id: "title_lower_third",
            title: "Нижня плашка (Lower Third)",
            path: "template:lower_third",
            type: "title",
            duration: 5,
            resolution: "Overlay",
            fps: 0,
            tagColor: "#a855f7" // Purple
        })
        items.push({
            id: "title_cinematic",
            title: "Кінематографічний вступ",
            path: "template:cinematic_intro",
            type: "title",
            duration: 8,
            resolution: "Overlay",
            fps: 0,
            tagColor: "#a855f7"
        })

        // Filtering
        var filtered = []
        for (var k = 0; k < items.length; k++) {
            var it = items[k]
            if (root.activeFilter === 1 && it.type !== "video") continue
            if (root.activeFilter === 1 && it.type !== "video" && it.type !== "image") continue
            if (root.activeFilter === 2 && it.type !== "audio") continue
            if (root.activeFilter === 3 && it.type !== "title") continue
            if (root.searchQuery.trim().length > 0) {
                if (it.title.toLowerCase().indexOf(root.searchQuery.toLowerCase()) < 0) continue
            }
            filtered.push(it)
        }
        return filtered
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        // Header: Title & Filter Tabs
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            AppIcon {
                name: "folder"
                Layout.preferredWidth: 16
                Layout.preferredHeight: 16
                iconColor: "#f59e0b"
            }

            Label {
                text: "Media Pool"
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontSizeSm
                font.bold: true
                color: Theme.textPrimary
            }

            Item { Layout.fillWidth: true }

            SecondaryButton {
                text: "+ Import"
                Layout.preferredHeight: 24
                font.pixelSize: 11
                onClicked: root.importRequested()
            }
        }

        // Category Filter Tabs & View Toggle
        RowLayout {
            Layout.fillWidth: true
            spacing: 4

            Repeater {
                model: ["Все", "Відео", "Аудіо", "Титри"]
                delegate: Rectangle {
                    required property int index
                    required property string modelData
                    Layout.preferredHeight: 22
                    Layout.preferredWidth: filterLabel.implicitWidth + 12
                    radius: 4
                    color: root.activeFilter === index ? "#3f3f46" : "#27272a"
                    border.width: 1
                    border.color: root.activeFilter === index ? "#71717a" : "transparent"

                    Label {
                        id: filterLabel
                        anchors.centerIn: parent
                        text: modelData
                        font.pixelSize: 10
                        font.weight: root.activeFilter === index ? Font.DemiBold : Font.Normal
                        color: root.activeFilter === index ? "#ffffff" : "#a1a1aa"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.activeFilter = index
                    }
                }
            }

            Item { Layout.fillWidth: true }

            AppIconButton {
                iconName: root.isGridView ? "grid" : "queue"
                accessibleLabel: "Вигляд сіткою / списком"
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                onClicked: root.isGridView = !root.isGridView
            }
        }

        // Search Box
        AppTextField {
            Layout.fillWidth: true
            placeholderText: "Пошук медіафайлів..."
            search: true
            text: root.searchQuery
            onTextChanged: root.searchQuery = text
        }

        // Grid / List View of Clips
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            GridView {
                id: grid
                anchors.fill: parent
                cellWidth: root.isGridView ? 144 : width
                cellHeight: root.isGridView ? 116 : 46
                model: root.mediaItems

                delegate: Rectangle {
                    id: card
                    required property var modelData
                    required property int index
                    width: root.isGridView ? 138 : grid.width - 8
                    height: root.isGridView ? 110 : 40
                    radius: 6
                    color: cardMouse.containsMouse ? "#27272a" : "#1e1e22"
                    border.width: 1
                    border.color: cardMouse.containsMouse ? "#52525b" : "#2d2d32"

                    MouseArea {
                        id: cardMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onDoubleClicked: root.clipAddRequested(card.modelData.path, card.modelData.type)
                        onClicked: root.clipActivated(card.modelData.path, card.modelData.type)
                    }

                    // Grid layout card
                    ColumnLayout {
                        visible: root.isGridView
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 2

                        // Thumbnail Box
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 4
                            color: "#121214"
                            clip: true

                            // Video / photo snapshot if available
                            Image {
                                anchors.fill: parent
                                source: card.modelData.path && (card.modelData.type === "video" || card.modelData.type === "image") && !card.modelData.path.startsWith("template:") ? ("file://" + card.modelData.path) : ""
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                visible: status === Image.Ready
                            }

                            // Center Icon for Audio/Titles or when no snapshot
                            AppIcon {
                                anchors.centerIn: parent
                                name: card.modelData.type === "video" ? "film" : card.modelData.type === "image" ? "image" : card.modelData.type === "audio" ? "audio" : "text"
                                width: 22
                                height: 22
                                iconColor: card.modelData.tagColor
                                visible: card.modelData.type === "audio" || card.modelData.type === "title"
                            }

                            // Type tag indicator (Top Left)
                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.margins: 4
                                width: 6; height: 6; radius: 3
                                color: card.modelData.tagColor
                            }

                            // Duration badge (Bottom Right)
                            Rectangle {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: 3
                                width: durLabel.implicitWidth + 6
                                height: 14
                                radius: 2
                                color: "#cc000000"

                                Label {
                                    id: durLabel
                                    anchors.centerIn: parent
                                    text: root.formatTime(card.modelData.duration)
                                    font.pixelSize: 8
                                    font.family: Theme.monoFont
                                    color: "#ffffff"
                                }
                            }

                            // Resolution badge (Bottom Left)
                            Rectangle {
                                anchors.left: parent.left
                                anchors.bottom: parent.bottom
                                anchors.margins: 3
                                width: resLabel.implicitWidth + 6
                                height: 14
                                radius: 2
                                color: "#cc000000"

                                Label {
                                    id: resLabel
                                    anchors.centerIn: parent
                                    text: card.modelData.resolution
                                    font.pixelSize: 8
                                    color: "#a1a1aa"
                                }
                            }
                        }

                        // Title Text
                        Label {
                            Layout.fillWidth: true
                            text: card.modelData.title
                            font.pixelSize: 10
                            font.weight: Font.Medium
                            color: Theme.textPrimary
                            elide: Text.ElideMiddle
                        }
                    }

                    // List layout row
                    RowLayout {
                        visible: !root.isGridView
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 8

                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: card.modelData.tagColor
                        }

                        AppIcon {
                            name: card.modelData.type === "video" ? "film" : card.modelData.type === "image" ? "image" : card.modelData.type === "audio" ? "audio" : "text"
                            Layout.preferredWidth: 16
                            Layout.preferredHeight: 16
                            iconColor: card.modelData.tagColor
                        }

                        Label {
                            Layout.fillWidth: true
                            text: card.modelData.title
                            font.pixelSize: 11
                            color: Theme.textPrimary
                            elide: Text.ElideMiddle
                        }

                        Label {
                            text: card.modelData.resolution
                            font.pixelSize: 9
                            color: "#71717a"
                        }

                        Label {
                            text: root.formatTime(card.modelData.duration)
                            font.family: Theme.monoFont
                            font.pixelSize: 10
                            color: "#a1a1aa"
                        }

                        AppButton {
                            text: "+"
                            Layout.preferredHeight: 22
                            Layout.preferredWidth: 22
                            font.pixelSize: 12
                            onClicked: root.clipAddRequested(card.modelData.path, card.modelData.type)
                        }
                    }
                }
            }
        }
    }
}

