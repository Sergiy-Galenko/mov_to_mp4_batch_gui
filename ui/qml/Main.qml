import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "components"

ApplicationWindow {
    id: root
    visible: true
    visibility: Window.Maximized
    minimumWidth: 980
    minimumHeight: 680
    title: backend ? backend.appTitle : "Media Converter"
    color: Theme.bg

    palette.window: Theme.bg
    palette.base: Theme.input
    palette.text: Theme.text
    palette.button: Theme.panel
    palette.buttonText: Theme.text
    palette.highlight: Theme.accent
    palette.highlightedText: "#FFFFFF"

    property bool hasBackend: backend !== null
    property int activeParamTab: 0
    property bool logErrorsOnly: false
    property var validationResult: ({ ok: true, errors: {}, warnings: [], summary: "Перевірка пройдена." })
    property bool formValid: true
    property string selectedPath: ""
    property int selectedIndex: -1
    property var operationOptions: [
        "Конвертація",
        "Лише аудіо",
        "Авто субтитри",
        "Витяг субтитрів",
        "Вшити субтитри",
        "Мініатюра",
        "Контакт-лист"
    ]
    property var videoFormats: ["mp4", "mkv", "webm", "mov", "avi", "gif"]
    property var imageFormats: ["jpg", "png", "webp", "bmp", "tiff"]
    property var audioFormats: ["mp3", "m4a", "aac", "wav", "flac", "opus"]
    property var subtitleFormats: ["srt", "ass", "vtt"]
    property var codecOptions: ["Авто", "H.264 (AVC)", "H.265 (HEVC)", "AV1", "VP9 (WebM)"]
    property var hwOptions: ["Авто", "Тільки CPU", "NVIDIA (NVENC)", "Intel (QSV)", "AMD (AMF)"]
    property var rotateOptions: ["0", "90° вправо", "90° вліво", "180°"]
    property var portraitOptions: [
        "Вимкнено",
        "9:16 (1080x1920) - crop",
        "9:16 (1080x1920) - blur",
        "9:16 (720x1280) - crop",
        "9:16 (720x1280) - blur"
    ]
    property var positionOptions: ["Верх-ліворуч", "Верх-праворуч", "Низ-ліворуч", "Низ-праворуч", "Центр"]

    function scheduleSettingsSync() {
        settingsSyncTimer.restart()
    }

    function fieldError(name) {
        if (!validationResult || !validationResult.errors)
            return ""
        return validationResult.errors[name] || ""
    }

    function validateForm() {
        if (!backend)
            return true
        validationResult = backend.validateSettings(collectSettings())
        formValid = !!validationResult.ok
        return formValid
    }

    function startIfValid() {
        if (!validateForm())
            return
        backend.startConversion(collectSettings())
    }

    function setComboText(combo, value) {
        if (!combo || value === undefined || value === null)
            return
        var aliases = {
            "Extract subtitle": "Витяг субтитрів",
            "Burn-in subtitle": "Вшити субтитри",
            "Thumbnail": "Мініатюра",
            "Contact sheet": "Контакт-лист"
        }
        if (aliases[value] !== undefined)
            value = aliases[value]
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
        if (preset.crf !== undefined) crfSpin.value = Number(preset.crf)
        if (preset.preset) setComboText(presetCombo, preset.preset)
        if (preset.portrait) setComboText(portraitCombo, preset.portrait)
        if (preset.img_quality !== undefined) imgQualitySpin.value = Number(preset.img_quality)
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
        speedField.text = preset.speed || ""
        setComboText(subtitleModeCombo, preset.subtitle_mode || "none")
        subtitlePathField.text = preset.subtitle_path || ""
        if (preset.subtitle_stream !== undefined) subtitleStreamSpin.value = Number(preset.subtitle_stream)
        subtitleLanguageField.text = preset.subtitle_language || "auto"
        setComboText(subtitleModelCombo, preset.subtitle_model || "base")
        setComboText(subtitleEngineCombo, preset.subtitle_engine || "auto")
        thumbnailTimeField.text = preset.thumbnail_time || ""
        if (preset.sheet_cols !== undefined) sheetColsSpin.value = Number(preset.sheet_cols)
        if (preset.sheet_rows !== undefined) sheetRowsSpin.value = Number(preset.sheet_rows)
        if (preset.sheet_width !== undefined) sheetWidthSpin.value = Number(preset.sheet_width)
        if (preset.sheet_interval !== undefined) sheetIntervalSpin.value = Number(preset.sheet_interval)
        wmPathField.text = preset.wm_path || ""
        if (preset.wm_pos) setComboText(wmPosCombo, preset.wm_pos)
        if (preset.wm_opacity !== undefined) wmOpacitySpin.value = Number(preset.wm_opacity)
        if (preset.wm_scale !== undefined) wmScaleSpin.value = Number(preset.wm_scale)
        textWatermarkField.text = preset.text_wm || ""
        if (preset.text_pos) setComboText(textPosCombo, preset.text_pos)
        if (preset.text_size !== undefined) textSizeSpin.value = Number(preset.text_size)
        textColorField.text = preset.text_color || "white"
        textBoxCheck.checked = !!preset.text_box
        textBoxColorField.text = preset.text_box_color || "black"
        if (preset.text_box_opacity !== undefined) textBoxOpacitySpin.value = Number(preset.text_box_opacity)
        textFontField.text = preset.text_font || ""
        if (preset.codec) setComboText(codecCombo, preset.codec)
        if (preset.hw) setComboText(hwCombo, preset.hw)
        replaceAudioPathField.text = preset.replace_audio_path || ""
        setComboText(normalizeAudioCombo, preset.normalize_audio || "none")
        peakLimitField.text = preset.audio_peak_limit_db || ""
        trimSilenceCheck.checked = !!preset.trim_silence
        silenceThresholdSpin.value = preset.silence_threshold_db !== undefined ? Number(preset.silence_threshold_db) : -50
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
        scheduleSettingsSync()
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

    function statusColor(status) {
        if (status === "success") return Theme.success
        if (status === "failed") return Theme.danger
        if (status === "skipped") return Theme.warning
        if (status === "cancelled") return Theme.subtleText
        if (status === "running" || status === "paused" || status === "analyzing") return Theme.running
        if (status === "ready") return Theme.accent2
        return Theme.muted
    }

    function statusLabel(status) {
        if (status === "queued") return "у черзі"
        if (status === "analyzing") return "аналіз"
        if (status === "ready") return "готово"
        if (status === "running") return "в роботі"
        if (status === "paused") return "пауза"
        if (status === "success") return "успіх"
        if (status === "failed") return "помилка"
        if (status === "skipped") return "пропущено"
        if (status === "cancelled") return "скасовано"
        return status
    }

    Timer {
        id: settingsSyncTimer
        interval: 280
        repeat: false
        onTriggered: {
            validateForm()
            if (backend)
                backend.refreshOutputPreview(collectSettings())
        }
    }

    Connections {
        target: backend
        function onPresetLoaded(data) { applyPreset(data) }
        function onWatermarkPicked(path) { wmPathField.text = path; scheduleSettingsSync() }
        function onFontPicked(path) { textFontField.text = path; scheduleSettingsSync() }
        function onSubtitlePicked(path) { subtitlePathField.text = path; scheduleSettingsSync() }
        function onCoverArtPicked(path) { coverArtField.text = path; scheduleSettingsSync() }
        function onAudioReplacePicked(path) { replaceAudioPathField.text = path; scheduleSettingsSync() }
        function onTaskOverrideLoaded(data) {
            overrideOutputTemplateField.text = data.output_template || ""
            if (data.crf !== undefined) overrideCrfSpin.value = Number(data.crf)
            overrideAudioBitrateField.text = data.audio_bitrate || ""
        }
    }

    Component.onCompleted: {
        if (backend) {
            backend.restoreSession()
            backend.refreshEncoders()
            scheduleSettingsSync()
        }
    }

    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (backend && drop.hasUrls)
                backend.addDroppedUrls(drop.urls)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space2
        spacing: Theme.space2

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 48
            color: Theme.panel
            radius: Theme.radiusCard
            border.width: 1
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.space2
                spacing: Theme.space2

                Label {
                    text: "Media Converter"
                    color: Theme.text
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }

                Label {
                    text: backend ? backend.statusText : "Готово"
                    color: Theme.muted
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Label { text: "Черга: " + (backend ? backend.queueCount : 0); color: Theme.muted; font.pixelSize: 12 }
                Label { text: "Помилки: " + (backend ? backend.failedCount : 0); color: Theme.danger; font.pixelSize: 12 }

                PrimaryButton {
                    Layout.preferredWidth: 118
                    text: backend && backend.isRunning ? "В роботі" : "Запустити"
                    enabled: backend && !backend.isRunning && formValid
                    onClicked: startIfValid()
                }
                SecondaryButton {
                    Layout.preferredWidth: 96
                    text: backend && backend.isPaused ? "Resume" : "Pause"
                    enabled: backend && backend.isRunning
                    onClicked: backend.isPaused ? backend.resumeConversion() : backend.pauseConversion()
                }
                SecondaryButton {
                    Layout.preferredWidth: 88
                    text: "Skip"
                    enabled: backend && backend.isRunning
                    onClicked: backend.skipCurrentFile()
                }
                GhostButton {
                    Layout.preferredWidth: 86
                    text: "Stop"
                    enabled: backend && backend.isRunning
                    onClicked: backend.stopConversion()
                }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Card {
                SplitView.preferredWidth: 360
                SplitView.minimumWidth: 300
                title: "Черга"

                ColumnLayout {
                    spacing: Theme.space2

                    GridLayout {
                        columns: 2
                        columnSpacing: Theme.space1
                        rowSpacing: Theme.space1
                        Layout.fillWidth: true

                        PrimaryButton { text: "Додати файли"; onClicked: backend.addFiles() }
                        SecondaryButton { text: "Додати папку"; onClicked: backend.addFolder() }
                        GhostButton { text: "Dedupe"; onClicked: backend.deduplicateQueue() }
                        GhostButton { text: "Hash dedupe"; onClicked: backend.deduplicateQueueByHash() }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 54
                        radius: Theme.radiusSection
                        color: Theme.section
                        border.width: 1
                        border.color: Theme.border

                        Label {
                            anchors.fill: parent
                            anchors.margins: Theme.space1
                            text: "Перетягни сюди файли або папки. Підтримуються відео, зображення, аудіо й субтитри."
                            color: Theme.muted
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    ListView {
                        id: queueList
                        model: backend ? backend.queueModel : null
                        clip: true
                        spacing: Theme.space1
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        delegate: Rectangle {
                            width: ListView.view.width
                            implicitHeight: 78
                            color: root.selectedPath === model.path ? Theme.sectionAlt : Theme.section
                            border.width: 1
                            border.color: root.selectedPath === model.path ? Theme.focusRing : Theme.border
                            radius: Theme.radiusSection

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.selectedPath = model.path
                                    root.selectedIndex = index
                                    backend.selectQueueIndex(index)
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: Theme.space1
                                spacing: Theme.space1

                                Rectangle {
                                    Layout.preferredWidth: 42
                                    Layout.preferredHeight: 42
                                    radius: Theme.radiusInput
                                    color: Theme.input
                                    border.width: 1
                                    border.color: Theme.border

                                    Image {
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        source: model.thumbnailSource
                                        fillMode: Image.PreserveAspectCrop
                                        visible: source !== ""
                                    }

                                    Label {
                                        anchors.centerIn: parent
                                        visible: model.thumbnailSource === ""
                                        text: model.mediaType === "video" ? "VID" : model.mediaType === "image" ? "IMG" : model.mediaType === "audio" ? "AUD" : "SUB"
                                        color: Theme.muted
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Label {
                                        text: model.name
                                        color: Theme.text
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: model.previewOutput || model.path
                                        color: Theme.subtleText
                                        font.pixelSize: 11
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                    RowLayout {
                                        spacing: Theme.space1
                                        Label { text: statusLabel(model.status); color: statusColor(model.status); font.pixelSize: 11 }
                                        Label { text: model.durationText; color: Theme.subtleText; font.pixelSize: 11 }
                                        Label { text: model.sizeText; color: Theme.subtleText; font.pixelSize: 11 }
                                        Label { text: model.hasOverride ? "override" : ""; color: Theme.warning; font.pixelSize: 11 }
                                    }
                                }

                                GhostButton {
                                    Layout.preferredWidth: 42
                                    text: "×"
                                    onClicked: backend.removeTaskPath(model.path)
                                }
                            }
                        }
                    }

                    GridLayout {
                        columns: 4
                        columnSpacing: Theme.space1
                        Layout.fillWidth: true
                        GhostButton { text: "↑"; onClicked: backend.moveSelectedPathsUp([root.selectedPath]) }
                        GhostButton { text: "↓"; onClicked: backend.moveSelectedPathsDown([root.selectedPath]) }
                        SecondaryButton { text: "Retry"; onClicked: backend.retryTaskPath(root.selectedPath) }
                        GhostButton { text: "Очистити"; onClicked: backend.clearQueue() }
                    }
                }
            }

            Card {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 460
                title: "Операція, параметри й preview"

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: Theme.space2

                        Section {
                            title: "Операція та пресети"
                            GridLayout {
                                columns: root.width < 1180 ? 2 : 4
                                columnSpacing: Theme.space2
                                rowSpacing: Theme.space1
                                Layout.fillWidth: true

                                Label { text: "Операція"; color: Theme.muted }
                                AppComboBox { id: operationCombo; model: root.operationOptions; onCurrentTextChanged: scheduleSettingsSync() }
                                Label { text: "Пресет"; color: Theme.muted }
                                AppComboBox { id: savedPresetCombo; model: backend ? backend.presetsModel : null }

                                Label { text: "Назва нового"; color: Theme.muted }
                                AppTextField { id: presetNameField; placeholderText: "Мій пресет" }
                                RowLayout {
                                    Layout.columnSpan: 2
                                    Layout.fillWidth: true
                                    SecondaryButton { text: "Завантажити"; onClicked: backend.loadPreset(savedPresetCombo.currentText) }
                                    SecondaryButton { text: "Зберегти"; onClicked: backend.savePreset(presetNameField.text, collectSettings()) }
                                    GhostButton { text: "Видалити"; onClicked: backend.deletePreset(savedPresetCombo.currentText) }
                                }
                            }
                        }

                        Section {
                            title: "Вивід і шаблони"
                            GridLayout {
                                columns: root.width < 1180 ? 2 : 4
                                columnSpacing: Theme.space2
                                rowSpacing: Theme.space1
                                Layout.fillWidth: true

                                Label { text: "Папка"; color: Theme.muted }
                                AppTextField {
                                    id: outputDirField
                                    text: backend ? backend.outputDir : ""
                                    invalid: fieldError("output_dir") !== ""
                                    onEditingFinished: { if (backend) backend.outputDir = text; scheduleSettingsSync() }
                                }
                                SecondaryButton { text: "Обрати"; onClicked: backend.pickOutputDir() }
                                GhostButton { text: "Відкрити"; onClicked: backend.openOutputDir() }

                                Label { text: "Шаблон"; color: Theme.muted }
                                AppTextField { id: outputTemplateField; text: "{stem}"; invalid: fieldError("output_template") !== ""; placeholderText: "{stem}_{index}"; onTextChanged: scheduleSettingsSync() }
                                AppCheckBox { id: overwriteCheck; text: "Перезапис"; onCheckedChanged: scheduleSettingsSync() }
                                AppCheckBox { id: skipExistingCheck; text: "Skip existing"; onCheckedChanged: scheduleSettingsSync() }

                                Label { text: "Формати"; color: Theme.muted }
                                AppComboBox { id: outVideoFmt; model: root.videoFormats; onCurrentTextChanged: scheduleSettingsSync() }
                                AppComboBox { id: outImageFmt; model: root.imageFormats; onCurrentTextChanged: scheduleSettingsSync() }
                                AppComboBox { id: outAudioFmt; model: root.audioFormats; onCurrentTextChanged: scheduleSettingsSync() }

                                Label { text: "Субтитри"; color: Theme.muted }
                                AppComboBox { id: outSubtitleFmt; model: root.subtitleFormats; onCurrentTextChanged: scheduleSettingsSync() }
                                AppTextField { id: platformProfileField; placeholderText: "YouTube / TikTok / custom"; onTextChanged: scheduleSettingsSync() }
                                AppCheckBox { id: fastCopyCheck; text: "Fast copy"; onCheckedChanged: scheduleSettingsSync() }
                            }
                        }

                        Section {
                            title: "Параметри"
                            ColumnLayout {
                                spacing: Theme.space2
                                TabBar {
                                    id: paramsTabs
                                    Layout.fillWidth: true
                                    currentIndex: root.activeParamTab
                                    onCurrentIndexChanged: root.activeParamTab = currentIndex
                                    TabButton { text: "Кодеки" }
                                    TabButton { text: "Монтаж" }
                                    TabButton { text: "Аудіо" }
                                    TabButton { text: "Субтитри" }
                                    TabButton { text: "Overlay" }
                                    TabButton { text: "Мета" }
                                }

                                GridLayout {
                                    visible: root.activeParamTab === 0
                                    columns: root.width < 1180 ? 2 : 4
                                    columnSpacing: Theme.space2
                                    rowSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    Label { text: "Кодек"; color: Theme.muted }
                                    AppComboBox { id: codecCombo; model: root.codecOptions; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Hardware"; color: Theme.muted }
                                    AppComboBox { id: hwCombo; model: root.hwOptions; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "CRF"; color: Theme.muted }
                                    AppSpinBox { id: crfSpin; from: 0; to: 63; value: 23; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Preset"; color: Theme.muted }
                                    AppComboBox { id: presetCombo; model: ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]; currentIndex: 5; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Якість зображень"; color: Theme.muted }
                                    AppSpinBox { id: imgQualitySpin; from: 1; to: 100; value: 90; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Вертикальний формат"; color: Theme.muted }
                                    AppComboBox { id: portraitCombo; model: root.portraitOptions; onCurrentTextChanged: scheduleSettingsSync() }
                                }

                                GridLayout {
                                    visible: root.activeParamTab === 1
                                    columns: root.width < 1180 ? 2 : 4
                                    columnSpacing: Theme.space2
                                    rowSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    Label { text: "Trim start"; color: Theme.muted }
                                    AppTextField { id: trimStartField; placeholderText: "00:00:05"; invalid: fieldError("trim_start") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Trim end"; color: Theme.muted }
                                    AppTextField { id: trimEndField; placeholderText: "00:01:10"; invalid: fieldError("trim_end") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Resize W"; color: Theme.muted }
                                    AppTextField { id: resizeWField; placeholderText: "1920"; invalid: fieldError("resize_w") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Resize H"; color: Theme.muted }
                                    AppTextField { id: resizeHField; placeholderText: "1080"; invalid: fieldError("resize_h") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Crop W/H"; color: Theme.muted }
                                    AppTextField { id: cropWField; placeholderText: "w"; invalid: fieldError("crop_w") !== ""; onTextChanged: scheduleSettingsSync() }
                                    AppTextField { id: cropHField; placeholderText: "h"; invalid: fieldError("crop_h") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Crop X/Y"; color: Theme.muted }
                                    AppTextField { id: cropXField; placeholderText: "x"; invalid: fieldError("crop_x") !== ""; onTextChanged: scheduleSettingsSync() }
                                    AppTextField { id: cropYField; placeholderText: "y"; invalid: fieldError("crop_y") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Rotate"; color: Theme.muted }
                                    AppComboBox { id: rotateCombo; model: root.rotateOptions; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Speed"; color: Theme.muted }
                                    AppTextField { id: speedField; placeholderText: "1.25"; invalid: fieldError("speed") !== ""; onTextChanged: scheduleSettingsSync() }
                                    AppCheckBox { id: mergeCheck; text: "Merge відео"; onCheckedChanged: scheduleSettingsSync() }
                                    AppTextField { id: mergeNameField; text: "merged"; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Thumbnail time"; color: Theme.muted }
                                    AppTextField { id: thumbnailTimeField; placeholderText: "00:00:05"; invalid: fieldError("thumbnail_time") !== ""; onTextChanged: scheduleSettingsSync() }
                                }

                                GridLayout {
                                    visible: root.activeParamTab === 2
                                    columns: root.width < 1180 ? 2 : 4
                                    columnSpacing: Theme.space2
                                    rowSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    Label { text: "Бітрейт"; color: Theme.muted }
                                    AppTextField { id: audioBitrateField; text: "192k"; invalid: fieldError("audio_bitrate") !== ""; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Доріжка"; color: Theme.muted }
                                    AppSpinBox { id: audioTrackSpin; from: 1; to: 32; value: 1; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Normalize"; color: Theme.muted }
                                    AppComboBox { id: normalizeAudioCombo; model: ["none", "ebu_r128"]; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Peak limit dB"; color: Theme.muted }
                                    AppTextField { id: peakLimitField; placeholderText: "-1.0"; invalid: fieldError("audio_peak_limit_db") !== ""; onTextChanged: scheduleSettingsSync() }
                                    AppCheckBox { id: trimSilenceCheck; text: "Trim silence"; onCheckedChanged: scheduleSettingsSync() }
                                    AppSpinBox { id: silenceThresholdSpin; from: -90; to: 0; value: -50; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Silence duration"; color: Theme.muted }
                                    AppTextField { id: silenceDurationField; text: "0.3"; invalid: fieldError("silence_duration") !== ""; onTextChanged: scheduleSettingsSync() }
                                    AppCheckBox { id: splitChaptersCheck; text: "Split chapters"; onCheckedChanged: scheduleSettingsSync() }
                                    Label { text: "Cover art"; color: Theme.muted }
                                    AppTextField { id: coverArtField; invalid: fieldError("cover_art_path") !== ""; onTextChanged: scheduleSettingsSync() }
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickCoverArt() }
                                    Label { text: "Замінити аудіо"; color: Theme.muted }
                                    AppTextField { id: replaceAudioPathField; invalid: fieldError("replace_audio_path") !== ""; onTextChanged: scheduleSettingsSync() }
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickAudioReplace() }
                                }

                                GridLayout {
                                    visible: root.activeParamTab === 3
                                    columns: root.width < 1180 ? 2 : 4
                                    columnSpacing: Theme.space2
                                    rowSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    Label { text: "Режим"; color: Theme.muted }
                                    AppComboBox { id: subtitleModeCombo; model: ["none", "burn_in"]; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Файл"; color: Theme.muted }
                                    AppTextField { id: subtitlePathField; invalid: fieldError("subtitle_path") !== ""; onTextChanged: scheduleSettingsSync() }
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickSubtitle() }
                                    Label { text: "Stream"; color: Theme.muted }
                                    AppSpinBox { id: subtitleStreamSpin; from: 0; to: 32; value: 0; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Мова"; color: Theme.muted }
                                    AppTextField { id: subtitleLanguageField; text: "auto"; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Whisper model"; color: Theme.muted }
                                    AppComboBox { id: subtitleModelCombo; model: ["tiny", "base", "small", "medium", "large"]; currentIndex: 1; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Engine"; color: Theme.muted }
                                    AppComboBox { id: subtitleEngineCombo; model: ["auto", "whisper"]; onCurrentTextChanged: scheduleSettingsSync() }
                                }

                                GridLayout {
                                    visible: root.activeParamTab === 4
                                    columns: root.width < 1180 ? 2 : 4
                                    columnSpacing: Theme.space2
                                    rowSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    Label { text: "Watermark"; color: Theme.muted }
                                    AppTextField { id: wmPathField; invalid: fieldError("wm_path") !== ""; onTextChanged: scheduleSettingsSync() }
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickWatermark() }
                                    AppComboBox { id: wmPosCombo; model: root.positionOptions; currentIndex: 3; onCurrentTextChanged: scheduleSettingsSync() }
                                    Label { text: "Opacity"; color: Theme.muted }
                                    AppSpinBox { id: wmOpacitySpin; from: 0; to: 100; value: 80; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Scale"; color: Theme.muted }
                                    AppSpinBox { id: wmScaleSpin; from: 1; to: 100; value: 30; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Text overlay"; color: Theme.muted }
                                    AppTextField { id: textWatermarkField; onTextChanged: scheduleSettingsSync() }
                                    AppComboBox { id: textPosCombo; model: root.positionOptions; currentIndex: 3; onCurrentTextChanged: scheduleSettingsSync() }
                                    AppSpinBox { id: textSizeSpin; from: 8; to: 160; value: 24; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Text color"; color: Theme.muted }
                                    AppTextField { id: textColorField; text: "white"; onTextChanged: scheduleSettingsSync() }
                                    AppCheckBox { id: textBoxCheck; text: "Box"; onCheckedChanged: scheduleSettingsSync() }
                                    AppTextField { id: textBoxColorField; text: "black"; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Box opacity"; color: Theme.muted }
                                    AppSpinBox { id: textBoxOpacitySpin; from: 0; to: 100; value: 50; onValueChanged: scheduleSettingsSync() }
                                    Label { text: "Font"; color: Theme.muted }
                                    AppTextField { id: textFontField; invalid: fieldError("text_font") !== ""; onTextChanged: scheduleSettingsSync() }
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickFont() }
                                }

                                GridLayout {
                                    visible: root.activeParamTab === 5
                                    columns: root.width < 1180 ? 2 : 4
                                    columnSpacing: Theme.space2
                                    rowSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    AppCheckBox { id: copyMetadataCheck; text: "Копіювати метадані"; checked: true; onCheckedChanged: scheduleSettingsSync() }
                                    AppCheckBox { id: stripMetadataCheck; text: "Очистити метадані"; onCheckedChanged: scheduleSettingsSync() }
                                    Label { text: "Title"; color: Theme.muted }
                                    AppTextField { id: metaTitleField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Author"; color: Theme.muted }
                                    AppTextField { id: metaAuthorField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Album"; color: Theme.muted }
                                    AppTextField { id: metaAlbumField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Genre"; color: Theme.muted }
                                    AppTextField { id: metaGenreField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Year"; color: Theme.muted }
                                    AppTextField { id: metaYearField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Track"; color: Theme.muted }
                                    AppTextField { id: metaTrackField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Comment"; color: Theme.muted }
                                    AppTextField { id: metaCommentField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Copyright"; color: Theme.muted }
                                    AppTextField { id: metaCopyrightField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "Before hook"; color: Theme.muted }
                                    AppTextField { id: beforeHookField; onTextChanged: scheduleSettingsSync() }
                                    Label { text: "After hook"; color: Theme.muted }
                                    AppTextField { id: afterHookField; onTextChanged: scheduleSettingsSync() }
                                }

                                GridLayout {
                                    columns: 4
                                    columnSpacing: Theme.space1
                                    Layout.fillWidth: true
                                    AppSpinBox { id: sheetColsSpin; visible: false; from: 1; to: 20; value: 4 }
                                    AppSpinBox { id: sheetRowsSpin; visible: false; from: 1; to: 20; value: 4 }
                                    AppSpinBox { id: sheetWidthSpin; visible: false; from: 80; to: 2000; value: 320 }
                                    AppSpinBox { id: sheetIntervalSpin; visible: false; from: 1; to: 3600; value: 10 }
                                }
                            }
                        }

                        Section {
                            title: "Preview output і dry-run"
                            ColumnLayout {
                                spacing: Theme.space1
                                Label {
                                    text: validationResult.summary
                                    color: formValid ? Theme.accent2 : Theme.danger
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                                AppTextArea {
                                    text: backend ? backend.outputPreviewText : ""
                                    readOnly: true
                                    wrapMode: TextEdit.NoWrap
                                    Layout.preferredHeight: 150
                                }
                                GridLayout {
                                    columns: 2
                                    Layout.fillWidth: true
                                    Label { text: "Вхідний"; color: Theme.muted }
                                    Label { text: backend ? backend.selectedPreviewSource : "—"; color: Theme.text; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                    Label { text: "Вихідний"; color: Theme.muted }
                                    Label { text: backend ? backend.selectedPreviewOutput : "—"; color: Theme.text; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                }
                                AppTextArea {
                                    text: backend ? backend.selectedPreviewCommand : ""
                                    readOnly: true
                                    wrapMode: TextEdit.Wrap
                                    Layout.preferredHeight: 92
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    SecondaryButton { text: "Оновити"; onClicked: backend.refreshOutputPreview(collectSettings()) }
                                    SecondaryButton { text: "Копіювати команду"; onClicked: backend.copyDryRunCommand(collectSettings()) }
                                    SecondaryButton { text: "Експорт script"; onClicked: backend.exportCommandScript(collectSettings()) }
                                    Item { Layout.fillWidth: true }
                                    PrimaryButton { Layout.preferredWidth: 130; text: "Запустити"; enabled: formValid && backend && !backend.isRunning; onClicked: startIfValid() }
                                }
                            }
                        }
                    }
                }
            }

            Card {
                SplitView.preferredWidth: 350
                SplitView.minimumWidth: 310
                title: "Інспектор і система"

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: Theme.space2

                        Section {
                            title: "Вибраний файл"
                            GridLayout {
                                columns: 2
                                columnSpacing: Theme.space1
                                rowSpacing: Theme.space1
                                Layout.fillWidth: true
                                Label { text: "Назва"; color: Theme.muted }
                                Label { text: backend ? backend.infoName : "—"; color: Theme.text; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                Label { text: "Тривалість"; color: Theme.muted }
                                Label { text: backend ? backend.infoDuration : "--:--"; color: Theme.text }
                                Label { text: "Кодеки"; color: Theme.muted }
                                Label { text: backend ? backend.infoCodec : "—"; color: Theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: "Розмір"; color: Theme.muted }
                                Label { text: backend ? backend.infoRes + " / " + backend.infoSize : "—"; color: Theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: "Контейнер"; color: Theme.muted }
                                Label { text: backend ? backend.infoContainer : "—"; color: Theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                            Label { text: backend ? backend.infoAnalysis : "—"; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Label { text: backend ? backend.infoWarnings : "—"; color: Theme.warning; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            RowLayout {
                                Layout.fillWidth: true
                                SecondaryButton { text: "Джерело"; enabled: root.selectedPath !== ""; onClicked: backend.openSourcePath(root.selectedPath) }
                                SecondaryButton { text: "Output"; enabled: root.selectedPath !== ""; onClicked: backend.openOutputForPath(root.selectedPath) }
                            }
                        }

                        Section {
                            title: "Override для файла"
                            GridLayout {
                                columns: 2
                                columnSpacing: Theme.space1
                                rowSpacing: Theme.space1
                                Layout.fillWidth: true
                                Label { text: "Шаблон"; color: Theme.muted }
                                AppTextField { id: overrideOutputTemplateField; placeholderText: "порожньо = загальний" }
                                Label { text: "CRF"; color: Theme.muted }
                                AppSpinBox { id: overrideCrfSpin; from: 0; to: 63; value: 23 }
                                Label { text: "Audio bitrate"; color: Theme.muted }
                                AppTextField { id: overrideAudioBitrateField; placeholderText: "192k" }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                SecondaryButton {
                                    text: "Зберегти"
                                    enabled: root.selectedIndex >= 0
                                    onClicked: backend.saveTaskOverride(root.selectedIndex, {
                                        output_template: overrideOutputTemplateField.text,
                                        crf: overrideCrfSpin.value,
                                        audio_bitrate: overrideAudioBitrateField.text
                                    })
                                }
                                GhostButton { text: "Очистити"; enabled: root.selectedIndex >= 0; onClicked: backend.clearTaskOverride(root.selectedIndex) }
                            }
                        }

                        Section {
                            title: "FFmpeg"
                            ColumnLayout {
                                spacing: Theme.space1
                                AppTextField {
                                    id: ffmpegPathField
                                    text: backend ? backend.ffmpegPath : ""
                                    invalid: fieldError("ffmpeg") !== ""
                                    onEditingFinished: { if (backend) backend.ffmpegPath = text; scheduleSettingsSync() }
                                }
                                Label { text: backend ? backend.encoderInfo : ""; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                RowLayout {
                                    Layout.fillWidth: true
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickFfmpeg() }
                                    SecondaryButton { text: "Перевірити"; onClicked: backend.refreshEncoders() }
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
                                    onEditingFinished: { if (backend) backend.watchFolder = text }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    SecondaryButton { text: "Обрати"; onClicked: backend.pickWatchFolder() }
                                    SecondaryButton { text: backend && backend.watchRunning ? "Зупинити" : "Старт"; onClicked: backend.watchRunning ? backend.stopWatching() : backend.startWatching() }
                                }
                            }
                        }

                        Section {
                            title: "Проєкт та історія"
                            ColumnLayout {
                                spacing: Theme.space1
                                RowLayout {
                                    Layout.fillWidth: true
                                    SecondaryButton { text: "Import"; onClicked: backend.importProject() }
                                    SecondaryButton { text: "Export"; onClicked: backend.exportProject(collectSettings()) }
                                }
                                ListView {
                                    model: backend ? backend.historyModel : null
                                    clip: true
                                    spacing: Theme.space1
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 170
                                    delegate: Rectangle {
                                        width: ListView.view.width
                                        implicitHeight: 58
                                        color: Theme.sectionAlt
                                        radius: Theme.radiusSection
                                        border.width: 1
                                        border.color: Theme.border
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: Theme.space1
                                            spacing: 2
                                            Label { text: model.startedText + " · " + model.operation; color: Theme.text; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                            Label { text: "Файлів: " + model.totalFiles + "  Помилок: " + model.failedFiles + "  Пропущено: " + model.skippedFiles; color: Theme.muted; font.pixelSize: 11 }
                                            Label { text: model.outputDir; color: Theme.subtleText; font.pixelSize: 10; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                        }
                                        MouseArea { anchors.fill: parent; onDoubleClicked: backend.loadHistorySettings(index) }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    SecondaryButton { text: "Завантажити"; onClicked: backend.loadHistorySettings(0) }
                                    SecondaryButton { text: "Повторити"; onClicked: backend.rerunHistory(0) }
                                    GhostButton { text: "Очистити"; onClicked: backend.clearHistory() }
                                }
                            }
                        }
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true
            Layout.preferredHeight: 210
            title: "Прогрес і журнал"

            ColumnLayout {
                spacing: Theme.space2

                GridLayout {
                    columns: root.width < 1100 ? 1 : 5
                    columnSpacing: Theme.space2
                    rowSpacing: Theme.space1
                    Layout.fillWidth: true

                    Label { text: backend ? backend.statusText : "Готово"; color: Theme.text; elide: Text.ElideRight; Layout.fillWidth: true }
                    ProgressBar { from: 0; to: 1; value: backend ? backend.fileProgress : 0; Layout.fillWidth: true }
                    Label { text: backend ? backend.fileProgressText : "Файл: --"; color: Theme.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                    ProgressBar { from: 0; to: 1; value: backend ? backend.totalProgress : 0; Layout.fillWidth: true }
                    Label { text: backend ? backend.totalProgressText : "Всього: --"; color: Theme.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                }

                RowLayout {
                    Layout.fillWidth: true
                    GhostButton { Layout.preferredWidth: 130; text: root.logErrorsOnly ? "Усі повідомлення" : "Тільки помилки"; onClicked: root.logErrorsOnly = !root.logErrorsOnly }
                    GhostButton { Layout.preferredWidth: 100; text: "Експорт"; onClicked: backend.exportLog() }
                    GhostButton { Layout.preferredWidth: 100; text: "Очистити"; onClicked: backend.clearLog() }
                    Item { Layout.fillWidth: true }
                }

                ListView {
                    id: logList
                    model: backend ? backend.logModel : null
                    clip: true
                    spacing: Theme.space1
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: visible ? Math.max(30, logMessage.implicitHeight + 12) : 0
                        visible: !root.logErrorsOnly || model.level === "ERROR" || model.level === "WARN"
                        color: model.level === "ERROR" ? Theme.dangerSoft : model.level === "WARN" ? Theme.warningSoft : Theme.section
                        radius: Theme.radiusInput
                        border.width: 1
                        border.color: model.level === "ERROR" ? Theme.danger : model.level === "WARN" ? Theme.warning : Theme.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.space1
                            spacing: Theme.space1
                            Label { text: model.timeText; color: Theme.subtleText; font.pixelSize: 10; Layout.preferredWidth: 54 }
                            Label { text: model.level; color: model.level === "ERROR" ? Theme.danger : model.level === "WARN" ? Theme.warning : Theme.muted; font.pixelSize: 10; font.weight: Font.DemiBold; Layout.preferredWidth: 42 }
                            Label { id: logMessage; text: model.message; color: Theme.text; wrapMode: Text.WordWrap; font.pixelSize: 11; Layout.fillWidth: true }
                            GhostButton { Layout.preferredWidth: 58; text: "Copy"; onClicked: backend.copyLogLine(index) }
                        }
                    }
                }
            }
        }
    }
}
