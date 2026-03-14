import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "components"

ApplicationWindow {
    id: root
    visible: true
    visibility: Window.Maximized
    title: backend ? backend.appTitle : "Media Converter"
    color: Theme.bg

    palette.window: Theme.bg
    palette.base: Theme.input
    palette.text: Theme.text
    palette.button: Theme.panel
    palette.buttonText: Theme.text
    palette.highlight: Theme.accent
    palette.highlightedText: "#FFFFFF"

    Rectangle {
        anchors.fill: parent
        z: -3
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.bgLift }
            GradientStop { position: 0.4; color: Theme.bg }
            GradientStop { position: 1.0; color: Theme.bgDeep }
        }
    }

    Rectangle {
        width: root.width * 0.42
        height: width
        radius: width / 2
        x: root.width - width * 0.72
        y: -width * 0.35
        z: -2
        color: Qt.rgba(1, 0.44, 0.25, 0.12)
    }

    Rectangle {
        width: root.width * 0.34
        height: width
        radius: width / 2
        x: -width * 0.28
        y: root.height * 0.18
        z: -2
        color: Qt.rgba(1, 0.70, 0.28, 0.08)
    }

    property real layoutWidth: Math.min(contentWrap.availableWidth, Theme.maxWidth)
    property int headerColumns: layoutWidth < 760 ? 1 : layoutWidth < 1080 ? 2 : 4
    property int dashboardColumns: layoutWidth < 700 ? 2 : 4
    property int workspaceColumns: layoutWidth < Theme.compactBreakpoint ? 1 : 2
    property real paneWidth: workspaceColumns === 1 ? layoutWidth : Math.max((layoutWidth - Theme.space2) / 2, 0)
    property int formColumns: paneWidth < 740 ? 1 : 2
    property int queueActionColumns: paneWidth < 440 ? 1 : paneWidth < 760 ? 2 : 4
    property int dualActionColumns: paneWidth < 560 ? 1 : 2
    property int tripleActionColumns: paneWidth < 540 ? 1 : paneWidth < 760 ? 2 : 3
    property int presetColumns: paneWidth < 560 ? 1 : paneWidth < 980 ? 2 : 3
    property int statusColumns: layoutWidth < 560 ? 1 : layoutWidth < 900 ? 2 : layoutWidth < 1160 ? 3 : 5
    property bool compact: formColumns === 1
    property bool hasBackend: backend !== null
    property var selectedQueue: []
    property int currentTab: 0
    property string inheritLabel: "За замовчуванням"
    property bool queueEmpty: queueList.count === 0
    property var operationTabs: ["Старт", "Відео", "Фото", "Аудіо", "Субтитри", "Проєкт", "Система"]
    property var operationOptions: [
        "Конвертація",
        "Лише аудіо",
        "Авто субтитри",
        "Extract subtitle",
        "Burn-in subtitle",
        "Thumbnail",
        "Contact sheet"
    ]
    property var operationQuickCards: [
        { name: "Конвертація", title: "Відео", meta: "Перекодування, resize, crop, watermark" },
        { name: "Лише аудіо", title: "Аудіо", meta: "Витяг доріжки, normalize, cover art" },
        { name: "Авто субтитри", title: "AI субтитри", meta: "Whisper transcription у SRT/VTT" },
        { name: "Extract subtitle", title: "Extract subtitle", meta: "Витяг вбудованої subtitle доріжки" },
        { name: "Burn-in subtitle", title: "Burn-in subtitle", meta: "Вшити субтитри у відео" },
        { name: "Thumbnail", title: "Thumbnail", meta: "Один кадр у JPG/PNG/WebP" },
        { name: "Contact sheet", title: "Contact sheet", meta: "Лист із кількох кадрів" }
    ]
    property var platformPresetCards: [
        { name: "YouTube • 1080p H.264", title: "YouTube", meta: "16:9 • MP4 • H.264", badge: "1080p" },
        { name: "TikTok • 9:16", title: "TikTok", meta: "9:16 • MP4 • Fast", badge: "Vertical" },
        { name: "Instagram Reels • 9:16", title: "Reels", meta: "9:16 • MP4 • Social", badge: "Reel" },
        { name: "Instagram Stories • 9:16", title: "Stories", meta: "9:16 • Crop • Quick", badge: "Story" },
        { name: "Telegram • Compact MP4", title: "Telegram", meta: "720p • Compact • Share", badge: "Light" },
        { name: "WhatsApp • Share MP4", title: "WhatsApp", meta: "480p • Small size", badge: "Mobile" }
    ]
    property var videoFormats: ["mp4", "mkv", "webm", "mov", "avi", "gif"]
    property var imageFormats: ["jpg", "png", "webp", "bmp", "tiff"]
    property var audioFormats: ["mp3", "m4a", "aac", "wav", "flac", "opus"]
    property var subtitleFormats: ["srt", "ass", "vtt"]
    property var codecOptions: ["Авто", "H.264 (AVC)", "H.265 (HEVC)", "AV1", "VP9 (WebM)"]
    property var hwOptions: ["Авто", "Тільки CPU", "NVIDIA (NVENC)", "Intel (QSV)", "AMD (AMF)"]
    property var normalizeOptions: ["none", "ebu_r128"]
    property var subtitleEngineOptions: ["auto", "whisper"]
    property var rotateOptions: ["0", "90° вправо", "90° вліво", "180°"]
    property var portraitOptions: [
        "Вимкнено",
        "9:16 (1080x1920) - crop",
        "9:16 (1080x1920) - blur",
        "9:16 (720x1280) - crop",
        "9:16 (720x1280) - blur"
    ]
    property var positionOptions: ["Верх-ліворуч", "Верх-праворуч", "Низ-ліворуч", "Низ-праворуч", "Центр"]
    property var subtitleModeOptions: ["none", "burn_in"]
    property var boolOverrideOptions: [inheritLabel, "Так", "Ні"]

    function toggleQueueIndex(idx, checked) {
        var pos = selectedQueue.indexOf(idx)
        if (checked && pos === -1) {
            selectedQueue.push(idx)
        } else if (!checked && pos !== -1) {
            selectedQueue.splice(pos, 1)
        }
    }

    function clearSelection() {
        selectedQueue = []
    }

    function statusColor(status) {
        if (status === "success")
            return Theme.success
        if (status === "failed")
            return Theme.danger
        if (status === "skipped")
            return Theme.warning
        if (status === "running")
            return Theme.running
        return Theme.muted
    }

    function statusSurfaceColor(status) {
        if (status === "success")
            return Theme.successSoft
        if (status === "failed")
            return Theme.dangerSoft
        if (status === "skipped")
            return Theme.warningSoft
        if (status === "running")
            return Theme.runningSoft
        return Theme.sectionAlt
    }

    function statusBorderColor(status) {
        if (status === "success")
            return Qt.rgba(0.18, 0.80, 0.60, 0.45)
        if (status === "failed")
            return Qt.rgba(1.0, 0.48, 0.54, 0.45)
        if (status === "skipped")
            return Qt.rgba(0.96, 0.77, 0.33, 0.45)
        if (status === "running")
            return Qt.rgba(0.33, 0.72, 1.0, 0.45)
        return Theme.border
    }

    function mediaGlyph(mediaType) {
        if (mediaType === "video")
            return "VID"
        if (mediaType === "image")
            return "IMG"
        return "MED"
    }

    function mediaColor(mediaType) {
        if (mediaType === "video")
            return Theme.running
        if (mediaType === "image")
            return Theme.accent2
        return Theme.muted
    }

    function collectSettings() {
        return {
            operation: operationCombo.currentText,
            out_video_fmt: outVideoFmt.currentText,
            out_image_fmt: outImageFmt.currentText,
            out_audio_fmt: outAudioFmt.currentText,
            out_subtitle_fmt: outSubtitleFmt.currentText,
            audio_bitrate: audioBitrateField.text,
            audio_track_index: audioTrackSpin.value - 1,
            crf: crfSpin.value,
            preset: presetCombo.currentText,
            portrait: portraitCombo.currentText,
            img_quality: imgQualitySpin.value,
            overwrite: overwriteCheck.checked,
            fast_copy: fastCopyCheck.checked,
            skip_existing: skipExistingCheck.checked,
            output_template: outputTemplateField.text,
            platform_profile: platformProfileField.text,
            trim_start: trimStartField.text,
            trim_end: trimEndField.text,
            merge: mergeCheck.checked,
            merge_name: mergeNameField.text,
            resize_w: resizeWField.text,
            resize_h: resizeHField.text,
            crop_w: cropWField.text,
            crop_h: cropHField.text,
            crop_x: cropXField.text,
            crop_y: cropYField.text,
            rotate: rotateCombo.currentText,
            speed: speedField.text,
            subtitle_mode: subtitleModeCombo.currentText,
            subtitle_path: subtitlePathField.text,
            subtitle_stream: subtitleStreamSpin.value,
            subtitle_out_fmt: outSubtitleFmt.currentText,
            subtitle_language: subtitleLanguageField.text,
            subtitle_model: subtitleModelCombo.currentText,
            subtitle_engine: subtitleEngineCombo.currentText,
            thumbnail_time: thumbnailTimeField.text,
            sheet_cols: sheetColsSpin.value,
            sheet_rows: sheetRowsSpin.value,
            sheet_width: sheetWidthSpin.value,
            sheet_interval: sheetIntervalSpin.value,
            wm_path: wmPathField.text,
            wm_pos: wmPosCombo.currentText,
            wm_opacity: wmOpacitySpin.value,
            wm_scale: wmScaleSpin.value,
            text_wm: textWatermarkField.text,
            text_pos: textPosCombo.currentText,
            text_size: textSizeSpin.value,
            text_color: textColorField.text,
            text_box: textBoxCheck.checked,
            text_box_color: textBoxColorField.text,
            text_box_opacity: textBoxOpacitySpin.value,
            text_font: textFontField.text,
            codec: codecCombo.currentText,
            hw: hwCombo.currentText,
            replace_audio_path: replaceAudioPathField.text,
            normalize_audio: normalizeAudioCombo.currentText,
            audio_peak_limit_db: peakLimitField.text,
            trim_silence: trimSilenceCheck.checked,
            silence_threshold_db: silenceThresholdSpin.value,
            silence_duration: silenceDurationField.text,
            split_chapters: splitChaptersCheck.checked,
            cover_art_path: coverArtField.text,
            before_hook: beforeHookField.text,
            after_hook: afterHookField.text,
            strip_metadata: stripMetadataCheck.checked,
            copy_metadata: copyMetadataCheck.checked,
            meta_title: metaTitleField.text,
            meta_comment: metaCommentField.text,
            meta_author: metaAuthorField.text,
            meta_copyright: metaCopyrightField.text,
            meta_album: metaAlbumField.text,
            meta_genre: metaGenreField.text,
            meta_year: metaYearField.text,
            meta_track: metaTrackField.text
        }
    }

    function setComboText(combo, value) {
        if (!combo || value === undefined || value === null)
            return
        var idx = combo.find(value)
        if (idx >= 0)
            combo.currentIndex = idx
    }

    function applyPreset(preset) {
        if (!preset)
            return
        if (preset.operation) setComboText(operationCombo, preset.operation)
        if (preset.out_video_fmt) setComboText(outVideoFmt, preset.out_video_fmt)
        if (preset.out_image_fmt) setComboText(outImageFmt, preset.out_image_fmt)
        if (preset.out_audio_fmt) setComboText(outAudioFmt, preset.out_audio_fmt)
        if (preset.out_subtitle_fmt) setComboText(outSubtitleFmt, preset.out_subtitle_fmt)
        if (preset.audio_bitrate) audioBitrateField.text = preset.audio_bitrate
        if (preset.audio_track_index !== undefined) audioTrackSpin.value = Number(preset.audio_track_index) + 1
        if (preset.crf !== undefined) crfSpin.value = preset.crf
        if (preset.preset) setComboText(presetCombo, preset.preset)
        if (preset.portrait) setComboText(portraitCombo, preset.portrait)
        if (preset.img_quality !== undefined) imgQualitySpin.value = preset.img_quality
        overwriteCheck.checked = !!preset.overwrite
        fastCopyCheck.checked = !!preset.fast_copy
        skipExistingCheck.checked = !!preset.skip_existing
        outputTemplateField.text = preset.output_template || "{stem}"
        platformProfileField.text = preset.platform_profile || ""
        trimStartField.text = preset.trim_start || ""
        trimEndField.text = preset.trim_end || ""
        mergeCheck.checked = !!preset.merge
        mergeNameField.text = preset.merge_name || "merged"
        resizeWField.text = preset.resize_w || ""
        resizeHField.text = preset.resize_h || ""
        cropWField.text = preset.crop_w || ""
        cropHField.text = preset.crop_h || ""
        cropXField.text = preset.crop_x || ""
        cropYField.text = preset.crop_y || ""
        if (preset.rotate) setComboText(rotateCombo, preset.rotate)
        speedField.text = preset.speed || "1.0"
        setComboText(subtitleModeCombo, preset.subtitle_mode || "none")
        subtitlePathField.text = preset.subtitle_path || ""
        if (preset.subtitle_stream !== undefined) subtitleStreamSpin.value = preset.subtitle_stream
        subtitleLanguageField.text = preset.subtitle_language || "auto"
        setComboText(subtitleModelCombo, preset.subtitle_model || "base")
        setComboText(subtitleEngineCombo, preset.subtitle_engine || "auto")
        thumbnailTimeField.text = preset.thumbnail_time || ""
        if (preset.sheet_cols !== undefined) sheetColsSpin.value = preset.sheet_cols
        if (preset.sheet_rows !== undefined) sheetRowsSpin.value = preset.sheet_rows
        if (preset.sheet_width !== undefined) sheetWidthSpin.value = preset.sheet_width
        if (preset.sheet_interval !== undefined) sheetIntervalSpin.value = preset.sheet_interval
        wmPathField.text = preset.wm_path || ""
        if (preset.wm_pos) setComboText(wmPosCombo, preset.wm_pos)
        if (preset.wm_opacity !== undefined) wmOpacitySpin.value = preset.wm_opacity
        if (preset.wm_scale !== undefined) wmScaleSpin.value = preset.wm_scale
        textWatermarkField.text = preset.text_wm || ""
        if (preset.text_pos) setComboText(textPosCombo, preset.text_pos)
        if (preset.text_size !== undefined) textSizeSpin.value = preset.text_size
        textColorField.text = preset.text_color || "white"
        textBoxCheck.checked = !!preset.text_box
        textBoxColorField.text = preset.text_box_color || "black"
        if (preset.text_box_opacity !== undefined) textBoxOpacitySpin.value = preset.text_box_opacity
        textFontField.text = preset.text_font || ""
        if (preset.codec) setComboText(codecCombo, preset.codec)
        if (preset.hw) setComboText(hwCombo, preset.hw)
        replaceAudioPathField.text = preset.replace_audio_path || ""
        setComboText(normalizeAudioCombo, preset.normalize_audio || "none")
        peakLimitField.text = preset.audio_peak_limit_db || ""
        trimSilenceCheck.checked = !!preset.trim_silence
        silenceThresholdSpin.value = preset.silence_threshold_db !== undefined ? preset.silence_threshold_db : -50
        silenceDurationField.text = preset.silence_duration || "0.3"
        splitChaptersCheck.checked = !!preset.split_chapters
        coverArtField.text = preset.cover_art_path || ""
        beforeHookField.text = preset.before_hook || ""
        afterHookField.text = preset.after_hook || ""
        stripMetadataCheck.checked = !!preset.strip_metadata
        copyMetadataCheck.checked = !!preset.copy_metadata
        metaTitleField.text = preset.meta_title || ""
        metaCommentField.text = preset.meta_comment || ""
        metaAuthorField.text = preset.meta_author || ""
        metaCopyrightField.text = preset.meta_copyright || ""
        metaAlbumField.text = preset.meta_album || ""
        metaGenreField.text = preset.meta_genre || ""
        metaYearField.text = preset.meta_year || ""
        metaTrackField.text = preset.meta_track || ""
    }

    function collectTaskOverride() {
        var data = {}
        if (overrideOperationCombo.currentText !== inheritLabel)
            data.operation = overrideOperationCombo.currentText
        if (overrideTemplateField.text.length > 0)
            data.output_template = overrideTemplateField.text
        if (overrideVideoFmt.currentText !== inheritLabel)
            data.out_video_fmt = overrideVideoFmt.currentText
        if (overrideImageFmt.currentText !== inheritLabel)
            data.out_image_fmt = overrideImageFmt.currentText
        if (overrideAudioFmt.currentText !== inheritLabel)
            data.out_audio_fmt = overrideAudioFmt.currentText
        if (overrideSubtitleFmt.currentText !== inheritLabel)
            data.out_subtitle_fmt = overrideSubtitleFmt.currentText
        if (overrideSkipCombo.currentText === "Так")
            data.skip_existing = true
        else if (overrideSkipCombo.currentText === "Ні")
            data.skip_existing = false
        return data
    }

    function applyTaskOverride(overrideData) {
        var data = overrideData || {}
        setComboText(overrideOperationCombo, data.operation || inheritLabel)
        overrideTemplateField.text = data.output_template || ""
        setComboText(overrideVideoFmt, data.out_video_fmt || inheritLabel)
        setComboText(overrideImageFmt, data.out_image_fmt || inheritLabel)
        setComboText(overrideAudioFmt, data.out_audio_fmt || inheritLabel)
        setComboText(overrideSubtitleFmt, data.out_subtitle_fmt || inheritLabel)
        if (data.skip_existing === true)
            setComboText(overrideSkipCombo, "Так")
        else if (data.skip_existing === false)
            setComboText(overrideSkipCombo, "Ні")
        else
            setComboText(overrideSkipCombo, inheritLabel)
    }

    Connections {
        target: backend ? backend : null

        function onLogAdded(level, msg) {
            logArea.text += "[" + new Date().toLocaleTimeString() + "] " + level + ": " + msg + "\n"
            logArea.cursorPosition = logArea.text.length
        }

        function onPresetLoaded(preset) {
            applyPreset(preset)
            if (backend)
                backend.refreshOutputPreview(collectSettings())
        }

        function onTaskOverrideLoaded(overrideData) {
            applyTaskOverride(overrideData)
        }

        function onWatermarkPicked(path) {
            wmPathField.text = path
        }

        function onFontPicked(path) {
            textFontField.text = path
        }

        function onSubtitlePicked(path) {
            subtitlePathField.text = path
        }

        function onCoverArtPicked(path) {
            coverArtField.text = path
        }

        function onAudioReplacePicked(path) {
            replaceAudioPathField.text = path
        }
    }

    Component.onCompleted: {
        if (backend) {
            backend.refreshEncoders()
            backend.restoreSession()
            backend.refreshOutputPreview(collectSettings())
        }
        applyTaskOverride({})
    }

    ScrollView {
        id: contentWrap
        anchors.fill: parent
        anchors.margins: Theme.space3
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        background: Rectangle { color: "transparent" }

        Item {
            width: contentWrap.availableWidth
            implicitHeight: pageColumn.implicitHeight

            ColumnLayout {
                id: pageColumn
                width: root.layoutWidth
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.space3

                Card {
                    ColumnLayout {
                        spacing: Theme.space3

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space3

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.space1

                                Label {
                                    text: "MEDIA CONVERTER STUDIO"
                                    color: Theme.accent2
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                    font.letterSpacing: 1.6
                                }

                                Label {
                                    text: backend ? backend.appTitle : "Media Converter"
                                    font.pixelSize: 28
                                    font.weight: Font.Black
                                    color: Theme.text
                                }

                                Label {
                                    text: "Черга, пресети під платформи, audio workflow, AI subtitle, preview і production-ready batch automation."
                                    color: Theme.muted
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 14
                                    Layout.fillWidth: true
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: compact ? 0 : 240
                                Layout.fillWidth: !compact
                                Layout.alignment: Qt.AlignTop
                                visible: !compact
                                radius: Theme.radiusSection
                                color: Theme.sectionAlt
                                border.width: 1
                                border.color: Theme.borderStrong
                                implicitHeight: 102

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.sectionPadding
                                    spacing: Theme.space1

                                    Label {
                                        text: "System status"
                                        color: Theme.muted
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                        font.letterSpacing: 1.2
                                    }

                                    Label {
                                        text: backend ? backend.statusText : "Готово"
                                        color: Theme.text
                                        font.pixelSize: 18
                                        font.weight: Font.Bold
                                    }

                                    Label {
                                        text: backend ? backend.encoderInfo : "Доступні: --"
                                        color: Theme.subtleText
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 11
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }

                        GridLayout {
                            columns: root.dashboardColumns
                            columnSpacing: Theme.space2
                            rowSpacing: Theme.space2
                            Layout.fillWidth: true

                            Rectangle {
                                Layout.fillWidth: true
                                radius: Theme.radiusSection
                                color: Theme.runningSoft
                                border.width: 1
                                border.color: root.statusBorderColor("running")
                                implicitHeight: 88

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.sectionPadding
                                    spacing: Theme.space0

                                    Label { text: "В черзі"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Label { text: backend ? backend.queueCount : 0; color: Theme.running; font.pixelSize: 24; font.weight: Font.Black }
                                    Label { text: backend && backend.runningCount > 0 ? "Є активна обробка" : "Очікує запуск"; color: Theme.subtleText; font.pixelSize: 11 }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                radius: Theme.radiusSection
                                color: Theme.successSoft
                                border.width: 1
                                border.color: root.statusBorderColor("success")
                                implicitHeight: 88

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.sectionPadding
                                    spacing: Theme.space0

                                    Label { text: "Готово"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Label { text: backend ? backend.completedCount : 0; color: Theme.success; font.pixelSize: 24; font.weight: Font.Black }
                                    Label { text: "Success + skipped"; color: Theme.subtleText; font.pixelSize: 11 }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                radius: Theme.radiusSection
                                color: Theme.dangerSoft
                                border.width: 1
                                border.color: root.statusBorderColor("failed")
                                implicitHeight: 88

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.sectionPadding
                                    spacing: Theme.space0

                                    Label { text: "Помилки"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Label { text: backend ? backend.failedCount : 0; color: Theme.danger; font.pixelSize: 24; font.weight: Font.Black }
                                    Label { text: "Потребують retry"; color: Theme.subtleText; font.pixelSize: 11 }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                radius: Theme.radiusSection
                                color: backend && backend.watchRunning ? Theme.warningSoft : Theme.sectionAlt
                                border.width: 1
                                border.color: backend && backend.watchRunning ? root.statusBorderColor("skipped") : Theme.border
                                implicitHeight: 88

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.sectionPadding
                                    spacing: Theme.space0

                                    Label { text: "Watch"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Label { text: backend && backend.watchRunning ? "ON" : "OFF"; color: backend && backend.watchRunning ? Theme.warning : Theme.text; font.pixelSize: 24; font.weight: Font.Black }
                                    Label { text: backend && backend.watchRunning ? "Папка моніториться" : "Неактивно"; color: Theme.subtleText; font.pixelSize: 11 }
                                }
                            }
                        }

                        GridLayout {
                            columns: root.headerColumns
                            columnSpacing: Theme.space2
                            rowSpacing: Theme.space1
                            Layout.fillWidth: true

                            Label { text: "FFmpeg:"; color: Theme.text }

                            AppTextField {
                                id: ffmpegField
                                text: backend ? backend.ffmpegPath : ""
                                Layout.fillWidth: true
                                onEditingFinished: if (backend) backend.ffmpegPath = text
                            }

                            SecondaryButton {
                                text: "Вказати"
                                onClicked: if (backend) backend.pickFfmpeg()
                            }

                            GhostButton {
                                text: "Перевірити"
                                onClicked: if (backend) backend.refreshEncoders()
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.space1

                            Repeater {
                                model: root.operationTabs
                                delegate: Rectangle {
                                    id: tabPill
                                    radius: Theme.radiusPill
                                    color: index === root.currentTab ? Theme.accent : tabMouse.containsMouse ? Theme.sectionAlt : Theme.section
                                    border.color: index === root.currentTab ? Theme.accent2 : tabMouse.containsMouse ? Theme.borderStrong : Theme.border
                                    border.width: 1
                                    height: 36
                                    implicitWidth: tabLabel.implicitWidth + Theme.space2 * 2 + 6
                                    scale: tabMouse.pressed ? 0.98 : tabMouse.containsMouse ? 1.02 : 1

                                    Behavior on color { ColorAnimation { duration: 120 } }
                                    Behavior on scale { NumberAnimation { duration: 120 } }

                                    Label {
                                        id: tabLabel
                                        anchors.centerIn: parent
                                        text: modelData
                                        color: index === root.currentTab ? "#FFFFFF" : Theme.muted
                                        font.pixelSize: 12
                                        font.weight: Font.Medium
                                    }

                                    MouseArea {
                                        id: tabMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.currentTab = index
                                    }
                                }
                            }
                        }
                    }
                }

                GridLayout {
                    columns: root.workspaceColumns
                    columnSpacing: Theme.space2
                    rowSpacing: Theme.space2
                    Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: Theme.space2

                    Card {
                        title: "Черга"

                        ColumnLayout {
                            spacing: Theme.space2

                            Rectangle {
                                visible: root.queueEmpty
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.compact ? 260 : 300
                                radius: Theme.radiusSection
                                color: dropZone.containsDrag ? Theme.sectionAlt : Theme.section
                                border.width: 1
                                border.color: dropZone.containsDrag ? Theme.focusRing : Theme.border

                                ColumnLayout {
                                    anchors.centerIn: parent
                                    width: Math.min(parent.width - Theme.space4 * 2, 420)
                                    spacing: Theme.space2

                                    Rectangle {
                                        Layout.alignment: Qt.AlignHCenter
                                        width: 74
                                        height: 74
                                        radius: 22
                                        color: Theme.panelAlt
                                        border.width: 1
                                        border.color: dropZone.containsDrag ? Theme.focusRing : Theme.borderStrong

                                        Label {
                                            anchors.centerIn: parent
                                            text: "DROP"
                                            color: Theme.accent2
                                            font.pixelSize: 16
                                            font.weight: Font.Black
                                        }
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: "Перетягни файли або папку прямо сюди"
                                        color: Theme.text
                                        horizontalAlignment: Text.AlignHCenter
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 18
                                        font.weight: Font.Bold
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: "Hero-зона для першого запуску: drop media, далі застосуй preset і перевір output preview."
                                        color: Theme.muted
                                        horizontalAlignment: Text.AlignHCenter
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 12
                                    }

                                    GridLayout {
                                        columns: root.dualActionColumns
                                        Layout.fillWidth: true
                                        columnSpacing: Theme.space1
                                        rowSpacing: Theme.space1

                                        SecondaryButton { text: "Додати файли"; onClicked: if (backend) backend.addFiles() }
                                        GhostButton { text: "Додати папку"; onClicked: if (backend) backend.addFolder() }
                                    }
                                }

                                DropArea {
                                    id: dropZone
                                    anchors.fill: parent
                                    onDropped: {
                                        if (backend)
                                            backend.addDroppedUrls(drop.urls)
                                        clearSelection()
                                    }
                                }
                            }

                            ScrollView {
                                visible: !root.queueEmpty
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.compact ? 280 : 360
                                background: Rectangle { color: "transparent" }

                                ListView {
                                    id: queueList
                                    model: backend ? backend.queueModel : null
                                    clip: true
                                    spacing: Theme.space1

                                    delegate: Rectangle {
                                        id: queueCard
                                        property bool hovered: queueHover.hovered
                                        width: ListView.view.width
                                        height: 94
                                        radius: Theme.radiusSection
                                        color: ListView.isCurrentItem ? Theme.panelHover : hovered ? Theme.sectionAlt : Theme.section
                                        border.width: 1
                                        border.color: ListView.isCurrentItem ? Theme.focusRing : hovered ? Theme.borderStrong : Theme.border

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: Theme.space2

                                            AppCheckBox {
                                                checked: selectedQueue.indexOf(index) !== -1
                                                onToggled: toggleQueueIndex(index, checked)
                                            }

                                            Rectangle {
                                                width: 46
                                                height: 46
                                                radius: 14
                                                color: Qt.rgba(mediaColor(model.mediaType).r, mediaColor(model.mediaType).g, mediaColor(model.mediaType).b, 0.14)
                                                border.width: 1
                                                border.color: Qt.rgba(mediaColor(model.mediaType).r, mediaColor(model.mediaType).g, mediaColor(model.mediaType).b, 0.40)
                                                Layout.alignment: Qt.AlignTop

                                                Label {
                                                    anchors.centerIn: parent
                                                    text: mediaGlyph(model.mediaType)
                                                    color: mediaColor(model.mediaType)
                                                    font.pixelSize: 12
                                                    font.weight: Font.Black
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: Theme.space0

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: Theme.space1

                                                    Label {
                                                        text: model.name
                                                        color: Theme.text
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                        font.pixelSize: 13
                                                        font.weight: Font.Bold
                                                    }

                                                    Rectangle {
                                                        visible: model.hasOverride
                                                        radius: Theme.radiusPill
                                                        color: Theme.accentSoft
                                                        border.width: 1
                                                        border.color: Theme.accent2
                                                        implicitWidth: overrideLabel.implicitWidth + 14
                                                        implicitHeight: 24

                                                        Label {
                                                            id: overrideLabel
                                                            anchors.centerIn: parent
                                                            text: "OVERRIDE"
                                                            color: Theme.accent2
                                                            font.pixelSize: 10
                                                            font.weight: Font.Black
                                                            font.letterSpacing: 0.8
                                                        }
                                                    }
                                                }

                                                Label {
                                                    Layout.fillWidth: true
                                                    text: "Source: " + model.name
                                                    color: Theme.subtleText
                                                    elide: Text.ElideRight
                                                    font.pixelSize: 11
                                                }

                                                Label {
                                                    Layout.fillWidth: true
                                                    text: "Output: " + (model.previewOutput && model.previewOutput.length > 0 ? model.previewOutput : "—")
                                                    color: Theme.muted
                                                    elide: Text.ElideRight
                                                    font.pixelSize: 12
                                                }

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: Theme.space1

                                                    Rectangle {
                                                        radius: Theme.radiusPill
                                                        color: root.statusSurfaceColor(model.status)
                                                        border.width: 1
                                                        border.color: root.statusBorderColor(model.status)
                                                        implicitWidth: statusLabel.implicitWidth + 14
                                                        implicitHeight: 24

                                                        Label {
                                                            id: statusLabel
                                                            anchors.centerIn: parent
                                                            text: model.status
                                                            color: root.statusColor(model.status)
                                                            font.pixelSize: 11
                                                            font.weight: Font.Black
                                                        }
                                                    }

                                                    Label {
                                                        visible: model.attempts > 0
                                                        text: "Спроба " + model.attempts
                                                        color: Theme.subtleText
                                                        font.pixelSize: 11
                                                    }

                                                    Label {
                                                        visible: model.errorText.length > 0
                                                        text: model.errorText
                                                        color: Theme.danger
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                        font.pixelSize: 11
                                                    }
                                                }
                                            }
                                        }

                                        HoverHandler { id: queueHover }

                                        TapHandler {
                                            onTapped: {
                                                queueList.currentIndex = index
                                                if (backend)
                                                    backend.selectQueueIndex(index)
                                            }
                                        }
                                    }
                                }
                            }

                            GridLayout {
                                columns: root.queueActionColumns
                                columnSpacing: Theme.space1
                                rowSpacing: Theme.space1
                                Layout.fillWidth: true

                                SecondaryButton { text: "Додати файли"; onClicked: if (backend) backend.addFiles() }
                                SecondaryButton { text: "Додати папку"; onClicked: if (backend) backend.addFolder() }
                                GhostButton { text: "Прибрати дублікати"; onClicked: if (backend) backend.deduplicateQueue() }
                                GhostButton { text: "Hash дублікати"; onClicked: if (backend) backend.deduplicateQueueByHash() }
                                GhostButton { text: "Повторити помилки"; onClicked: if (backend) backend.retryFailed() }
                                GhostButton {
                                    text: "Вгору"
                                    onClicked: {
                                        if (backend) backend.moveSelectedUp(selectedQueue)
                                    }
                                }
                                GhostButton {
                                    text: "Вниз"
                                    onClicked: {
                                        if (backend) backend.moveSelectedDown(selectedQueue)
                                    }
                                }
                                GhostButton {
                                    text: "На верх"
                                    onClicked: {
                                        if (backend) backend.moveSelectedTop(selectedQueue)
                                    }
                                }
                                GhostButton {
                                    text: "На низ"
                                    onClicked: {
                                        if (backend) backend.moveSelectedBottom(selectedQueue)
                                    }
                                }
                                GhostButton {
                                    text: "Видалити"
                                    onClicked: {
                                        if (backend) backend.removeSelected(selectedQueue)
                                        clearSelection()
                                    }
                                }
                                GhostButton {
                                    text: "Очистити"
                                    onClicked: {
                                        if (backend) backend.clearQueue()
                                        clearSelection()
                                    }
                                }
                            }
                        }
                    }

                    Card {
                        title: "Інформація"

                        ColumnLayout {
                            spacing: Theme.space1
                            RowLayout { Label { text: "Файл:"; color: Theme.muted } Label { text: backend ? backend.infoName : "—"; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Тривалість:"; color: Theme.muted } Label { text: backend ? backend.infoDuration : "--:--"; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Кодеки:"; color: Theme.muted } Label { text: backend ? backend.infoCodec : "—"; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Роздільність:"; color: Theme.muted } Label { text: backend ? backend.infoRes : "—"; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Розмір:"; color: Theme.muted } Label { text: backend ? backend.infoSize : "—"; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Контейнер:"; color: Theme.muted } Label { text: backend ? backend.infoContainer : "—"; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Аналіз:"; color: Theme.muted } Label { text: backend ? backend.infoAnalysis : "—"; color: Theme.text; wrapMode: Text.WordWrap; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Попередження:"; color: Theme.muted } Label { text: backend ? backend.infoWarnings : "—"; color: Theme.warning; wrapMode: Text.WordWrap; Layout.fillWidth: true } }
                        }
                    }

                    Card {
                        title: "Дії"

                        ColumnLayout {
                            spacing: Theme.space2

                            Label {
                                text: "Запуск batch, проєкт і preview тепер знаходяться у вкладці `Проєкт`, щоб ліва колонка залишалась простою."
                                color: Theme.muted
                                wrapMode: Text.WordWrap
                                font.pixelSize: 11
                            }

                            PrimaryButton { text: "Старт"; enabled: backend ? !backend.isRunning : false; onClicked: if (backend) backend.startConversion(collectSettings()) }
                            SecondaryButton { text: "Стоп"; enabled: backend ? backend.isRunning : false; onClicked: if (backend) backend.stopConversion() }
                            GhostButton { text: "Відкрити вкладку Проєкт"; onClicked: root.currentTab = 5 }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: Theme.space2

                    Card {
                        title: "Налаштування"

                        ColumnLayout {
                            spacing: Theme.space2

                            StackLayout {
                                currentIndex: root.currentTab
                                Layout.fillWidth: true

                                Item {
                                    implicitWidth: startColumn.implicitWidth
                                    implicitHeight: startColumn.implicitHeight

                                    ColumnLayout {
                                        id: startColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Що ти хочеш зробити?"

                                            ColumnLayout {
                                                spacing: Theme.space2

                                                Label {
                                                    text: "Почни зі сценарію. Після вибору інтерфейс стає зрозумілішим: відео шукай у вкладці `Відео`, фото у `Фото`, звук у `Аудіо`, субтитри у `Субтитри`."
                                                    color: Theme.muted
                                                    wrapMode: Text.WordWrap
                                                    font.pixelSize: 12
                                                }

                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.presetColumns
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space2

                                                    Repeater {
                                                        model: root.operationQuickCards
                                                        delegate: Rectangle {
                                                            Layout.fillWidth: true
                                                            implicitHeight: 108
                                                            radius: Theme.radiusSection
                                                            color: operationMouse.pressed ? Theme.panelHover : operationMouse.containsMouse ? Theme.sectionAlt : Theme.section
                                                            border.width: 1
                                                            border.color: operationCombo.currentText === modelData.name ? Theme.focusRing : operationMouse.containsMouse ? Theme.borderStrong : Theme.border

                                                            ColumnLayout {
                                                                anchors.fill: parent
                                                                anchors.margins: Theme.sectionPadding
                                                                spacing: Theme.space1

                                                                Label { text: modelData.title; color: Theme.text; font.pixelSize: 16; font.weight: Font.Bold }
                                                                Label { text: modelData.meta; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
                                                                Label { text: modelData.name; color: Theme.subtleText; font.pixelSize: 11 }
                                                            }

                                                            MouseArea {
                                                                id: operationMouse
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                onClicked: {
                                                                    setComboText(operationCombo, modelData.name)
                                                                    if (modelData.name === "Конвертація")
                                                                        root.currentTab = 1
                                                                    else if (modelData.name === "Лише аудіо")
                                                                        root.currentTab = 3
                                                                    else if (modelData.name === "Thumbnail" || modelData.name === "Contact sheet")
                                                                        root.currentTab = 2
                                                                    else
                                                                        root.currentTab = 4
                                                                    if (backend)
                                                                        backend.refreshOutputPreview(collectSettings())
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "База проєкту"

                                            ColumnLayout {
                                                spacing: Theme.space2

                                                Label {
                                                    text: "Тут тільки те, що потрібне для старту. Детальні параметри рознесені по вкладках нижче: `Відео`, `Фото`, `Аудіо`, `Субтитри`, `Проєкт`, `Система`."
                                                    color: Theme.muted
                                                    wrapMode: Text.WordWrap
                                                    font.pixelSize: 12
                                                }

                                                GridLayout {
                                                    columns: root.formColumns
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1

                                                    Label { text: "Операція:"; color: Theme.muted }
                                                    AppComboBox { id: operationCombo; model: root.operationOptions }
                                                    Label { text: "Шаблон імені:"; color: Theme.muted }
                                                    AppTextField { id: outputTemplateField; text: "{stem}" }
                                                    Label { text: "Профіль платформи:"; color: Theme.muted }
                                                    AppTextField { id: platformProfileField; placeholderText: "YouTube / TikTok / ..." }
                                                }

                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.presetColumns
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space2

                                                    Repeater {
                                                        model: [
                                                            { title: "Відео", meta: "Кодек, resize, crop, watermark", tab: 1, color: Theme.runningSoft, border: root.statusBorderColor("running") },
                                                            { title: "Фото", meta: "Thumbnail, contact sheet, image export", tab: 2, color: Theme.sectionAlt, border: Theme.borderStrong },
                                                            { title: "Аудіо", meta: "Track, normalize, peak, silence, cover", tab: 3, color: Theme.successSoft, border: root.statusBorderColor("success") },
                                                            { title: "Субтитри", meta: "Burn-in, extract, AI subtitle", tab: 4, color: Theme.warningSoft, border: root.statusBorderColor("skipped") },
                                                            { title: "Проєкт", meta: "Output folder, preview, history, presets", tab: 5, color: Theme.accentSoft, border: Theme.accent2 },
                                                            { title: "Система", meta: "Metadata, hooks, службові налаштування", tab: 6, color: Theme.sectionAlt, border: Theme.border }
                                                        ]

                                                        delegate: Rectangle {
                                                            Layout.fillWidth: true
                                                            implicitHeight: 82
                                                            radius: Theme.radiusSection
                                                            color: navMouse.pressed ? Theme.panelHover : navMouse.containsMouse ? modelData.color : Theme.section
                                                            border.width: 1
                                                            border.color: navMouse.containsMouse ? modelData.border : Theme.border

                                                            ColumnLayout {
                                                                anchors.fill: parent
                                                                anchors.margins: Theme.sectionPadding
                                                                spacing: Theme.space0

                                                                Label {
                                                                    text: modelData.title
                                                                    color: Theme.text
                                                                    font.pixelSize: 14
                                                                    font.weight: Font.Bold
                                                                }

                                                                Label {
                                                                    text: modelData.meta
                                                                    color: Theme.muted
                                                                    wrapMode: Text.WordWrap
                                                                    Layout.fillWidth: true
                                                                    font.pixelSize: 11
                                                                }
                                                            }

                                                            MouseArea {
                                                                id: navMouse
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                onClicked: root.currentTab = modelData.tab
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Готові пресети під платформи"

                                            ColumnLayout {
                                                spacing: Theme.space2

                                                Label {
                                                    text: "Якщо задача типова, почни з platform preset, а далі точково підправ параметри у вкладках `Відео` або `Фото`."
                                                    color: Theme.muted
                                                    wrapMode: Text.WordWrap
                                                    font.pixelSize: 11
                                                }

                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.presetColumns
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space2

                                                    Repeater {
                                                        model: root.platformPresetCards
                                                        delegate: Rectangle {
                                                            Layout.fillWidth: true
                                                            implicitHeight: 112
                                                            radius: Theme.radiusSection
                                                            color: presetMouse.pressed ? Theme.panelHover : presetMouse.containsMouse ? Theme.sectionAlt : Theme.section
                                                            border.width: 1
                                                            border.color: presetMouse.containsMouse ? Theme.focusRing : Theme.border

                                                            ColumnLayout {
                                                                anchors.fill: parent
                                                                anchors.margins: Theme.sectionPadding
                                                                spacing: Theme.space1

                                                                RowLayout {
                                                                    Layout.fillWidth: true
                                                                    Label { text: modelData.title; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold; Layout.fillWidth: true }
                                                                    Rectangle {
                                                                        radius: Theme.radiusPill
                                                                        color: Theme.accentSoft
                                                                        border.width: 1
                                                                        border.color: Theme.accent2
                                                                        implicitWidth: presetBadge.implicitWidth + 14
                                                                        implicitHeight: 24
                                                                        Label { id: presetBadge; anchors.centerIn: parent; text: modelData.badge; color: Theme.accent2; font.pixelSize: 10; font.weight: Font.Black }
                                                                    }
                                                                }

                                                                Label { text: modelData.meta; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
                                                                Label { text: modelData.name; color: Theme.subtleText; elide: Text.ElideRight; Layout.fillWidth: true; font.pixelSize: 11 }
                                                            }

                                                            MouseArea {
                                                                id: presetMouse
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                onClicked: {
                                                                    if (backend)
                                                                        backend.loadPreset(modelData.name)
                                                                    root.currentTab = 1
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Поведінка черги"

                                            ColumnLayout {
                                                spacing: Theme.space1
                                                AppCheckBox { id: overwriteCheck; text: "Перезаписувати існуючі файли" }
                                                AppCheckBox { id: skipExistingCheck; text: "Пропускати вже існуючі" }
                                                AppCheckBox { id: fastCopyCheck; text: "Fast copy, коли це можливо" }
                                            }
                                        }
                                    }
                                }

                                Item {
                                    implicitWidth: videoColumn.implicitWidth
                                    implicitHeight: videoColumn.implicitHeight

                                    ColumnLayout {
                                        id: videoColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Кодування відео"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Вихідний формат:"; color: Theme.muted }
                                                AppComboBox { id: outVideoFmt; model: root.videoFormats }
                                                Label { text: "CRF:"; color: Theme.muted }
                                                AppSpinBox { id: crfSpin; from: 14; to: 35; value: 23 }
                                                Label { text: "Preset:"; color: Theme.muted }
                                                AppComboBox { id: presetCombo; model: ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"] }
                                                Label { text: "Портрет:"; color: Theme.muted }
                                                AppComboBox { id: portraitCombo; model: root.portraitOptions }
                                                Label { text: "Кодек відео:"; color: Theme.muted }
                                                AppComboBox { id: codecCombo; model: root.codecOptions }
                                                Label { text: "GPU/CPU:"; color: Theme.muted }
                                                AppComboBox { id: hwCombo; model: root.hwOptions }
                                                Label { text: backend ? backend.encoderInfo : "Доступні: --"; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.columnSpan: root.formColumns }
                                            }
                                        }

                                        Section {
                                            title: "Час і монтаж"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Початок:"; color: Theme.muted }
                                                AppTextField { id: trimStartField; placeholderText: "hh:mm:ss або сек" }
                                                Label { text: "Кінець:"; color: Theme.muted }
                                                AppTextField { id: trimEndField; placeholderText: "hh:mm:ss або сек" }
                                                Label { text: "Швидкість:"; color: Theme.muted }
                                                AppTextField { id: speedField; text: "1.0" }
                                                AppCheckBox { id: mergeCheck; text: "Merge всі відео"; Layout.columnSpan: root.formColumns }
                                                Label { text: "Назва merge:"; color: Theme.muted }
                                                AppTextField { id: mergeNameField; text: "merged" }
                                            }
                                        }

                                        Section {
                                            title: "Кадр і композиція"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Resize W:"; color: Theme.muted }
                                                AppTextField { id: resizeWField }
                                                Label { text: "Resize H:"; color: Theme.muted }
                                                AppTextField { id: resizeHField }
                                                Label { text: "Crop W:"; color: Theme.muted }
                                                AppTextField { id: cropWField }
                                                Label { text: "Crop H:"; color: Theme.muted }
                                                AppTextField { id: cropHField }
                                                Label { text: "Crop X:"; color: Theme.muted }
                                                AppTextField { id: cropXField }
                                                Label { text: "Crop Y:"; color: Theme.muted }
                                                AppTextField { id: cropYField }
                                                Label { text: "Поворот:"; color: Theme.muted }
                                                AppComboBox { id: rotateCombo; model: root.rotateOptions }
                                            }
                                        }

                                        Section {
                                            title: "Водяний знак і текст"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "WM файл:"; color: Theme.muted }
                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    AppTextField { id: wmPathField; Layout.fillWidth: true }
                                                    SecondaryButton { text: "Вибрати"; onClicked: if (backend) backend.pickWatermark() }
                                                }
                                                Label { text: "WM позиція:"; color: Theme.muted }
                                                AppComboBox { id: wmPosCombo; model: root.positionOptions }
                                                Label { text: "WM scale %:"; color: Theme.muted }
                                                AppSpinBox { id: wmScaleSpin; from: 1; to: 200; value: 30 }
                                                Label { text: "WM opacity %:"; color: Theme.muted }
                                                AppSpinBox { id: wmOpacitySpin; from: 0; to: 100; value: 80 }
                                                Label { text: "Текст:"; color: Theme.muted }
                                                AppTextField { id: textWatermarkField }
                                                Label { text: "Text позиція:"; color: Theme.muted }
                                                AppComboBox { id: textPosCombo; model: root.positionOptions }
                                                Label { text: "Text size:"; color: Theme.muted }
                                                AppSpinBox { id: textSizeSpin; from: 8; to: 120; value: 24 }
                                                Label { text: "Text color:"; color: Theme.muted }
                                                AppTextField { id: textColorField; text: "white" }
                                                Label { text: "Font:"; color: Theme.muted }
                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    AppTextField { id: textFontField; Layout.fillWidth: true }
                                                    SecondaryButton { text: "Вибрати"; onClicked: if (backend) backend.pickFont() }
                                                }
                                                AppCheckBox { id: textBoxCheck; text: "Фон тексту"; Layout.columnSpan: root.formColumns }
                                                Label { text: "Box color:"; color: Theme.muted }
                                                AppTextField { id: textBoxColorField; text: "black" }
                                                Label { text: "Box opacity %:"; color: Theme.muted }
                                                AppSpinBox { id: textBoxOpacitySpin; from: 0; to: 100; value: 50 }
                                            }
                                        }
                                    }
                                }

                                Item {
                                    implicitWidth: photoColumn.implicitWidth
                                    implicitHeight: photoColumn.implicitHeight

                                    ColumnLayout {
                                        id: photoColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Фото і кадри"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Формат фото:"; color: Theme.muted }
                                                AppComboBox { id: outImageFmt; model: root.imageFormats }
                                                Label { text: "Якість фото:"; color: Theme.muted }
                                                AppSpinBox { id: imgQualitySpin; from: 1; to: 100; value: 90 }
                                                Label { text: "Thumbnail time:"; color: Theme.muted }
                                                AppTextField { id: thumbnailTimeField; placeholderText: "hh:mm:ss або сек" }
                                                Label { text: "Sheet cols:"; color: Theme.muted }
                                                AppSpinBox { id: sheetColsSpin; from: 1; to: 10; value: 4 }
                                                Label { text: "Sheet rows:"; color: Theme.muted }
                                                AppSpinBox { id: sheetRowsSpin; from: 1; to: 10; value: 4 }
                                                Label { text: "Cell width:"; color: Theme.muted }
                                                AppSpinBox { id: sheetWidthSpin; from: 80; to: 1200; value: 320 }
                                                Label { text: "Interval sec:"; color: Theme.muted }
                                                AppSpinBox { id: sheetIntervalSpin; from: 1; to: 600; value: 10 }
                                            }
                                        }

                                        Section {
                                            title: "Швидкі resize-пресети"

                                            Flow {
                                                Layout.fillWidth: true
                                                spacing: Theme.space1

                                                Repeater {
                                                    model: [
                                                        ["720p", 1280, 720],
                                                        ["1080p", 1920, 1080],
                                                        ["1440p", 2560, 1440],
                                                        ["4K", 3840, 2160]
                                                    ]
                                                    delegate: SecondaryButton {
                                                        text: "До " + modelData[0]
                                                        onClicked: {
                                                            resizeWField.text = modelData[1]
                                                            resizeHField.text = modelData[2]
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Підказка"

                                            Label {
                                                text: "Для `Thumbnail` і `Contact sheet` спочатку обери відповідну операцію у вкладці `Старт`, а потім налаштуй параметри тут."
                                                color: Theme.muted
                                                wrapMode: Text.WordWrap
                                                font.pixelSize: 12
                                            }
                                        }
                                    }
                                }

                                Item {
                                    implicitWidth: audioColumn.implicitWidth
                                    implicitHeight: audioColumn.implicitHeight

                                    ColumnLayout {
                                        id: audioColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Аудіо вихід"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Формат аудіо:"; color: Theme.muted }
                                                AppComboBox { id: outAudioFmt; model: root.audioFormats }
                                                Label { text: "Audio bitrate:"; color: Theme.muted }
                                                AppTextField { id: audioBitrateField; text: "192k" }
                                                Label { text: "Track для збереження:"; color: Theme.muted }
                                                AppSpinBox { id: audioTrackSpin; from: 1; to: 8; value: 1 }
                                                Label { text: "Замінити аудіо:"; color: Theme.muted }
                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    AppTextField { id: replaceAudioPathField; Layout.fillWidth: true }
                                                    SecondaryButton { text: "Вибрати"; onClicked: if (backend) backend.pickAudioReplace() }
                                                }
                                                Label { text: "Cover art:"; color: Theme.muted }
                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    AppTextField { id: coverArtField; Layout.fillWidth: true }
                                                    SecondaryButton { text: "Вибрати"; onClicked: if (backend) backend.pickCoverArt() }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Обробка аудіо"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Нормалізація:"; color: Theme.muted }
                                                AppComboBox { id: normalizeAudioCombo; model: root.normalizeOptions }
                                                Label { text: "Peak limit dB:"; color: Theme.muted }
                                                AppTextField { id: peakLimitField; placeholderText: "-1.0" }
                                                AppCheckBox { id: trimSilenceCheck; text: "Обрізати тишу"; Layout.columnSpan: root.formColumns }
                                                Label { text: "Поріг тиші dB:"; color: Theme.muted }
                                                AppSpinBox { id: silenceThresholdSpin; from: -90; to: -10; value: -50 }
                                                Label { text: "Тривалість тиші:"; color: Theme.muted }
                                                AppTextField { id: silenceDurationField; text: "0.3"; placeholderText: "0.3" }
                                                AppCheckBox { id: splitChaptersCheck; text: "Split by chapters"; Layout.columnSpan: root.formColumns }
                                            }
                                        }
                                    }
                                }

                                Item {
                                    implicitWidth: subtitleColumn.implicitWidth
                                    implicitHeight: subtitleColumn.implicitHeight

                                    ColumnLayout {
                                        id: subtitleColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Субтитри"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Вихідний формат:"; color: Theme.muted }
                                                AppComboBox { id: outSubtitleFmt; model: root.subtitleFormats }
                                                Label { text: "Режим:"; color: Theme.muted }
                                                AppComboBox { id: subtitleModeCombo; model: root.subtitleModeOptions }
                                                Label { text: "Файл:"; color: Theme.muted }
                                                GridLayout {
                                                    Layout.fillWidth: true
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    AppTextField { id: subtitlePathField; Layout.fillWidth: true }
                                                    SecondaryButton { text: "Вибрати"; onClicked: if (backend) backend.pickSubtitle() }
                                                }
                                                Label { text: "Subtitle stream:"; color: Theme.muted }
                                                AppSpinBox { id: subtitleStreamSpin; from: 0; to: 10; value: 0 }
                                            }
                                        }

                                        Section {
                                            title: "AI subtitle"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Мова:"; color: Theme.muted }
                                                AppTextField { id: subtitleLanguageField; text: "auto"; placeholderText: "auto / uk / en" }
                                                Label { text: "Whisper model:"; color: Theme.muted }
                                                AppComboBox { id: subtitleModelCombo; model: ["tiny", "base", "small", "medium"] }
                                                Label { text: "Engine:"; color: Theme.muted }
                                                AppComboBox { id: subtitleEngineCombo; model: root.subtitleEngineOptions }
                                            }
                                        }

                                        Section {
                                            title: "Підказка"

                                            Label {
                                                text: "Для `Авто субтитри` обери цю операцію у вкладці `Старт`. Для `Burn-in subtitle` спочатку задай subtitle-файл або обери subtitle stream."
                                                color: Theme.muted
                                                wrapMode: Text.WordWrap
                                                font.pixelSize: 12
                                            }
                                        }
                                    }
                                }

                                Item {
                                    implicitWidth: projectColumn.implicitWidth
                                    implicitHeight: projectColumn.implicitHeight

                                    ColumnLayout {
                                        id: projectColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Вивід"

                                            ColumnLayout {
                                                spacing: Theme.space1

                                                AppTextField {
                                                    id: outputDirField
                                                    text: backend ? backend.outputDir : ""
                                                    onEditingFinished: if (backend) backend.outputDir = text
                                                }

                                                GridLayout {
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    Layout.fillWidth: true

                                                    SecondaryButton { text: "Вибрати"; onClicked: if (backend) backend.pickOutputDir() }
                                                    GhostButton { text: "Відкрити"; onClicked: if (backend) backend.openOutputDir() }
                                                }

                                                Label {
                                                    text: "Шаблон імені: {stem}, {ext}, {dir}, {index}, {date}, {time}, {op}"
                                                    color: Theme.muted
                                                    wrapMode: Text.WordWrap
                                                    font.pixelSize: 11
                                                }

                                                AppComboBox {
                                                    id: recentFoldersCombo
                                                    model: backend ? backend.recentFoldersModel : []
                                                    Layout.fillWidth: true
                                                }

                                                GridLayout {
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    Layout.fillWidth: true

                                                    GhostButton { text: "У вивід"; onClicked: if (backend) backend.useRecentFolder(recentFoldersCombo.currentIndex, "output") }
                                                    GhostButton { text: "У watch"; onClicked: if (backend) backend.useRecentFolder(recentFoldersCombo.currentIndex, "watch") }
                                                    GhostButton { text: "Оновити preview"; onClicked: if (backend) backend.refreshOutputPreview(collectSettings()) }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Preview назв"

                                            ColumnLayout {
                                                spacing: Theme.space2

                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    radius: Theme.radiusSection
                                                    color: Theme.sectionAlt
                                                    border.width: 1
                                                    border.color: Theme.border
                                                    implicitHeight: 122

                                                    GridLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: Theme.sectionPadding
                                                        columns: compact ? 1 : 3
                                                        columnSpacing: Theme.space2
                                                        rowSpacing: Theme.space1

                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            spacing: Theme.space0
                                                            Label { text: "Source"; color: Theme.subtleText; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                            Label { text: backend ? backend.selectedPreviewSource : "—"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold; elide: Text.ElideRight; Layout.fillWidth: true }
                                                        }

                                                        Rectangle {
                                                            Layout.alignment: Qt.AlignCenter
                                                            width: compact ? 44 : 60
                                                            height: 34
                                                            radius: 17
                                                            color: Theme.runningSoft
                                                            border.width: 1
                                                            border.color: root.statusBorderColor("running")
                                                            Label { anchors.centerIn: parent; text: "→"; color: Theme.running; font.pixelSize: 18; font.weight: Font.Black }
                                                        }

                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            spacing: Theme.space0
                                                            Label { text: "Output"; color: Theme.subtleText; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                            Label { text: backend ? backend.selectedPreviewOutput : "—"; color: Theme.accent2; font.pixelSize: 15; font.weight: Font.Bold; elide: Text.ElideRight; Layout.fillWidth: true }
                                                        }
                                                    }
                                                }

                                                AppTextArea {
                                                    text: backend ? backend.outputPreviewText : ""
                                                    readOnly: true
                                                    textFormat: Text.PlainText
                                                    wrapMode: TextEdit.NoWrap
                                                    font.pixelSize: 12
                                                    Layout.preferredHeight: 150
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Watch folder"

                                            ColumnLayout {
                                                spacing: Theme.space1

                                                AppTextField {
                                                    id: watchFolderField
                                                    text: backend ? backend.watchFolder : ""
                                                    onEditingFinished: if (backend) backend.watchFolder = text
                                                }

                                                GridLayout {
                                                    columns: root.tripleActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    Layout.fillWidth: true

                                                    SecondaryButton { text: "Обрати"; onClicked: if (backend) backend.pickWatchFolder() }
                                                    PrimaryButton { text: backend && backend.watchRunning ? "Watching..." : "Старт"; enabled: backend ? !backend.watchRunning : false; onClicked: if (backend) backend.startWatching() }
                                                    SecondaryButton { text: "Стоп"; enabled: backend ? backend.watchRunning : false; onClicked: if (backend) backend.stopWatching() }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Пресети"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Збережені:"; color: Theme.muted }
                                                AppComboBox { id: presetsCombo; model: backend ? backend.presetsModel : [] }
                                                GridLayout {
                                                    Layout.columnSpan: root.formColumns
                                                    columns: root.dualActionColumns
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    Layout.fillWidth: true
                                                    SecondaryButton { text: "Завантажити"; onClicked: if (backend) backend.loadPreset(presetsCombo.currentText) }
                                                    GhostButton { text: "Видалити"; onClicked: if (backend) backend.deletePreset(presetsCombo.currentText) }
                                                }
                                                Label { text: "Назва нового:"; color: Theme.muted }
                                                AppTextField { id: newPresetField }
                                                PrimaryButton { text: "Зберегти"; Layout.columnSpan: root.formColumns; onClicked: if (backend) backend.savePreset(newPresetField.text, collectSettings()) }
                                            }
                                        }

                                        Section {
                                            title: "Per-file override"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Операція:"; color: Theme.muted }
                                                AppComboBox { id: overrideOperationCombo; model: [inheritLabel].concat(root.operationOptions) }
                                                Label { text: "Template:"; color: Theme.muted }
                                                AppTextField { id: overrideTemplateField; placeholderText: "{stem}" }
                                                Label { text: "Відео:"; color: Theme.muted }
                                                AppComboBox { id: overrideVideoFmt; model: [inheritLabel].concat(root.videoFormats) }
                                                Label { text: "Фото:"; color: Theme.muted }
                                                AppComboBox { id: overrideImageFmt; model: [inheritLabel].concat(root.imageFormats) }
                                                Label { text: "Аудіо:"; color: Theme.muted }
                                                AppComboBox { id: overrideAudioFmt; model: [inheritLabel].concat(root.audioFormats) }
                                                Label { text: "Субтитри:"; color: Theme.muted }
                                                AppComboBox { id: overrideSubtitleFmt; model: [inheritLabel].concat(root.subtitleFormats) }
                                                Label { text: "Skip existing:"; color: Theme.muted }
                                                AppComboBox { id: overrideSkipCombo; model: root.boolOverrideOptions }
                                                GridLayout {
                                                    Layout.columnSpan: root.formColumns
                                                    columns: root.dualActionColumns
                                                    Layout.fillWidth: true
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    PrimaryButton { text: "Зберегти override"; onClicked: if (backend) backend.saveTaskOverride(queueList.currentIndex, collectTaskOverride()) }
                                                    GhostButton { text: "Очистити override"; onClicked: if (backend) backend.clearTaskOverride(queueList.currentIndex) }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Проєкт"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label {
                                                    text: "Тут зберігається весь session-state: черга, overrides і поточні налаштування."
                                                    color: Theme.muted
                                                    wrapMode: Text.WordWrap
                                                    Layout.columnSpan: root.formColumns
                                                    Layout.fillWidth: true
                                                }

                                                PrimaryButton { text: "Експорт .json"; Layout.columnSpan: root.formColumns; onClicked: if (backend) backend.exportProject(collectSettings()) }
                                                GhostButton { text: "Імпорт .json"; Layout.columnSpan: root.formColumns; onClicked: if (backend) backend.importProject() }
                                            }
                                        }

                                        Section {
                                            title: "Історія запусків"

                                            ColumnLayout {
                                                spacing: Theme.space1

                                                AppTextArea {
                                                    text: backend ? backend.historyText : ""
                                                    readOnly: true
                                                    textFormat: Text.PlainText
                                                    wrapMode: TextEdit.NoWrap
                                                    font.pixelSize: 12
                                                    Layout.preferredHeight: 140
                                                }

                                                GridLayout {
                                                    columns: root.dualActionColumns
                                                    Layout.fillWidth: true
                                                    columnSpacing: Theme.space1
                                                    rowSpacing: Theme.space1
                                                    GhostButton { text: "Оновити preview"; onClicked: if (backend) backend.refreshOutputPreview(collectSettings()) }
                                                    GhostButton { text: "Очистити історію"; onClicked: if (backend) backend.clearHistory() }
                                                }
                                            }
                                        }
                                    }
                                }

                                Item {
                                    implicitWidth: systemColumn.implicitWidth
                                    implicitHeight: systemColumn.implicitHeight

                                    ColumnLayout {
                                        id: systemColumn
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                        Section {
                                            title: "Метадані"

                                            ColumnLayout {
                                                spacing: Theme.space1
                                                AppCheckBox { id: copyMetadataCheck; text: "Копіювати метадані з джерела"; checked: true }
                                                AppCheckBox { id: stripMetadataCheck; text: "Очистити метадані" }
                                                GridLayout {
                                                    columns: root.formColumns
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Title:"; color: Theme.muted }
                                                    AppTextField { id: metaTitleField }
                                                    Label { text: "Author:"; color: Theme.muted }
                                                    AppTextField { id: metaAuthorField }
                                                    Label { text: "Album:"; color: Theme.muted }
                                                    AppTextField { id: metaAlbumField }
                                                    Label { text: "Genre:"; color: Theme.muted }
                                                    AppTextField { id: metaGenreField }
                                                    Label { text: "Year:"; color: Theme.muted }
                                                    AppTextField { id: metaYearField }
                                                    Label { text: "Track:"; color: Theme.muted }
                                                    AppTextField { id: metaTrackField }
                                                    Label { text: "Comment:"; color: Theme.muted }
                                                    AppTextField { id: metaCommentField }
                                                    Label { text: "Copyright:"; color: Theme.muted }
                                                    AppTextField { id: metaCopyrightField }
                                                }
                                            }
                                        }

                                        Section {
                                            title: "Hooks"

                                            GridLayout {
                                                columns: root.formColumns
                                                columnSpacing: Theme.space2
                                                rowSpacing: Theme.space1

                                                Label { text: "Before hook:"; color: Theme.muted }
                                                AppTextField { id: beforeHookField; placeholderText: "bash script.sh before" }
                                                Label { text: "After hook:"; color: Theme.muted }
                                                AppTextField { id: afterHookField; placeholderText: "bash script.sh after" }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Card {
                        title: "Лог"

                        ColumnLayout {
                            spacing: Theme.space2

                            Rectangle {
                                Layout.fillWidth: true
                                radius: Theme.radiusSection
                                color: Theme.section
                                border.width: 1
                                border.color: Theme.border
                                implicitHeight: logToolbar.implicitHeight + Theme.space2 * 2

                                RowLayout {
                                    id: logToolbar
                                    anchors.fill: parent
                                    anchors.margins: Theme.space2
                                    spacing: Theme.space2

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Label {
                                            text: "Журнал подій"
                                            color: Theme.text
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                        }

                                        Label {
                                            text: "FFmpeg, ffprobe і системні повідомлення з автопрокруткою до останнього запису."
                                            color: Theme.muted
                                            font.pixelSize: 11
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }

                                    GridLayout {
                                        columns: root.tripleActionColumns
                                        columnSpacing: Theme.space1
                                        rowSpacing: Theme.space1

                                        SecondaryButton {
                                            Layout.fillWidth: false
                                            text: "Експорт"
                                            onClicked: if (backend) backend.exportLog()
                                        }

                                        GhostButton {
                                            Layout.fillWidth: false
                                            text: "Очистити"
                                            onClicked: logArea.text = ""
                                        }

                                        GhostButton {
                                            Layout.fillWidth: false
                                            text: "В кінець"
                                            onClicked: logArea.cursorPosition = logArea.text.length
                                        }
                                    }
                                }
                            }

                            AppTextArea {
                                id: logArea
                                readOnly: true
                                textFormat: Text.PlainText
                                wrapMode: TextEdit.NoWrap
                                font.pixelSize: 12
                                Layout.preferredHeight: root.compact ? 220 : 260
                            }
                        }
                    }
                }
            }

                Card {
                    GridLayout {
                        columns: root.statusColumns
                        columnSpacing: Theme.space2
                        rowSpacing: Theme.space1
                        Layout.fillWidth: true

                        Label { text: backend ? backend.statusText : "Готово"; color: Theme.text }
                        ProgressBar { from: 0; to: 1; value: backend ? backend.fileProgress : 0; Layout.fillWidth: true }
                        Label { text: backend ? backend.fileProgressText : "Файл: --"; color: Theme.muted }
                        ProgressBar { from: 0; to: 1; value: backend ? backend.totalProgress : 0; Layout.fillWidth: true }
                        Label { text: backend ? backend.totalProgressText : "Всього: --"; color: Theme.muted }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: backend ? backend.onboardingVisible : false
        color: Qt.rgba(3 / 255, 10 / 255, 20 / 255, 0.78)
        z: 20

        MouseArea {
            anchors.fill: parent
        }

        Card {
            width: Math.min(root.width - Theme.space4 * 2, 860)
            anchors.centerIn: parent

            ColumnLayout {
                spacing: Theme.space3

                Label {
                    text: "Перший запуск"
                    color: Theme.accent2
                    font.pixelSize: 12
                    font.weight: Font.Black
                    font.letterSpacing: 1.2
                }

                Label {
                    text: "Швидкий onboarding по інтерфейсу"
                    color: Theme.text
                    font.pixelSize: 28
                    font.weight: Font.Black
                }

                Label {
                    text: "UI уже має drag-and-drop, platform presets, queue preview і history. Тут коротко показано, з чого починати."
                    color: Theme.muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                GridLayout {
                    columns: root.compact ? 1 : 3
                    columnSpacing: Theme.space2
                    rowSpacing: Theme.space2
                    Layout.fillWidth: true

                    Repeater {
                        model: [
                            { step: "1", title: "Додай медіа", text: "Перетягни файли в hero-зону черги або натисни `Додати файли` / `Додати папку`." },
                            { step: "2", title: "Обери сценарій", text: "У вкладці `Старт` обери тип задачі і, якщо треба, застосуй готовий preset для YouTube, TikTok, Reels, Stories, Telegram або WhatsApp." },
                            { step: "3", title: "Налаштуй і перевір", text: "Деталі редагуй у вкладках `Відео`, `Фото`, `Аудіо`, `Субтитри`, а `Preview назв` і output folder перевір у вкладці `Проєкт`." }
                        ]

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 152
                            radius: Theme.radiusSection
                            color: Theme.sectionAlt
                            border.width: 1
                            border.color: Theme.border

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.sectionPadding
                                spacing: Theme.space1

                                Rectangle {
                                    width: 34
                                    height: 34
                                    radius: 17
                                    color: Theme.accentSoft
                                    border.width: 1
                                    border.color: Theme.accent2

                                    Label {
                                        anchors.centerIn: parent
                                        text: modelData.step
                                        color: Theme.accent2
                                        font.pixelSize: 14
                                        font.weight: Font.Black
                                    }
                                }

                                Label {
                                    text: modelData.title
                                    color: Theme.text
                                    font.pixelSize: 16
                                    font.weight: Font.Bold
                                }

                                Label {
                                    text: modelData.text
                                    color: Theme.muted
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Label {
                        text: "Підказка: onboarding показується лише для першого запуску."
                        color: Theme.subtleText
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }

                    GhostButton {
                        Layout.fillWidth: false
                        text: "Закрити"
                        onClicked: if (backend) backend.dismissOnboarding()
                    }

                    PrimaryButton {
                        Layout.fillWidth: false
                        text: "Почати"
                        onClicked: if (backend) backend.dismissOnboarding()
                    }
                }
            }
        }
    }
}
