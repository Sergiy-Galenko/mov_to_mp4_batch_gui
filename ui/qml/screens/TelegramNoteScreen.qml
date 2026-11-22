import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import App 1.0
import "../components"
import "../layout" as AppLayout

ScrollView {
    id: root
    property var appRoot

    property string sourcePath: ""
    property var mediaInfo: ({})
    property real trimStart: 0.0
    property real trimEnd: 0.0
    property int selectedResolution: 480
    property string cropMode: "center"
    property string selectedBitrate: "1400k"
    property bool burnCircle: false
    property bool circularPreview: true
    property bool audioEnabled: true
    property real volumeBoost: 1.0
    property string lastOutputPath: ""
    property string statusMessage: ""
    property bool statusIsError: false

    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    readonly property bool hasMedia: sourcePath.length > 0 && !!mediaInfo.valid
    readonly property real mediaDuration: mediaInfo && mediaInfo.duration ? Number(mediaInfo.duration) : 0.0
    readonly property real selectedDuration: Math.max(0.0, trimEnd - trimStart)
    readonly property bool isBusy: !!(backend && backend.telegramNote && backend.telegramNote.busy)
    readonly property int jobProgress: backend && backend.telegramNote ? backend.telegramNote.progress : 0

    function loadSource(path) {
        if (!path) return
        sourcePath = path
        lastOutputPath = ""
        statusMessage = ""
        statusIsError = false
        if (backend && backend.telegramNote) {
            var info = backend.telegramNote.inspect(path)
            applyMediaInfo(info)
        }
    }

    function applyMediaInfo(info) {
        mediaInfo = info || {}
        var dur = mediaInfo.duration ? Number(mediaInfo.duration) : 0.0
        trimStart = 0.0
        trimEnd = dur > 0 ? Math.min(60.0, dur) : 60.0
        if (player.playbackState === MediaPlayer.PlayingState) {
            player.pause()
        }
        player.source = sourcePath ? ("file://" + sourcePath) : ""
    }

    function formatTimecode(secs) {
        if (isNaN(secs) || secs < 0) secs = 0
        var s = Math.floor(secs)
        var ms = Math.floor((secs - s) * 10)
        var m = Math.floor(s / 60)
        var remSec = s % 60
        var mStr = (m < 10 ? "0" : "") + m
        var sStr = (remSec < 10 ? "0" : "") + remSec
        return mStr + ":" + sStr + "." + ms
    }

    function buildOptions() {
        return {
            "start_time": trimStart,
            "end_time": trimEnd,
            "resolution": selectedResolution,
            "crop_mode": cropMode,
            "bitrate": selectedBitrate,
            "burn_circle": burnCircle,
            "audio_enabled": audioEnabled,
            "volume_boost": volumeBoost
        }
    }

    function renderNote() {
        if (!sourcePath || !backend || !backend.telegramNote) return
        statusMessage = "Рендеринг кружечка для Telegram..."
        statusIsError = false
        var opts = buildOptions()
        backend.telegramNote.render(sourcePath, "", opts)
    }

    function addToConversionQueue() {
        if (!sourcePath || !backend || !backend.telegramNote) return
        var opts = buildOptions()
        var ok = backend.telegramNote.addToQueue(sourcePath, opts)
        if (ok) {
            statusMessage = "Додано до загальної черги конвертації!"
            statusIsError = false
        } else {
            statusMessage = "Не вдалося додати до черги."
            statusIsError = true
        }
    }

    Connections {
        target: backend ? backend.telegramNote : null
        ignoreUnknownSignals: true

        function onFileInspected(info) {
            root.applyMediaInfo(info)
        }

        function onCompleted(res) {
            if (res && res.ok) {
                root.lastOutputPath = res.output_path || ""
                root.statusMessage = I18n.t("telegram_note_rendered_success") + " (" + (res.size_mb || 0) + " MB)"
                root.statusIsError = false
            }
        }

        function onErrorChanged() {
            if (backend && backend.telegramNote && backend.telegramNote.error) {
                root.statusMessage = backend.telegramNote.error
                root.statusIsError = true
            }
        }
    }

    MediaPlayer {
        id: player
        videoOutput: cropMode === "blur_pad" ? fgVideoOutput : singleVideoOutput
        audioOutput: AudioOutput {
            muted: !root.audioEnabled
            volume: Math.min(1.0, root.volumeBoost)
        }

        onPositionChanged: {
            if (root.trimEnd > 0 && position >= (root.trimEnd * 1000)) {
                position = root.trimStart * 1000
            }
        }
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: Theme.space4
        Layout.leftMargin: Theme.space4
        Layout.rightMargin: Theme.space4

        // Top Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 70
            color: Theme.windowBackground

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space4
                anchors.rightMargin: Theme.space4
                spacing: Theme.space3

                Rectangle {
                    width: 44
                    height: 44
                    radius: 22
                    color: "#18222D"
                    border.width: 1
                    border.color: "#2AABEE"

                    AppIcon {
                        anchors.centerIn: parent
                        name: "telegram"
                        iconColor: "#2AABEE"
                        width: 24
                        height: 24
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label {
                        text: I18n.t("nav_telegram_note")
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontHeading
                        font.weight: Font.DemiBold
                    }
                    Label {
                        text: I18n.t("telegram_note_subtitle")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontMeta
                    }
                }

                AppButton {
                    iconName: "folder"
                    text: I18n.t("telegram_note_select_file")
                    onClicked: {
                        if (backend && backend.telegramNote) {
                            var chosen = backend.telegramNote.chooseVideoFile()
                            if (chosen) root.loadSource(chosen)
                        }
                    }
                }
            }
        }

        // Duration constraint warning if applicable
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            radius: Theme.radiusMd
            color: root.selectedDuration > 60.0 ? "#4A1818" : "#1B2A38"
            border.width: 1
            border.color: root.selectedDuration > 60.0 ? "#E04040" : "#2AABEE"
            visible: root.hasMedia

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space3
                anchors.rightMargin: Theme.space3
                spacing: Theme.space2

                AppIcon {
                    name: "info"
                    iconColor: root.selectedDuration > 60.0 ? "#FF5555" : "#2AABEE"
                    width: 16
                    height: 16
                }

                Label {
                    Layout.fillWidth: true
                    text: root.selectedDuration > 60.0
                        ? I18n.t("telegram_note_duration_warning")
                        : ("Тривалість кружечка: " + (Math.round(root.selectedDuration * 10) / 10) + " с (Ліміт Telegram: 60.0 с) • Початок: " + root.formatTimecode(root.trimStart) + " • Кінець: " + root.formatTimecode(root.trimEnd))
                    color: root.selectedDuration > 60.0 ? "#FF9999" : Theme.textPrimary
                    font.pixelSize: Theme.fontSizeSm
                }

                AppButton {
                    text: "Клепати до 60 с"
                    visible: root.selectedDuration > 60.0
                    onClicked: {
                        root.trimEnd = Math.min(root.mediaDuration, root.trimStart + 60.0)
                    }
                }
            }
        }

        // Two Column Main Section
        GridLayout {
            Layout.fillWidth: true
            columns: root.width >= 960 ? 2 : 1
            columnSpacing: Theme.space4
            rowSpacing: Theme.space4

            // Left Column: 1:1 Preview Player & Timeline Trimmer
            Card {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                title: "Попередній перегляд (1:1)"

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space3

                    // Square Player Viewport
                    Rectangle {
                        id: playerContainer
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(380, root.width - 64)
                        Layout.preferredHeight: Layout.preferredWidth
                        color: "#0B0E14"
                        radius: Theme.radiusLg
                        border.width: 1
                        border.color: Theme.borderMuted
                        clip: true

                        DropArea {
                            anchors.fill: parent
                            onDropped: function(drop) {
                                if (drop.hasUrls && drop.urls.length > 0) {
                                    var u = String(drop.urls[0])
                                    var p = u.replace(/^file:\/\//, "")
                                    root.loadSource(p)
                                    drop.acceptProposedAction()
                                }
                            }
                        }

                        // When Blur Pad mode is selected: blurred background + centered video
                        Item {
                            anchors.fill: parent
                            visible: root.hasMedia && root.cropMode === "blur_pad"

                            VideoOutput {
                                id: bgVideoOutput
                                anchors.fill: parent
                                fillMode: VideoOutput.PreserveAspectCrop
                                opacity: 0.35
                            }

                            VideoOutput {
                                id: fgVideoOutput
                                anchors.fill: parent
                                fillMode: VideoOutput.PreserveAspectFit
                            }
                        }

                        // When Center Crop mode is selected: crop to fill square
                        Item {
                            anchors.fill: parent
                            visible: root.hasMedia && root.cropMode !== "blur_pad"

                            VideoOutput {
                                id: singleVideoOutput
                                anchors.fill: parent
                                fillMode: VideoOutput.PreserveAspectCrop
                            }
                        }

                        // Empty State Placeholder
                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: Theme.space3
                            visible: !root.hasMedia

                            AppIcon {
                                Layout.alignment: Qt.AlignHCenter
                                name: "telegram"
                                iconColor: Theme.textSecondary
                                width: 48
                                height: 48
                            }

                            Label {
                                text: I18n.t("telegram_note_no_file")
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontSizeSm
                                horizontalAlignment: Text.AlignHCenter
                            }

                            AppButton {
                                Layout.alignment: Qt.AlignHCenter
                                text: I18n.t("telegram_note_select_file")
                                iconName: "folder"
                                onClicked: {
                                    if (backend && backend.telegramNote) {
                                        var chosen = backend.telegramNote.chooseVideoFile()
                                        if (chosen) root.loadSource(chosen)
                                    }
                                }
                            }
                        }

                        // Circular Telegram Overlay Mask
                        Canvas {
                            id: circleMaskCanvas
                            anchors.fill: parent
                            visible: root.circularPreview
                            antialiasing: true

                            onPaint: {
                                var ctx = getContext("2d")
                                var w = width
                                var h = height
                                var r = Math.min(w, h) / 2.0
                                var cx = w / 2.0
                                var cy = h / 2.0

                                ctx.clearRect(0, 0, w, h)

                                // Draw dark mask outside the circle
                                ctx.save()
                                ctx.beginPath()
                                ctx.rect(0, 0, w, h)
                                ctx.arc(cx, cy, r - 1, 0, Math.PI * 2, true)
                                ctx.closePath()
                                ctx.fillStyle = "#DD000000"
                                ctx.fill()
                                ctx.restore()

                                // Draw subtle blue Telegram circular border
                                ctx.beginPath()
                                ctx.arc(cx, cy, r - 1.5, 0, Math.PI * 2, false)
                                ctx.strokeStyle = "#2AABEE"
                                ctx.lineWidth = 2.0
                                ctx.stroke()
                            }

                            onWidthChanged: requestPaint()
                            onHeightChanged: requestPaint()
                        }

                        // Play/Pause Click Handler Overlay
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            enabled: root.hasMedia
                            onClicked: {
                                if (player.playbackState === MediaPlayer.PlayingState) {
                                    player.pause()
                                } else {
                                    if (player.position < root.trimStart * 1000 || player.position >= root.trimEnd * 1000) {
                                        player.position = root.trimStart * 1000
                                    }
                                    player.play()
                                }
                            }
                        }
                    }

                    // Transport Bar & Preview Toggle
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space2

                        AppButton {
                            iconName: player.playbackState === MediaPlayer.PlayingState ? "close" : "sort"
                            text: player.playbackState === MediaPlayer.PlayingState ? "Пауза" : "Відтворити"
                            enabled: root.hasMedia
                            onClicked: {
                                if (player.playbackState === MediaPlayer.PlayingState) {
                                    player.pause()
                                } else {
                                    if (player.position < root.trimStart * 1000 || player.position >= root.trimEnd * 1000) {
                                        player.position = root.trimStart * 1000
                                    }
                                    player.play()
                                }
                            }
                        }

                        AppButton {
                            text: "На початок"
                            enabled: root.hasMedia
                            onClicked: {
                                player.position = root.trimStart * 1000
                            }
                        }

                        Item { Layout.fillWidth: true }

                        AppSwitch {
                            id: previewSwitch
                            text: I18n.t("telegram_note_circular_preview")
                            checked: root.circularPreview
                            onToggled: root.circularPreview = checked
                        }
                    }

                    // Timeline Trimmer Section
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 120
                        color: Theme.windowBackground
                        radius: Theme.radiusMd
                        border.width: 1
                        border.color: Theme.borderMuted
                        visible: root.hasMedia

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.space3
                            spacing: Theme.space2

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "Обрізка (Початок / Кінець):"
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontMeta
                                    font.weight: Font.DemiBold
                                }
                                Item { Layout.fillWidth: true }
                                Label {
                                    text: root.formatTimecode(root.trimStart) + " — " + root.formatTimecode(root.trimEnd)
                                    color: "#2AABEE"
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontMeta
                                    font.weight: Font.DemiBold
                                }
                            }

                            // Start slider
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space2

                                Label {
                                    text: "In:"
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontMeta
                                    Layout.preferredWidth: 26
                                }

                                Slider {
                                    id: startSlider
                                    Layout.fillWidth: true
                                    from: 0.0
                                    to: Math.max(0.1, root.mediaDuration)
                                    value: root.trimStart
                                    stepSize: 0.1
                                    onMoved: {
                                        root.trimStart = value
                                        if (root.trimEnd < root.trimStart + 0.5) {
                                            root.trimEnd = Math.min(root.mediaDuration, root.trimStart + 0.5)
                                        }
                                        if (root.trimEnd - root.trimStart > 60.0) {
                                            root.trimEnd = Math.min(root.mediaDuration, root.trimStart + 60.0)
                                        }
                                        player.position = root.trimStart * 1000
                                    }
                                }

                                Label {
                                    text: root.formatTimecode(root.trimStart)
                                    color: Theme.textPrimary
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontMeta
                                    Layout.preferredWidth: 64
                                }
                            }

                            // End slider
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space2

                                Label {
                                    text: "Out:"
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontMeta
                                    Layout.preferredWidth: 26
                                }

                                Slider {
                                    id: endSlider
                                    Layout.fillWidth: true
                                    from: 0.0
                                    to: Math.max(0.1, root.mediaDuration)
                                    value: root.trimEnd
                                    stepSize: 0.1
                                    onMoved: {
                                        root.trimEnd = value
                                        if (root.trimStart > root.trimEnd - 0.5) {
                                            root.trimStart = Math.max(0.0, root.trimEnd - 0.5)
                                        }
                                        if (root.trimEnd - root.trimStart > 60.0) {
                                            root.trimStart = Math.max(0.0, root.trimEnd - 60.0)
                                        }
                                        player.position = root.trimEnd * 1000
                                    }
                                }

                                Label {
                                    text: root.formatTimecode(root.trimEnd)
                                    color: Theme.textPrimary
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontMeta
                                    Layout.preferredWidth: 64
                                }
                            }
                        }
                    }
                }
            }

            // Right Column: Settings & Export
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: Theme.space4

                // Source Info Card
                Card {
                    Layout.fillWidth: true
                    title: "Інформація про файл"
                    visible: root.hasMedia

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space2

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Файл:"; color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; Layout.preferredWidth: 90 }
                            Label { text: root.mediaInfo.file_name || ""; color: Theme.textPrimary; font.weight: Font.DemiBold; elide: Text.ElideMiddle; Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Роздільність:"; color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; Layout.preferredWidth: 90 }
                            Label { text: (root.mediaInfo.width || 0) + "x" + (root.mediaInfo.height || 0) + " (" + (root.mediaInfo.fps || 30) + " fps)"; color: Theme.textPrimary; font.family: Theme.monoFont }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Тривалість:"; color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; Layout.preferredWidth: 90 }
                            Label { text: root.formatTimecode(root.mediaDuration) + " (" + (root.mediaInfo.size_mb || 0) + " МБ)"; color: Theme.textPrimary; font.family: Theme.monoFont }
                        }
                    }
                }

                // Telegram Note Settings Card
                Card {
                    Layout.fillWidth: true
                    title: "Параметри кружечка"

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space3

                        // Cropping Mode
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Label { text: I18n.t("telegram_note_crop_mode"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space2

                                AppButton {
                                    Layout.fillWidth: true
                                    text: I18n.t("telegram_note_crop_center")
                                    variant: root.cropMode === "center" ? "primary" : "secondary"
                                    onClicked: root.cropMode = "center"
                                }

                                AppButton {
                                    Layout.fillWidth: true
                                    text: I18n.t("telegram_note_crop_blur")
                                    variant: root.cropMode === "blur_pad" ? "primary" : "secondary"
                                    onClicked: root.cropMode = "blur_pad"
                                }
                            }
                        }

                        // Target Resolution
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Label { text: I18n.t("telegram_note_resolution"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm }
                            AppComboBox {
                                id: resBox
                                Layout.fillWidth: true
                                model: ["480x480 (Оптимально для Telegram)", "384x384 (Стандартний Telegram)", "640x640 (HD Кружечок)"]
                                currentIndex: 0
                                onActivated: {
                                    if (index === 0) root.selectedResolution = 480
                                    else if (index === 1) root.selectedResolution = 384
                                    else if (index === 2) root.selectedResolution = 640
                                }
                            }
                        }

                        // Video Bitrate
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Label { text: I18n.t("telegram_note_quality"); color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm }
                            AppComboBox {
                                id: bitrateBox
                                Layout.fillWidth: true
                                model: ["1400 kbps (Рекомендовано)", "1000 kbps (Компактний)", "2000 kbps (Високий бітрейт)"]
                                currentIndex: 0
                                onActivated: {
                                    if (index === 0) root.selectedBitrate = "1400k"
                                    else if (index === 1) root.selectedBitrate = "1000k"
                                    else if (index === 2) root.selectedBitrate = "2000k"
                                }
                            }
                        }

                        // Audio Settings
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            RowLayout {
                                Layout.fillWidth: true
                                AppSwitch {
                                    text: "Звукова доріжка (AAC 128k)"
                                    checked: root.audioEnabled
                                    onToggled: root.audioEnabled = checked
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                visible: root.audioEnabled
                                spacing: Theme.space2

                                Label {
                                    text: I18n.t("telegram_note_audio_boost") + " (" + Math.round(root.volumeBoost * 100) + "%):"
                                    color: Theme.textSecondary
                                    font.pixelSize: Theme.fontSizeSm
                                }

                                Slider {
                                    Layout.fillWidth: true
                                    from: 0.5
                                    to: 2.0
                                    value: root.volumeBoost
                                    stepSize: 0.1
                                    onMoved: root.volumeBoost = value
                                }
                            }
                        }

                        // Burn Circle Matte Option
                        AppSwitch {
                            text: I18n.t("telegram_note_burn_circle")
                            checked: root.burnCircle
                            onToggled: root.burnCircle = checked
                        }
                    }
                }

                // Action & Rendering Box
                Card {
                    Layout.fillWidth: true
                    title: "Експорт"

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space3

                        // Progress indicator during rendering
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            visible: root.isBusy

                            AppProgressBar {
                                Layout.fillWidth: true
                                value: root.jobProgress / 100.0
                            }

                            Label {
                                text: "Створення кружечка: " + root.jobProgress + "%"
                                color: "#2AABEE"
                                font.pixelSize: Theme.fontMeta
                            }
                        }

                        // Status message
                        Label {
                            Layout.fillWidth: true
                            visible: root.statusMessage.length > 0
                            text: root.statusMessage
                            color: root.statusIsError ? "#FF5555" : "#34C759"
                            font.pixelSize: Theme.fontSizeSm
                            wrapMode: Text.WordWrap
                        }

                        // Action buttons
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space2

                            PrimaryButton {
                                text: I18n.t("telegram_note_render")
                                iconName: "telegram"
                                enabled: root.hasMedia && !root.isBusy
                                onClicked: root.renderNote()
                            }

                            SecondaryButton {
                                text: I18n.t("telegram_note_add_queue")
                                iconName: "plus"
                                enabled: root.hasMedia && !root.isBusy
                                onClicked: root.addToConversionQueue()
                            }
                        }

                        AppButton {
                            Layout.fillWidth: true
                            text: I18n.t("telegram_note_open_folder")
                            iconName: "folder"
                            visible: root.lastOutputPath.length > 0
                            onClicked: {
                                if (backend && backend.telegramNote && root.lastOutputPath) {
                                    backend.telegramNote.openInFolder(root.lastOutputPath)
                                }
                            }
                        }
                    }
                }
            }
        }

        Item { Layout.preferredHeight: Theme.space5 }
    }
}
