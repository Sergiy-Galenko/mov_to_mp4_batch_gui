import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "components"

ApplicationWindow {
    id: root
    visible: true
    visibility: Window.Maximized
    minimumWidth: 1040
    minimumHeight: 700
    title: I18n.t("app.title")
    color: Theme.bgBase

    palette.window: Theme.bgBase
    palette.base: Theme.input
    palette.text: Theme.textPrimary
    palette.button: Theme.bgSurface
    palette.buttonText: Theme.textPrimary
    palette.highlight: Theme.accentPrimary
    palette.highlightedText: "#FFFFFF"

    property bool hasBackend: backend !== null
    property bool sidebarCollapsed: false
    property int activeSection: 0
    property bool logErrorsOnly: false
    property var validationResult: ({ ok: true, errors: {}, warnings: [], summary: "OK" })
    property bool formValid: true
    property string selectedPath: ""
    property int selectedIndex: -1
    property string selectedPreset: ""
    property real sharedShimmerPhase: 0
    property bool highLoadMode: backend ? backend.queueCount > 50 : false

    property var operationOptions: ["convert", "audio_only", "auto_subtitle", "subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet"]
    property var videoFormats: ["mp4", "mkv", "webm", "mov", "avi", "gif"]
    property var imageFormats: ["jpg", "png", "webp", "bmp", "tiff"]
    property var audioFormats: ["mp3", "m4a", "aac", "wav", "flac", "opus"]
    property var subtitleFormats: ["srt", "ass", "vtt"]
    property var codecOptions: ["Авто", "H.264 (AVC)", "H.265 (HEVC)", "AV1", "VP9 (WebM)"]
    property var hwOptions: ["Авто", "Тільки CPU", "NVIDIA (NVENC)", "Intel (QSV)", "AMD (AMF)"]
    property var rotateOptions: ["0", "90° вправо", "90° вліво", "180°"]
    property var portraitOptions: ["Вимкнено", "9:16 (1080x1920) - crop", "9:16 (1080x1920) - blur", "9:16 (720x1280) - crop", "9:16 (720x1280) - blur"]
    property var positionOptions: ["Верх-ліворуч", "Верх-праворуч", "Низ-ліворуч", "Низ-праворуч", "Центр"]

    NumberAnimation on sharedShimmerPhase {
        from: 0
        to: 1
        duration: 1200
        loops: Animation.Infinite
        running: !root.highLoadMode
    }

    function scheduleSettingsSync() {
        settingsSyncTimer.restart()
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
            "Конвертація": "convert",
            "Лише аудіо": "audio_only",
            "Авто субтитри": "auto_subtitle",
            "Витяг субтитрів": "subtitle_extract",
            "Вшити субтитри": "subtitle_burn",
            "Мініатюра": "thumbnail",
            "Контакт-лист": "contact_sheet",
            "Extract subtitle": "subtitle_extract",
            "Burn-in subtitle": "subtitle_burn",
            "Thumbnail": "thumbnail",
            "Contact sheet": "contact_sheet"
        }
        if (aliases[value] !== undefined)
            value = aliases[value]
        var idx = combo.find(String(value))
        if (idx >= 0)
            combo.currentIndex = idx
    }

    function applyPreset(preset) {
        if (settingsPanel)
            settingsPanel.applyPreset(preset)
    }

    function collectSettings() {
        return settingsPanel ? settingsPanel.collectSettings() : ({})
    }

    Timer {
        id: settingsSyncTimer
        interval: 260
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
        function onUiLanguageChanged() {
            I18n.language = backend.uiLanguage
            settingsPanel.syncLanguage()
        }
        function onWatermarkPicked(path) { settingsPanel.setPickedPath("watermark", path) }
        function onFontPicked(path) { settingsPanel.setPickedPath("font", path) }
        function onSubtitlePicked(path) { settingsPanel.setPickedPath("subtitle", path) }
        function onCoverArtPicked(path) { settingsPanel.setPickedPath("cover", path) }
        function onAudioReplacePicked(path) { settingsPanel.setPickedPath("audio", path) }
        function onOutputDirChanged() { settingsPanel.syncBackendPaths() }
        function onFfmpegPathChanged() { settingsPanel.syncBackendPaths() }
        function onWatchFolderChanged() { settingsPanel.syncBackendPaths() }
        function onTaskOverrideLoaded(data) {
            settingsPanel.loadTaskOverride(data)
        }
    }

    Component.onCompleted: {
        if (backend) {
            I18n.language = backend.uiLanguage
            backend.restoreSession()
            backend.refreshEncoders()
            scheduleSettingsSync()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.titlebarHeight
            color: Theme.bgBase
            border.width: 0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 10

                Button {
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 28
                    text: sidebarCollapsed ? ">" : "="
                    onClicked: sidebarCollapsed = !sidebarCollapsed
                }

                Label {
                    text: I18n.t("app.title")
                    color: Theme.textPrimary
                    font.family: Theme.displayFont
                    font.pixelSize: Theme.fontTitle
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                RowLayout {
                    spacing: 8
                    PulseDot {
                        dotColor: backend && backend.isRunning ? Theme.accentWarn : Theme.accentSuccess
                        running: backend ? backend.isRunning : false
                    }
                    Label {
                        text: backend && backend.isRunning ? I18n.t("live") : I18n.t("idle")
                        color: Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                    }
                    StatusPill { text: "CPU --"; accent: Theme.textSecondary }
                    StatusPill { text: "GPU --"; accent: Theme.accentPurple }
                    StatusPill { text: backend ? backend.encoderInfo : "FFmpeg --"; accent: Theme.accentPrimary; maxWidth: 260 }
                }

            }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.bgBorder }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            SidebarPanel {
                Layout.fillHeight: true
                collapsed: root.sidebarCollapsed
                activeIndex: root.activeSection
                onSectionRequested: function(index) { root.activeSection = index }
                onAddFilesRequested: backend && backend.addFiles()
                onAddFolderRequested: backend && backend.addFolder()
                onDedupeRequested: backend && backend.deduplicateQueueByHash()
            }

            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.bgBorder }

            SplitView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                orientation: Qt.Horizontal

                ScrollView {
                    id: mainScroll
                    SplitView.fillWidth: true
                    SplitView.minimumWidth: 620
                    clip: true

                    ColumnLayout {
                        width: mainScroll.availableWidth
                        spacing: 12
                        anchors.margins: 12

                        PresetsBar {
                            Layout.fillWidth: true
                            model: backend ? backend.presetsModel : null
                            activePreset: root.selectedPreset
                            onPresetSelected: function(name) {
                                root.selectedPreset = name
                                if (backend)
                                    backend.loadPreset(name)
                            }
                        }

                        StackLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.activeSection === 1 ? Math.max(520, root.height - 130) : Math.max(360, root.height * 0.45)
                            currentIndex: root.activeSection === 1 ? 1 : 0

                            Rectangle {
                                color: "transparent"
                                radius: 0

                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 10

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        Label {
                                            Layout.fillWidth: true
                                            text: I18n.t("queue")
                                            color: Theme.textPrimary
                                            font.family: Theme.displayFont
                                            font.pixelSize: Theme.fontHeading
                                            font.bold: true
                                        }
                                        Label {
                                            text: backend ? backend.queueCount + " " + I18n.t("files") : "0 " + I18n.t("files")
                                            color: Theme.textSecondary
                                            font.family: Theme.monoFont
                                            font.pixelSize: Theme.fontMeta
                                        }
                                        Button { text: I18n.t("add"); onClicked: backend && backend.addFiles() }
                                        Button { text: I18n.t("folder"); onClicked: backend && backend.addFolder() }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: Theme.radiusPanel
                                        color: Theme.bgSurface
                                        border.width: 1
                                        border.color: Theme.bgBorder
                                        clip: true

                                        DropZone {
                                            anchors.centerIn: parent
                                            width: Math.min(parent.width - 28, 680)
                                            visible: backend ? backend.queueCount === 0 : true
                                            onFilesDropped: function(urls) { backend && backend.addDroppedUrls(urls) }
                                            onClicked: backend && backend.addFiles()
                                        }

                                        ListView {
                                            id: queueList
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            visible: backend ? backend.queueCount > 0 : false
                                            model: backend ? backend.queueModel : null
                                            clip: true
                                            spacing: 8
                                            cacheBuffer: 200
                                            boundsBehavior: Flickable.StopAtBounds

                                            delegate: QueueItem {
                                                fileName: model.name
                                                filePath: model.path
                                                mediaType: model.mediaType
                                                status: model.status
                                                errorText: model.errorText
                                                outputPath: model.outputPath
                                                durationText: model.durationText
                                                sizeText: model.sizeText
                                                thumbnailSource: model.thumbnailSource
                                                progress: model.progress
                                                etaText: model.etaText
                                                speedText: model.speedText
                                                exitCode: model.exitCode
                                                hasOverride: model.hasOverride
                                                selected: root.selectedPath === model.path
                                                highLoadMode: root.highLoadMode
                                                shimmerPhase: root.sharedShimmerPhase
                                                onSelectedRequested: function(path) {
                                                    root.selectedPath = path
                                                    root.selectedIndex = index
                                                    if (backend)
                                                        backend.selectQueuePath(path)
                                                }
                                                onRetryRequested: function(path) { backend && backend.retryTaskPath(path) }
                                                onSkipRequested: function(path) { backend && backend.skipCurrentFile() }
                                                onRemoveRequested: function(path) { backend && backend.removeTaskPath(path) }
                                                onOverrideRequested: function(path) {
                                                    root.selectedPath = path
                                                    root.selectedIndex = index
                                                    root.activeSection = 4
                                                    if (backend)
                                                        backend.selectQueuePath(path)
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            AnalyticsPanel {
                                speedHistory: backend ? backend.speedHistory : []
                                fileTimings: backend ? backend.fileTimings : []
                                codecDistribution: backend ? backend.codecDistribution : ({})
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 104
                            spacing: 12

                            Rectangle {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                radius: Theme.radiusPanel
                                color: Theme.bgSurface
                                border.width: 1
                                border.color: Theme.bgBorder

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12
                                    ArcSpinner {
                                        arcSize: 56
                                        progress: backend ? backend.totalProgress : 0
                                        indeterminate: backend ? (backend.isRunning && backend.totalProgress <= 0.001) : false
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Label { text: I18n.t("total"); color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta }
                                        Label { text: backend ? Math.round(backend.totalProgress * 100) + "%" : "0%"; color: Theme.textPrimary; font.family: Theme.displayFont; font.pixelSize: Theme.fontHeading; font.bold: true }
                                        Label { text: backend ? backend.totalProgressText : "--"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.fontMeta; elide: Text.ElideRight; Layout.fillWidth: true }
                                    }
                                }
                            }

                            SessionStats {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                doneCount: backend ? backend.completedCount : 0
                                failedCount: backend ? backend.failedCount : 0
                                skippedCount: backend ? backend.skippedCount : 0
                                totalCount: backend ? backend.queueCount : 0
                                elapsedText: backend ? backend.sessionElapsedText : "00:00"
                                etaText: backend ? backend.sessionEtaText : "--:--"
                                avgSpeedText: backend ? backend.sessionAvgSpeedText : "--"
                                savedText: backend ? backend.sessionSavedText : "0 B"
                                inputText: backend ? backend.sessionInputText : "0 B"
                                outputText: backend ? backend.sessionOutputText : "0 B"
                            }
                        }

                        AnalyticsPanel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 360
                            visible: root.activeSection !== 1
                            speedHistory: backend ? backend.speedHistory : []
                            fileTimings: backend ? backend.fileTimings : []
                            codecDistribution: backend ? backend.codecDistribution : ({})
                        }

                        LogPanel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.activeSection === 3 ? 260 : 160
                        }
                    }
                }

                ScrollView {
                    id: settingsScroll
                    SplitView.preferredWidth: root.activeSection === 4 || root.activeSection === 2 || root.activeSection === 3 ? 420 : 360
                    SplitView.minimumWidth: 320
                    clip: true

                    ColumnLayout {
                        width: settingsScroll.availableWidth
                        spacing: 12
                        anchors.margins: 12

                        SettingsPanel {
                            id: settingsPanel
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }

    component StatusPill: Rectangle {
        property alias text: pillText.text
        property color accent: Theme.textSecondary
        property int maxWidth: 120
        Layout.maximumWidth: maxWidth
        Layout.preferredHeight: 24
        Layout.preferredWidth: Math.min(maxWidth, pillText.implicitWidth + 18)
        radius: Theme.radiusPill
        color: Qt.rgba(1, 1, 1, 0.035)
        border.width: 1
        border.color: Theme.bgBorder
        Label {
            id: pillText
            anchors.centerIn: parent
            width: parent.width - 14
            elide: Text.ElideRight
            color: parent.accent
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
            horizontalAlignment: Text.AlignHCenter
        }
    }

    component Panel: Rectangle {
        default property alias content: panelColumn.data
        property string title: ""
        Layout.fillWidth: true
        radius: Theme.radiusPanel
        color: Theme.bgSurface
        border.width: 1
        border.color: Theme.bgBorder
        implicitHeight: panelColumn.implicitHeight + 26

        ColumnLayout {
            id: panelColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 12
            spacing: 8

            Label {
                visible: parent.parent.title.length > 0
                text: parent.parent.title
                color: Theme.textPrimary
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }
        }
    }

    component FieldLabel: Label {
        color: Theme.textMuted
        font.family: Theme.monoFont
        font.pixelSize: Theme.fontMeta
        Layout.fillWidth: true
    }

    component LogPanel: Panel {
        title: I18n.t("log")
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: backend ? backend.statusText : "Ready"
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSmall
                elide: Text.ElideRight
            }
            Button { text: I18n.t("export"); onClicked: backend && backend.exportLog() }
            Button { text: I18n.t("clear"); onClicked: backend && backend.clearLog() }
        }
        ListView {
            Layout.fillWidth: true
            Layout.preferredHeight: 104
            model: backend ? backend.logModel : null
            clip: true
            spacing: 4
            delegate: Label {
                width: ListView.view.width
                text: model.line
                color: model.level === "ERROR" ? Theme.accentError : model.level === "WARN" ? Theme.accentWarn : Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                elide: Text.ElideRight
            }
        }
    }

    component SettingsPanel: ColumnLayout {
        id: settingsRoot
        spacing: 12

        function applyPreset(preset) {
            if (!preset)
                return
            if (preset.operation) root.setComboText(operationCombo, preset.operation)
            if (preset.out_video_fmt) root.setComboText(outVideoFmt, preset.out_video_fmt)
            if (preset.out_image_fmt) root.setComboText(outImageFmt, preset.out_image_fmt)
            if (preset.out_audio_fmt) root.setComboText(outAudioFmt, preset.out_audio_fmt)
            if (preset.out_subtitle_fmt) root.setComboText(outSubtitleFmt, preset.out_subtitle_fmt)
            if (preset.audio_bitrate) audioBitrateField.text = preset.audio_bitrate
            if (preset.audio_track_index !== undefined) audioTrackSpin.value = Number(preset.audio_track_index) + 1
            if (preset.crf !== undefined) crfSpin.value = Number(preset.crf)
            if (preset.preset) root.setComboText(presetCombo, preset.preset)
            if (preset.portrait) root.setComboText(portraitCombo, preset.portrait)
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
            if (preset.rotate) root.setComboText(rotateCombo, preset.rotate)
            speedField.text = preset.speed || ""
            root.setComboText(subtitleModeCombo, preset.subtitle_mode || "none")
            subtitlePathField.text = preset.subtitle_path || ""
            if (preset.subtitle_stream !== undefined) subtitleStreamSpin.value = Number(preset.subtitle_stream)
            subtitleLanguageField.text = preset.subtitle_language || "auto"
            root.setComboText(subtitleModelCombo, preset.subtitle_model || "base")
            root.setComboText(subtitleEngineCombo, preset.subtitle_engine || "auto")
            thumbnailTimeField.text = preset.thumbnail_time || ""
            if (preset.sheet_cols !== undefined) sheetColsSpin.value = Number(preset.sheet_cols)
            if (preset.sheet_rows !== undefined) sheetRowsSpin.value = Number(preset.sheet_rows)
            if (preset.sheet_width !== undefined) sheetWidthSpin.value = Number(preset.sheet_width)
            if (preset.sheet_interval !== undefined) sheetIntervalSpin.value = Number(preset.sheet_interval)
            wmPathField.text = preset.wm_path || ""
            if (preset.wm_pos) root.setComboText(wmPosCombo, preset.wm_pos)
            if (preset.wm_opacity !== undefined) wmOpacitySpin.value = Number(preset.wm_opacity)
            if (preset.wm_scale !== undefined) wmScaleSpin.value = Number(preset.wm_scale)
            textWatermarkField.text = preset.text_wm || ""
            if (preset.text_pos) root.setComboText(textPosCombo, preset.text_pos)
            if (preset.text_size !== undefined) textSizeSpin.value = Number(preset.text_size)
            textColorField.text = preset.text_color || "white"
            textBoxCheck.checked = !!preset.text_box
            textBoxColorField.text = preset.text_box_color || "black"
            if (preset.text_box_opacity !== undefined) textBoxOpacitySpin.value = Number(preset.text_box_opacity)
            textFontField.text = preset.text_font || ""
            if (preset.codec) root.setComboText(codecCombo, preset.codec)
            if (preset.hw) root.setComboText(hwCombo, preset.hw)
            replaceAudioPathField.text = preset.replace_audio_path || ""
            root.setComboText(normalizeAudioCombo, preset.normalize_audio || "none")
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
            root.scheduleSettingsSync()
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

        function setPickedPath(kind, path) {
            if (kind === "watermark") wmPathField.text = path
            else if (kind === "font") textFontField.text = path
            else if (kind === "subtitle") subtitlePathField.text = path
            else if (kind === "cover") coverArtField.text = path
            else if (kind === "audio") replaceAudioPathField.text = path
            root.scheduleSettingsSync()
        }

        function syncBackendPaths() {
            if (!backend)
                return
            outputDirField.text = backend.outputDir
            ffmpegPathField.text = backend.ffmpegPath
            watchFolderField.text = backend.watchFolder
        }

        function syncLanguage() {
            if (!backend)
                return
            languageCombo.currentIndex = backend.uiLanguage === "en" ? 1 : 0
        }

        function loadTaskOverride(data) {
            overrideOutputTemplateField.text = data.output_template || ""
            if (data.crf !== undefined)
                overrideCrfSpin.value = Number(data.crf)
            overrideAudioBitrateField.text = data.audio_bitrate || ""
        }

        Panel {
            title: I18n.t("run")
            FieldLabel { text: I18n.t("language") }
            AppComboBox {
                id: languageCombo
                model: [I18n.t("ukrainian"), I18n.t("english")]
                currentIndex: backend && backend.uiLanguage === "en" ? 1 : 0
                onActivated: {
                    if (backend)
                        backend.uiLanguage = currentIndex === 1 ? "en" : "uk"
                    I18n.language = currentIndex === 1 ? "en" : "uk"
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Button { text: backend && backend.isRunning ? I18n.t("running") : I18n.t("start"); enabled: backend && !backend.isRunning && formValid; onClicked: startIfValid() }
                Button { text: backend && backend.isPaused ? I18n.t("resume") : I18n.t("pause"); enabled: backend && backend.isRunning; onClicked: backend.isPaused ? backend.resumeConversion() : backend.pauseConversion() }
                Button { text: I18n.t("skip"); enabled: backend && backend.isRunning; onClicked: backend.skipCurrentFile() }
                Button { text: I18n.t("stop"); enabled: backend && backend.isRunning; onClicked: backend.stopConversion() }
            }
            Label {
                Layout.fillWidth: true
                text: validationResult && validationResult.summary ? validationResult.summary : ""
                color: formValid ? Theme.textMuted : Theme.accentError
                font.pixelSize: Theme.fontMeta
                wrapMode: Text.WordWrap
            }
        }

        Panel {
            title: I18n.t("presets")
            AppComboBox { id: savedPresetCombo; model: backend ? backend.presetsModel : null }
            RowLayout {
                Layout.fillWidth: true
                Button { text: I18n.t("load"); onClicked: { root.selectedPreset = savedPresetCombo.currentText; backend && backend.loadPreset(savedPresetCombo.currentText) } }
                Button { text: I18n.t("save"); onClicked: backend && backend.savePreset(savedPresetCombo.currentText || "Custom", collectSettings()) }
                Button { text: I18n.t("delete"); onClicked: backend && backend.deletePreset(savedPresetCombo.currentText) }
            }
        }

        Panel {
            title: I18n.t("core")
            FieldLabel { text: I18n.t("operation") }
            AppComboBox { id: operationCombo; model: root.operationOptions; onActivated: scheduleSettingsSync() }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                FieldLabel { text: I18n.t("video") }
                AppComboBox { id: outVideoFmt; model: root.videoFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("image") }
                AppComboBox { id: outImageFmt; model: root.imageFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("audio") }
                AppComboBox { id: outAudioFmt; model: root.audioFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("subtitle") }
                AppComboBox { id: outSubtitleFmt; model: root.subtitleFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("codec") }
                AppComboBox { id: codecCombo; model: root.codecOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("hw") }
                AppComboBox { id: hwCombo; model: root.hwOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: "CRF" }
                AppSpinBox { id: crfSpin; from: 0; to: 51; value: 23; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("preset") }
                AppComboBox { id: presetCombo; model: ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]; currentIndex: 5; onActivated: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: overwriteCheck; text: I18n.t("overwrite"); onToggled: scheduleSettingsSync() }
                AppCheckBox { id: fastCopyCheck; text: I18n.t("fast_copy"); onToggled: scheduleSettingsSync() }
                AppCheckBox { id: skipExistingCheck; text: I18n.t("skip_existing"); onToggled: scheduleSettingsSync() }
            }
        }

        Panel {
            title: I18n.t("output")
            AppTextField { id: outputDirField; text: backend ? backend.outputDir : ""; onEditingFinished: { if (backend) backend.outputDir = text; scheduleSettingsSync() } }
            RowLayout {
                Layout.fillWidth: true
                Button { text: I18n.t("choose"); onClicked: backend && backend.pickOutputDir() }
                Button { text: I18n.t("open"); onClicked: backend && backend.openOutputDir() }
                Button { text: I18n.t("preview"); onClicked: backend && backend.refreshOutputPreview(collectSettings()) }
            }
            FieldLabel { text: I18n.t("template") }
            AppTextField { id: outputTemplateField; text: "{stem}"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("platform_profile") }
            AppTextField { id: platformProfileField; onEditingFinished: scheduleSettingsSync() }
            Label {
                Layout.fillWidth: true
                text: backend ? backend.outputPreviewText : ""
                color: Theme.textSecondary
                font.family: Theme.monoFont
                font.pixelSize: Theme.fontMeta
                wrapMode: Text.WordWrap
                maximumLineCount: 5
                elide: Text.ElideRight
            }
        }

        Panel {
            title: I18n.t("video")
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                FieldLabel { text: I18n.t("portrait") }
                AppComboBox { id: portraitCombo; model: root.portraitOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("resize_w") }
                AppTextField { id: resizeWField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("resize_h") }
                AppTextField { id: resizeHField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("crop_w") }
                AppTextField { id: cropWField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("crop_h") }
                AppTextField { id: cropHField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("crop_x") }
                AppTextField { id: cropXField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("crop_y") }
                AppTextField { id: cropYField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("rotate") }
                AppComboBox { id: rotateCombo; model: root.rotateOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("speed") }
                AppTextField { id: speedField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("trim_start") }
                AppTextField { id: trimStartField; placeholderText: "00:00:00"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("trim_end") }
                AppTextField { id: trimEndField; placeholderText: "00:00:10"; onEditingFinished: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: mergeCheck; text: I18n.t("merge"); onToggled: scheduleSettingsSync() }
                AppTextField { id: mergeNameField; text: "merged"; onEditingFinished: scheduleSettingsSync() }
            }
        }

        Panel {
            title: I18n.t("audio_subtitles")
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                FieldLabel { text: I18n.t("bitrate") }
                AppTextField { id: audioBitrateField; text: "192k"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("track") }
                AppSpinBox { id: audioTrackSpin; from: 1; to: 32; value: 1; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("normalize") }
                AppComboBox { id: normalizeAudioCombo; model: ["none", "ebu_r128", "peak"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("peak_db") }
                AppTextField { id: peakLimitField; placeholderText: "-1.0"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("silence_db") }
                AppSpinBox { id: silenceThresholdSpin; from: -90; to: -5; value: -50; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("silence_sec") }
                AppTextField { id: silenceDurationField; text: "0.3"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("subtitle_mode") }
                AppComboBox { id: subtitleModeCombo; model: ["none", "burn", "extract"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("subtitle_path") }
                RowLayout {
                    Layout.fillWidth: true
                    AppTextField { id: subtitlePathField; onEditingFinished: scheduleSettingsSync() }
                    Button { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickSubtitle() }
                }
                FieldLabel { text: I18n.t("subtitle_stream") }
                AppSpinBox { id: subtitleStreamSpin; from: 0; to: 32; value: 0; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("language_field") }
                AppTextField { id: subtitleLanguageField; text: "auto"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("model") }
                AppComboBox { id: subtitleModelCombo; model: ["tiny", "base", "small", "medium", "large"]; currentIndex: 1; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("engine") }
                AppComboBox { id: subtitleEngineCombo; model: ["auto", "whisper"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: trimSilenceCheck; text: I18n.t("trim_silence"); onToggled: scheduleSettingsSync() }
                AppCheckBox { id: splitChaptersCheck; text: I18n.t("split_chapters"); onToggled: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppTextField { id: replaceAudioPathField; placeholderText: I18n.t("replace_audio_path"); onEditingFinished: scheduleSettingsSync() }
                Button { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickAudioReplace() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppTextField { id: coverArtField; placeholderText: I18n.t("cover_art"); onEditingFinished: scheduleSettingsSync() }
                Button { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickCoverArt() }
            }
        }

        Panel {
            title: I18n.t("images_sheets")
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                FieldLabel { text: I18n.t("image_quality") }
                AppSpinBox { id: imgQualitySpin; from: 1; to: 100; value: 90; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("thumbnail_time") }
                AppTextField { id: thumbnailTimeField; placeholderText: "00:00:05"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("sheet_cols") }
                AppSpinBox { id: sheetColsSpin; from: 1; to: 12; value: 4; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("sheet_rows") }
                AppSpinBox { id: sheetRowsSpin; from: 1; to: 12; value: 4; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("sheet_width") }
                AppSpinBox { id: sheetWidthSpin; from: 80; to: 1920; value: 320; stepSize: 10; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("sheet_interval") }
                AppSpinBox { id: sheetIntervalSpin; from: 1; to: 600; value: 10; onValueChanged: scheduleSettingsSync() }
            }
        }

        Panel {
            title: I18n.t("watermark_text")
            RowLayout {
                Layout.fillWidth: true
                AppTextField { id: wmPathField; placeholderText: I18n.t("watermark_image"); onEditingFinished: scheduleSettingsSync() }
                Button { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickWatermark() }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                FieldLabel { text: I18n.t("position") }
                AppComboBox { id: wmPosCombo; model: root.positionOptions; currentIndex: 3; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("opacity") }
                AppSpinBox { id: wmOpacitySpin; from: 0; to: 100; value: 80; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("scale") }
                AppSpinBox { id: wmScaleSpin; from: 1; to: 100; value: 30; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("text") }
                AppTextField { id: textWatermarkField; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("text_pos") }
                AppComboBox { id: textPosCombo; model: root.positionOptions; currentIndex: 3; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("text_size") }
                AppSpinBox { id: textSizeSpin; from: 6; to: 200; value: 24; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("text_color") }
                AppTextField { id: textColorField; text: "white"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("box_color") }
                AppTextField { id: textBoxColorField; text: "black"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("box_opacity") }
                AppSpinBox { id: textBoxOpacitySpin; from: 0; to: 100; value: 50; onValueChanged: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: textBoxCheck; text: I18n.t("text_box"); onToggled: scheduleSettingsSync() }
                AppTextField { id: textFontField; placeholderText: I18n.t("font_path"); onEditingFinished: scheduleSettingsSync() }
                Button { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickFont() }
            }
        }

        Panel {
            title: I18n.t("metadata_hooks")
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: stripMetadataCheck; text: I18n.t("strip"); onToggled: scheduleSettingsSync() }
                AppCheckBox { id: copyMetadataCheck; text: I18n.t("copy"); onToggled: scheduleSettingsSync() }
            }
            AppTextField { id: metaTitleField; placeholderText: I18n.t("title"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaAuthorField; placeholderText: I18n.t("author"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaCommentField; placeholderText: I18n.t("comment"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaCopyrightField; placeholderText: I18n.t("copyright"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaAlbumField; placeholderText: I18n.t("album"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaGenreField; placeholderText: I18n.t("genre"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaYearField; placeholderText: I18n.t("year"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: metaTrackField; placeholderText: I18n.t("track_meta"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: beforeHookField; placeholderText: I18n.t("before_hook"); onEditingFinished: scheduleSettingsSync() }
            AppTextField { id: afterHookField; placeholderText: I18n.t("after_hook"); onEditingFinished: scheduleSettingsSync() }
        }

        Panel {
            title: I18n.t("selected_override")
            AppTextField { id: overrideOutputTemplateField; placeholderText: I18n.t("output_template_override") }
            AppSpinBox { id: overrideCrfSpin; from: 0; to: 51; value: 23 }
            AppTextField { id: overrideAudioBitrateField; placeholderText: I18n.t("audio_bitrate_override") }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: I18n.t("save")
                    enabled: root.selectedPath.length > 0
                    onClicked: backend && backend.saveTaskOverrideByPath(root.selectedPath, {
                        output_template: overrideOutputTemplateField.text,
                        crf: overrideCrfSpin.value,
                        audio_bitrate: overrideAudioBitrateField.text
                    })
                }
                Button { text: I18n.t("clear"); enabled: root.selectedPath.length > 0; onClicked: backend && backend.clearTaskOverrideByPath(root.selectedPath) }
            }
        }

        Panel {
            title: I18n.t("ffmpeg_watch")
            AppTextField { id: ffmpegPathField; text: backend ? backend.ffmpegPath : ""; onEditingFinished: { if (backend) backend.ffmpegPath = text } }
            RowLayout {
                Layout.fillWidth: true
                Button { text: I18n.t("choose"); onClicked: backend && backend.pickFfmpeg() }
                Button { text: I18n.t("refresh"); onClicked: backend && backend.refreshEncoders() }
            }
            Label { Layout.fillWidth: true; text: backend ? backend.encoderInfo : ""; color: Theme.textMuted; wrapMode: Text.WordWrap; font.pixelSize: Theme.fontMeta }
            AppTextField { id: watchFolderField; text: backend ? backend.watchFolder : ""; placeholderText: I18n.t("watch_folder"); onEditingFinished: { if (backend) backend.watchFolder = text } }
            RowLayout {
                Layout.fillWidth: true
                Button { text: I18n.t("choose"); onClicked: backend && backend.pickWatchFolder() }
                Button { text: backend && backend.watchRunning ? I18n.t("stop_watch") : I18n.t("start_watch"); onClicked: backend && (backend.watchRunning ? backend.stopWatching() : backend.startWatching()) }
            }
            RowLayout {
                Layout.fillWidth: true
                Button { text: I18n.t("import"); onClicked: backend && backend.importProject() }
                Button { text: I18n.t("export"); onClicked: backend && backend.exportProject(collectSettings()) }
            }
        }
    }
}
