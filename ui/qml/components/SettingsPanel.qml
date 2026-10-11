import QtQuick 2.15
import QtQml 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

ColumnLayout {
    id: settingsRoot
    objectName: "settingsPanelRoot"
    property var controller
    property var targetEstimate: ({})
    function refreshTargetEstimate() {
        targetEstimate = backend ? backend.targetSizeEstimate(collectSettings()) : ({})
    }
    Connections {
        target: backend
        function onOutputPreviewChanged() { settingsRoot.refreshTargetEstimate() }
        function onSelectedDetailsChanged() { settingsRoot.refreshTargetEstimate() }
    }
    function scheduleSettingsSync() { controller.scheduleSettingsSync() }
    spacing: Theme.space5
    readonly property string page: controller.pendingSettingsTarget || "core"
    readonly property bool compactFields: width < 720
    property string subtitleDevice: "auto"

    WhisperModelManagerModal {
        id: whisperModal
        selectedModel: subtitleModelCombo.currentText
        selectedDevice: settingsRoot.subtitleDevice
        selectedEngine: subtitleEngineCombo.currentText
        onModelChosen: function(name) {
            controller.setComboText(subtitleModelCombo, name)
            controller.scheduleSettingsSync()
        }
        onDeviceChosen: function(device) {
            settingsRoot.subtitleDevice = device
            controller.scheduleSettingsSync()
        }
        onEngineChosen: function(engine) {
            settingsRoot.subtitleDevice = "auto"
            controller.setComboText(subtitleEngineCombo, engine)
            controller.scheduleSettingsSync()
        }
    }

    function applyPreset(preset) {
        if (!preset)
            return
        if (preset.operation) controller.setComboText(operationCombo, preset.operation)
        if (preset.out_video_fmt) controller.setComboText(outVideoFmt, preset.out_video_fmt)
        if (preset.out_image_fmt) controller.setComboText(outImageFmt, preset.out_image_fmt)
        if (preset.out_audio_fmt) controller.setComboText(outAudioFmt, preset.out_audio_fmt)
        if (preset.out_subtitle_fmt) controller.setComboText(outSubtitleFmt, preset.out_subtitle_fmt)
        if (preset.out_text_fmt) controller.setComboText(outTextFmt, preset.out_text_fmt)
        if (preset.audio_bitrate) audioBitrateField.text = preset.audio_bitrate
        if (preset.audio_codec) controller.setComboText(audioCodecCombo, preset.audio_codec)
        if (preset.audio_track_index !== undefined) audioTrackSpin.value = Number(preset.audio_track_index) + 1
        if (preset.crf !== undefined) crfSpin.value = Number(preset.crf)
        if (preset.preset) controller.setComboText(presetCombo, preset.preset)
        if (preset.performance_profile) controller.setComboText(performanceProfileCombo, preset.performance_profile)
        targetSizeField.text = preset.target_size_mb || ""
        if (preset.concurrency_limit !== undefined && backend) backend.concurrencyLimit = Number(preset.concurrency_limit)
        if (preset.cpu_load_limit !== undefined) cpuLimitSpin.value = Number(preset.cpu_load_limit)
        if (preset.gpu_load_limit !== undefined) gpuLimitSpin.value = Number(preset.gpu_load_limit)
        smartConvertCheck.checked = !!preset.smart_convert_enabled
        controller.setComboText(smartContentTypeCombo, preset.smart_content_type || "auto")
        controller.setComboText(smartQualityTargetCombo, preset.smart_quality_target || "balanced")
        smartReencodeCheck.checked = preset.smart_reencode_detection === undefined ? true : !!preset.smart_reencode_detection
        smartTwoPassCheck.checked = !!preset.smart_two_pass
        smartIntegrityCheck.checked = !!preset.smart_integrity_check
        controller.setComboText(smartQualityMetricCombo, preset.smart_quality_metric || "none")
        smartAbTestCheck.checked = !!preset.smart_ab_test
        smartAbCrfsField.text = preset.smart_ab_crfs || "18,23,28"
        if (preset.smart_ab_duration !== undefined) smartAbDurationSpin.value = Number(preset.smart_ab_duration)
        controller.setComboCanonical(portraitCombo, preset.portrait || controller.portraitCanonicalOptions[0], controller.portraitCanonicalOptions)
        if (preset.img_quality !== undefined) imgQualitySpin.value = Number(preset.img_quality)
        overwriteCheck.checked = !!preset.overwrite
        fastCopyCheck.checked = !!preset.fast_copy
        skipExistingCheck.checked = !!preset.skip_existing
        controller.setComboText(collisionPolicyCombo, preset.output_collision_policy || (preset.overwrite ? "overwrite" : preset.skip_existing ? "skip" : "index"))
        if (preset.disk_safety_margin_mb !== undefined) diskSafetyMarginSpin.value = Number(preset.disk_safety_margin_mb)
        outputTemplateField.text = preset.output_template || "{stem}"
        commercialExportCheck.checked = !!preset.commercial_export
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
        if (preset.rotate) controller.setComboCanonical(rotateCombo, preset.rotate, controller.rotateCanonicalOptions)
        speedField.text = preset.speed || ""
        controller.setComboText(subtitleModeCombo, preset.subtitle_mode || "none")
        subtitlePathField.text = preset.subtitle_path || ""
        if (preset.subtitle_stream !== undefined) subtitleStreamSpin.value = Number(preset.subtitle_stream)
        subtitleLanguageField.text = preset.subtitle_language || "auto"
        controller.setComboText(subtitleModelCombo, preset.subtitle_model || "base")
        controller.setComboText(subtitleEngineCombo, preset.subtitle_engine || "auto")
        settingsRoot.subtitleDevice = preset.subtitle_device || "auto"
        thumbnailTimeField.text = preset.thumbnail_time || ""
        if (preset.sheet_cols !== undefined) sheetColsSpin.value = Number(preset.sheet_cols)
        if (preset.sheet_rows !== undefined) sheetRowsSpin.value = Number(preset.sheet_rows)
        if (preset.sheet_width !== undefined) sheetWidthSpin.value = Number(preset.sheet_width)
        if (preset.sheet_interval !== undefined) sheetIntervalSpin.value = Number(preset.sheet_interval)
        wmPathField.text = preset.wm_path || ""
        if (preset.wm_pos) controller.setComboCanonical(wmPosCombo, preset.wm_pos, controller.positionCanonicalOptions)
        if (preset.wm_opacity !== undefined) wmOpacitySpin.value = Number(preset.wm_opacity)
        if (preset.wm_scale !== undefined) wmScaleSpin.value = Number(preset.wm_scale)
        textWatermarkField.text = preset.text_wm || ""
        if (preset.text_pos) controller.setComboCanonical(textPosCombo, preset.text_pos, controller.positionCanonicalOptions)
        if (preset.text_size !== undefined) textSizeSpin.value = Number(preset.text_size)
        textColorField.text = preset.text_color || "white"
        textBoxCheck.checked = !!preset.text_box
        textBoxColorField.text = preset.text_box_color || "black"
        if (preset.text_box_opacity !== undefined) textBoxOpacitySpin.value = Number(preset.text_box_opacity)
        textFontField.text = preset.text_font || ""
        if (preset.codec) controller.setComboText(codecCombo, preset.codec)
        if (preset.hw) controller.setComboText(hwCombo, preset.hw)
        replaceAudioPathField.text = preset.replace_audio_path || ""
        controller.setComboText(normalizeAudioCombo, preset.normalize_audio || "none")
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
        privacyBlurRegionsField.text = preset.privacy_blur_regions || ""
        aiBlurCheck.checked = !!preset.ai_blur_enabled
        checksumCombo.currentIndex = Math.max(0, checksumCombo.find(preset.checksum_algorithm || "none"))
        secureDeleteCheck.checked = !!preset.secure_delete_original
        subtitleSyncField.text = preset.subtitle_sync_ms || ""
        subtitleStyleCheck.checked = !!preset.subtitle_style_enabled
        subtitleFontNameField.text = preset.subtitle_font_name || ""
        if (preset.subtitle_font_size !== undefined) subtitleFontSizeSpin.value = Number(preset.subtitle_font_size)
        subtitlePrimaryColorField.text = preset.subtitle_primary_color || "white"
        if (preset.subtitle_outline !== undefined) subtitleOutlineSpin.value = Number(preset.subtitle_outline)
        if (preset.subtitle_shadow !== undefined) subtitleShadowSpin.value = Number(preset.subtitle_shadow)
        if (preset.subtitle_alignment !== undefined) subtitleAlignmentSpin.value = Number(preset.subtitle_alignment)
        editorDeinterlaceCheck.checked = !!preset.editor_deinterlace
        editorStabilizeCheck.checked = !!preset.editor_stabilize
        controller.setComboText(editorDenoiseCombo, preset.editor_denoise || "none")
        editorBrightnessField.text = preset.editor_brightness || ""
        editorContrastField.text = preset.editor_contrast || ""
        editorSaturationField.text = preset.editor_saturation || ""
        editorGammaField.text = preset.editor_gamma || ""
        editorLutPathField.text = preset.editor_lut_path || ""
        cloudUploadCheck.checked = !!preset.cloud_upload_enabled
        controller.setComboText(cloudProviderCombo, preset.cloud_provider || "rclone")
        cloudRclonePathField.text = preset.cloud_rclone_path || "rclone"
        cloudRemotePathField.text = preset.cloud_remote_path || ""
        controller.scheduleSettingsSync()
    }

    function setOutputFormatFor(mediaType, format) {
        if (!format || format.length === 0)
            return
        if (mediaType === "image")
            controller.setComboText(outImageFmt, format)
        else if (mediaType === "audio")
            controller.setComboText(outAudioFmt, format)
        else if (mediaType === "subtitle")
            controller.setComboText(outSubtitleFmt, format)
        else if (mediaType === "text")
            controller.setComboText(outTextFmt, format)
        else
            controller.setComboText(outVideoFmt, format)
        controller.scheduleSettingsSync()
    }

    function applyWorkload(data) {
        cpuLimitSpin.value = data.cpu_load_limit
        gpuLimitSpin.value = data.gpu_load_limit
        controller.scheduleSettingsSync()
    }

    function collectSettings() {
        return {
            operation: operationCombo.currentText,
            out_video_fmt: outVideoFmt.currentText,
            out_image_fmt: outImageFmt.currentText,
            out_audio_fmt: outAudioFmt.currentText,
            out_subtitle_fmt: outSubtitleFmt.currentText,
            out_text_fmt: outTextFmt.currentText,
            audio_bitrate: audioBitrateField.text,
            audio_codec: audioCodecCombo.currentText,
            audio_track_index: audioTrackSpin.value - 1,
            crf: crfSpin.value,
            preset: presetCombo.currentText,
            performance_profile: performanceProfileCombo.currentText,
            target_size_mb: targetSizeField.text,
            concurrency_limit: backend ? backend.concurrencyLimit : 0,
            cpu_load_limit: cpuLimitSpin.value,
            gpu_load_limit: gpuLimitSpin.value,
            disk_safety_margin_mb: diskSafetyMarginSpin.value,
            smart_convert_enabled: smartConvertCheck.checked,
            smart_content_type: smartContentTypeCombo.currentText,
            smart_quality_target: smartQualityTargetCombo.currentText,
            smart_reencode_detection: smartReencodeCheck.checked,
            smart_two_pass: smartTwoPassCheck.checked,
            smart_integrity_check: smartIntegrityCheck.checked,
            smart_quality_metric: smartQualityMetricCombo.currentText,
            smart_ab_test: smartAbTestCheck.checked,
            smart_ab_crfs: smartAbCrfsField.text,
            smart_ab_duration: smartAbDurationSpin.value,
            portrait: controller.canonicalOption(controller.portraitCanonicalOptions, portraitCombo.currentIndex, portraitCombo.currentText),
            img_quality: imgQualitySpin.value,
            overwrite: overwriteCheck.checked,
            fast_copy: fastCopyCheck.checked,
            skip_existing: skipExistingCheck.checked,
            output_collision_policy: collisionPolicyCombo.currentText,
            output_template: outputTemplateField.text,
            commercial_export: commercialExportCheck.checked,
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
            rotate: controller.canonicalOption(controller.rotateCanonicalOptions, rotateCombo.currentIndex, rotateCombo.currentText),
            speed: speedField.text,
            subtitle_mode: subtitleModeCombo.currentText,
            subtitle_path: subtitlePathField.text,
            subtitle_stream: subtitleStreamSpin.value,
            subtitle_out_fmt: outSubtitleFmt.currentText,
            subtitle_language: subtitleLanguageField.text,
            subtitle_model: subtitleModelCombo.currentText,
            subtitle_engine: subtitleEngineCombo.currentText,
            subtitle_device: settingsRoot.subtitleDevice,
            thumbnail_time: thumbnailTimeField.text,
            sheet_cols: sheetColsSpin.value,
            sheet_rows: sheetRowsSpin.value,
            sheet_width: sheetWidthSpin.value,
            sheet_interval: sheetIntervalSpin.value,
            wm_path: wmPathField.text,
            wm_pos: controller.canonicalOption(controller.positionCanonicalOptions, wmPosCombo.currentIndex, wmPosCombo.currentText),
            wm_opacity: wmOpacitySpin.value,
            wm_scale: wmScaleSpin.value,
            text_wm: textWatermarkField.text,
            text_pos: controller.canonicalOption(controller.positionCanonicalOptions, textPosCombo.currentIndex, textPosCombo.currentText),
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
            meta_track: metaTrackField.text,
            privacy_blur_regions: privacyBlurRegionsField.text,
            ai_blur_enabled: aiBlurCheck.checked,
            sanitize_metadata: stripMetadataCheck.checked,
            checksum_algorithm: checksumCombo.currentText,
            secure_delete_original: secureDeleteCheck.checked,
            subtitle_sync_ms: subtitleSyncField.text,
            subtitle_style_enabled: subtitleStyleCheck.checked,
            subtitle_font_name: subtitleFontNameField.text,
            subtitle_font_size: subtitleFontSizeSpin.value,
            subtitle_primary_color: subtitlePrimaryColorField.text,
            subtitle_outline: subtitleOutlineSpin.value,
            subtitle_shadow: subtitleShadowSpin.value,
            subtitle_alignment: subtitleAlignmentSpin.value,
            editor_deinterlace: editorDeinterlaceCheck.checked,
            editor_stabilize: editorStabilizeCheck.checked,
            editor_denoise: editorDenoiseCombo.currentText,
            editor_brightness: editorBrightnessField.text,
            editor_contrast: editorContrastField.text,
            editor_saturation: editorSaturationField.text,
            editor_gamma: editorGammaField.text,
            editor_lut_path: editorLutPathField.text,
            cloud_upload_enabled: cloudUploadCheck.checked,
            cloud_provider: cloudProviderCombo.currentText,
            cloud_rclone_path: cloudRclonePathField.text,
            cloud_remote_path: cloudRemotePathField.text
        }
    }

    function setPickedPath(kind, path) {
        if (kind === "watermark") wmPathField.text = path
        else if (kind === "font") textFontField.text = path
        else if (kind === "subtitle") subtitlePathField.text = path
        else if (kind === "cover") coverArtField.text = path
        else if (kind === "audio") replaceAudioPathField.text = path
        controller.scheduleSettingsSync()
    }

    function syncBackendPaths() {
        if (!backend)
            return
        outputDirField.text = backend.outputDir
        ffmpegPathField.text = backend.ffmpegPath
        watchFolderField.text = backend.watchFolder
    }

    function syncLanguage() {
        controller._langVersion += 1
    }

    function loadTaskOverride(data) {
        overrideOutputTemplateField.text = data.output_template || ""
        if (data.crf !== undefined)
            overrideCrfSpin.value = Number(data.crf)
        overrideAudioBitrateField.text = data.audio_bitrate || ""
    }


    Panel {
        id: runPanel
        objectName: "settingsPage_run"
        visible: settingsRoot.page === "run"
        iconName: "play"
        iconTint: "#34C759"
        title: I18n.t("run")
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton { text: backend && backend.isRunning ? I18n.t("running") : I18n.t("start"); enabled: backend && !backend.isRunning && formValid; onClicked: startIfValid() }
            SecondaryButton { text: backend && backend.isPaused ? I18n.t("resume") : I18n.t("pause"); enabled: backend && backend.isRunning; onClicked: backend.isPaused ? backend.resumeConversion() : backend.pauseConversion() }
            SecondaryButton { iconName: "skip"; text: I18n.t("skip"); enabled: backend && backend.isRunning; onClicked: backend.skipCurrentFile() }
            SecondaryButton { iconName: "stop"; text: I18n.t("stop"); enabled: backend && backend.isRunning; onClicked: backend.stopConversion() }
        }
        Label {
            Layout.fillWidth: true
            text: validationResult && validationResult.summary ? validationResult.summary : ""
            color: formValid ? Theme.textMuted : Theme.accentError
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
    }

    PresetManagerPanel {
        objectName: "settingsPage_run_presets"
        visible: settingsRoot.page === "run"
        service: backend
        settingsProvider: function() { return settingsRoot.collectSettings() }
        onPresetSelected: function(name) { controller.selectedPreset = name }
    }

    Panel {
        id: smartConvertPanel
        objectName: "settingsPage_smart_convert"
        visible: settingsRoot.page === "smart_convert"
        iconName: "sparkles"
        iconTint: "#AF52DE"
        title: I18n.t("smart_convert")
        AppSwitch { id: smartConvertCheck; objectName: "smartConvertSwitch"; text: I18n.t("smart_convert_enabled"); onToggled: scheduleSettingsSync() }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("smart_content_type") }
            AppComboBox { id: smartContentTypeCombo; model: controller.smartContentTypes; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("smart_quality_target") }
            AppComboBox { id: smartQualityTargetCombo; model: controller.smartQualityTargets; currentIndex: 1; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("smart_quality_metric") }
            AppComboBox { id: smartQualityMetricCombo; model: controller.smartQualityMetrics; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("smart_ab_crfs") }
            AppTextField { id: smartAbCrfsField; text: "18,23,28"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("smart_ab_duration") }
            AppSpinBox { id: smartAbDurationSpin; from: 1; to: 120; value: 8; onValueChanged: scheduleSettingsSync() }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox { id: smartReencodeCheck; text: I18n.t("smart_reencode_detection"); checked: true; onToggled: scheduleSettingsSync() }
            AppCheckBox { id: smartTwoPassCheck; text: I18n.t("smart_two_pass"); onToggled: scheduleSettingsSync() }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox { id: smartIntegrityCheck; text: I18n.t("smart_integrity_check"); onToggled: scheduleSettingsSync() }
            AppCheckBox { id: smartAbTestCheck; text: I18n.t("smart_ab_test"); onToggled: scheduleSettingsSync() }
        }
        Label {
            Layout.fillWidth: true
            text: I18n.t("smart_convert_hint")
            color: Theme.textMuted
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
    }

    Panel {
        id: corePanel
        objectName: "settingsPage_core"
        visible: settingsRoot.page === "core"
        iconName: "settings"
        iconTint: "#8E8E93"
        title: I18n.t("core")
        FieldLabel { text: I18n.t("operation") }
        AppComboBox { id: operationCombo; model: controller.operationOptions; onActivated: scheduleSettingsSync() }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("video") }
            AppComboBox { id: outVideoFmt; model: controller.videoFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("image") }
            AppComboBox { id: outImageFmt; model: controller.imageFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("audio") }
            AppComboBox { id: outAudioFmt; model: controller.audioFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle") }
            AppComboBox { id: outSubtitleFmt; model: controller.subtitleFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("text") }
            AppComboBox { id: outTextFmt; model: controller.textFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("codec") }
            AppComboBox { id: codecCombo; model: controller.codecOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("hw") }
            AppComboBox { id: hwCombo; model: controller.hwOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("performance_profile") }
            AppComboBox { id: performanceProfileCombo; model: controller.performanceProfiles; currentIndex: 1; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("target_size_mb"); helpText: I18n.t("target_size_hint") }
            AppTextField { id: targetSizeField; objectName: "targetSizeField"; placeholderText: "8 / 25 / 50"; invalid: controller.fieldError("target_size_mb").length > 0; errorText: controller.fieldError("target_size_mb"); onEditingFinished: scheduleSettingsSync() }
            Label {
                Layout.columnSpan: settingsRoot.compactFields ? 1 : 2
                Layout.fillWidth: true
                objectName: "targetSizeEstimateLabel"
                visible: targetSizeField.text.length > 0
                wrapMode: Text.WordWrap
                color: settingsRoot.targetEstimate.low_bitrate ? Theme.accentWarn : Theme.textSecondary
                text: settingsRoot.targetEstimate.video_kbps !== undefined
                    ? I18n.t("target_size_estimate").replace("{video}", settingsRoot.targetEstimate.video_kbps)
                        .replace("{audio}", settingsRoot.targetEstimate.audio_kbps)
                        .replace("{minimum}", settingsRoot.targetEstimate.minimum_mb)
                    : I18n.t("target_size_probe_hint")
            }
            SecondaryButton {
                Layout.columnSpan: settingsRoot.compactFields ? 1 : 2
                objectName: "targetSizeResizeButton"
                visible: targetSizeField.text.length > 0 && !!settingsRoot.targetEstimate.low_bitrate
                text: I18n.t("target_size_resize").replace("{width}", settingsRoot.targetEstimate.suggested_width)
                    .replace("{height}", settingsRoot.targetEstimate.suggested_height)
                onClicked: {
                    resizeWField.text = settingsRoot.targetEstimate.suggested_width
                    resizeHField.text = settingsRoot.targetEstimate.suggested_height
                    controller.setComboCanonical(portraitCombo, controller.portraitCanonicalOptions[0], controller.portraitCanonicalOptions)
                    scheduleSettingsSync()
                }
            }

            FieldLabel { text: I18n.t("cpu_load_limit"); helpText: I18n.t("settings_hint_limits") }
            AppSpinBox { id: cpuLimitSpin; from: 1; to: 100; value: 95; onValueModified: backend.autoTuneEnabled = false; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("gpu_load_limit"); helpText: I18n.t("settings_hint_limits") }
            AppSpinBox { id: gpuLimitSpin; from: 1; to: 100; value: 98; onValueModified: backend.autoTuneEnabled = false; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("disk_reserve"); helpText: I18n.t("settings_hint_disk_reserve") }
            AppSpinBox { id: diskSafetyMarginSpin; from: 0; to: 10240; value: 512; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: "CRF"; helpText: I18n.t("settings_hint_crf") }
            AppSpinBox { id: crfSpin; from: 0; to: 51; value: 23; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("preset") }
            AppComboBox { id: presetCombo; model: ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]; currentIndex: 5; onActivated: scheduleSettingsSync() }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox { id: overwriteCheck; text: I18n.t("overwrite"); onToggled: {
                controller.setComboText(collisionPolicyCombo, checked ? "overwrite" : "index")
                skipExistingCheck.checked = false
                scheduleSettingsSync()
            } }
            AppCheckBox { id: fastCopyCheck; text: I18n.t("fast_copy"); onToggled: scheduleSettingsSync() }
            AppCheckBox { id: skipExistingCheck; text: I18n.t("skip_existing"); onToggled: {
                controller.setComboText(collisionPolicyCombo, checked ? "skip" : "index")
                overwriteCheck.checked = false
                scheduleSettingsSync()
            } }
        }
    }

    Panel {
        id: outputPanel
        objectName: "settingsPage_output"
        visible: settingsRoot.page === "output"
        iconName: "folder"
        iconTint: "#007AFF"
        title: I18n.t("output")
        AppTextField { id: outputDirField; text: backend ? backend.outputDir : ""; placeholderText: I18n.t("output_folder_required"); invalid: controller.fieldError("output_dir").length > 0; errorText: controller.fieldError("output_dir"); onEditingFinished: { if (backend) backend.outputDir = text; scheduleSettingsSync() } }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton { iconName: "folder"; text: I18n.t("choose"); onClicked: backend && backend.pickOutputDir() }
            SecondaryButton { iconName: "folder"; text: I18n.t("open"); onClicked: backend && backend.openOutputDir() }
            SecondaryButton { iconName: "play"; text: I18n.t("preview"); onClicked: backend && backend.refreshOutputPreview(collectSettings()) }
            SecondaryButton { iconName: "copy"; text: I18n.t("copy_rename"); onClicked: backend && backend.copyRenamePreview(collectSettings()) }
            SecondaryButton { text: "CSV"; onClicked: backend && backend.exportRenamePreviewCsv(collectSettings()) }
        }
        FieldLabel { text: I18n.t("template") }
        AppTextField { id: outputTemplateField; text: "{stem}"; onEditingFinished: scheduleSettingsSync() }
        FieldLabel { text: "Політика колізій" }
        AppComboBox {
            id: collisionPolicyCombo
            model: ["index", "parent", "stop", "overwrite", "skip"]
            currentIndex: 0
            onActivated: {
                overwriteCheck.checked = currentText === "overwrite"
                skipExistingCheck.checked = currentText === "skip"
                scheduleSettingsSync()
            }
        }
        AppSwitch {
            id: commercialExportCheck
            text: I18n.t("watermark_free_commercial_export")
            onToggled: scheduleSettingsSync()
        }
        Label {
            Layout.fillWidth: true
            text: backend && backend.commercialExportAllowed ? I18n.t("commercial_export_licensed") : I18n.t("commercial_export_required")
            color: backend && backend.commercialExportAllowed ? Theme.statusSuccess : Theme.accentWarn
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
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

    ColumnLayout {
        id: advancedToolsSection
        Layout.fillWidth: true
        spacing: Theme.space5
        visible: ["core", "run", "output", "smart_convert"].indexOf(settingsRoot.page) < 0

    Panel {
        id: videoPanel
        objectName: "settingsPage_video"
        visible: settingsRoot.page === "video"
        iconName: "video"
        iconTint: "#AF52DE"
        title: I18n.t("video")
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("portrait") }
            AppComboBox { id: portraitCombo; model: controller.portraitOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
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
            AppComboBox { id: rotateCombo; model: controller.rotateOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("speed") }
            AppTextField { id: speedField; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("trim_start"); helpText: I18n.t("settings_hint_timecode") }
            AppTextField { id: trimStartField; placeholderText: "00:00:00"; invalid: controller.fieldError("trim_start").length > 0; errorText: controller.fieldError("trim_start"); onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("trim_end"); helpText: I18n.t("settings_hint_timecode") }
            AppTextField { id: trimEndField; placeholderText: "00:00:10"; invalid: controller.fieldError("trim_end").length > 0; errorText: controller.fieldError("trim_end"); onEditingFinished: scheduleSettingsSync() }
        }
        RowLayout {
            Layout.fillWidth: true
            AppCheckBox { id: mergeCheck; text: I18n.t("merge"); onToggled: scheduleSettingsSync() }
            AppTextField { id: mergeNameField; text: "merged"; onEditingFinished: scheduleSettingsSync() }
        }
    }

    Panel {
        id: videoEditorPanel
        objectName: "settingsPage_video_editor"
        visible: settingsRoot.page === "video_editor"
        iconName: "crop"
        iconTint: "#FF9500"
        title: I18n.t("video_editor")
        PrimaryButton {
            Layout.fillWidth: true
            text: I18n.t("nav_montage")
            iconName: "film"
            onClicked: controller.openMontageEditor(controller.selectedPath)
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox { id: editorDeinterlaceCheck; text: I18n.t("editor_deinterlace"); onToggled: scheduleSettingsSync() }
            AppCheckBox { id: editorStabilizeCheck; text: I18n.t("editor_stabilize"); onToggled: scheduleSettingsSync() }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("editor_denoise") }
            AppComboBox { id: editorDenoiseCombo; model: ["none", "hqdn3d", "nlmeans"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("brightness") }
            AppTextField { id: editorBrightnessField; placeholderText: "0.0"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("contrast") }
            AppTextField { id: editorContrastField; placeholderText: "1.0"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("saturation") }
            AppTextField { id: editorSaturationField; placeholderText: "1.0"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("gamma") }
            AppTextField { id: editorGammaField; placeholderText: "1.0"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("lut_path") }
            AppTextField { id: editorLutPathField; placeholderText: ".cube / .3dl"; onEditingFinished: scheduleSettingsSync() }
        }
    }

    Panel {
        id: audioSubtitlesPanel
        objectName: "settingsPage_audio_subtitles"
        visible: settingsRoot.page === "audio_subtitles"
        iconName: "audio"
        iconTint: "#FF2D55"
        title: I18n.t("audio_subtitles")
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("bitrate") }
            AppTextField { id: audioBitrateField; text: "192k"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("audio_codec") }
            AppComboBox { id: audioCodecCombo; model: controller.audioCodecOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
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
                SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickSubtitle() }
            }
            FieldLabel { text: I18n.t("subtitle_stream") }
            AppSpinBox { id: subtitleStreamSpin; from: 0; to: 32; value: 0; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("language_field") }
            AppTextField { id: subtitleLanguageField; text: "auto"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("model") }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                AppComboBox {
                    id: subtitleModelCombo
                    Layout.fillWidth: true
                    model: ["tiny", "base", "small", "medium", "large", "large-v3", "large-v3-turbo"]
                    currentIndex: 1
                    onActivated: scheduleSettingsSync()
                }
                SecondaryButton {
                    text: I18n.t("whisper.manage")
                    objectName: "openWhisperManager"
                    implicitHeight: 32
                    onClicked: whisperModal.open()
                }
            }
            FieldLabel { text: I18n.t("engine"); visible: backend ? backend.isWhisperAvailable : true }
            AppComboBox { id: subtitleEngineCombo; model: ["auto", "whisper", "faster-whisper"]; currentIndex: 0; visible: backend ? backend.isWhisperAvailable : true; enabled: visible; onActivated: scheduleSettingsSync() }
            Label {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                visible: backend ? !backend.isWhisperAvailable : false
                text: I18n.t("whisper_not_installed")
                color: Theme.accentWarn
                font.pixelSize: Theme.fontMeta
                wrapMode: Text.WordWrap
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox { id: trimSilenceCheck; text: I18n.t("trim_silence"); onToggled: scheduleSettingsSync() }
            AppCheckBox { id: splitChaptersCheck; text: I18n.t("split_chapters"); onToggled: scheduleSettingsSync() }
        }
        RowLayout {
            Layout.fillWidth: true
            AppTextField { id: replaceAudioPathField; placeholderText: I18n.t("replace_audio_path"); onEditingFinished: scheduleSettingsSync() }
            SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickAudioReplace() }
        }
        RowLayout {
            Layout.fillWidth: true
            AppTextField { id: coverArtField; placeholderText: I18n.t("cover_art"); onEditingFinished: scheduleSettingsSync() }
            SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickCoverArt() }
        }
    }

    Panel {
        id: subtitleToolsPanel
        objectName: "settingsPage_subtitle_tools"
        visible: settingsRoot.page === "subtitle_tools"
        iconName: "subtitle"
        iconTint: "#007AFF"
        title: I18n.t("subtitle_tools")
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("subtitle_sync_ms") }
            AppTextField { id: subtitleSyncField; placeholderText: "0"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle_font_name") }
            AppTextField { id: subtitleFontNameField; placeholderText: "Arial"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle_font_size") }
            AppSpinBox { id: subtitleFontSizeSpin; from: 6; to: 200; value: 24; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle_primary_color") }
            AppTextField { id: subtitlePrimaryColorField; text: "white"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle_outline") }
            AppSpinBox { id: subtitleOutlineSpin; from: 0; to: 20; value: 1; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle_shadow") }
            AppSpinBox { id: subtitleShadowSpin; from: 0; to: 20; value: 0; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("subtitle_alignment") }
            AppSpinBox { id: subtitleAlignmentSpin; from: 1; to: 9; value: 2; onValueChanged: scheduleSettingsSync() }
        }
        AppSwitch { id: subtitleStyleCheck; text: I18n.t("subtitle_style_enabled"); onToggled: scheduleSettingsSync() }
    }

    Panel {
        id: imagesSheetsPanel
        objectName: "settingsPage_images_sheets"
        visible: settingsRoot.page === "images_sheets"
        iconName: "image"
        iconTint: "#34C759"
        title: I18n.t("images_sheets")
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
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
        id: watermarkTextPanel
        objectName: "settingsPage_watermark_text"
        visible: settingsRoot.page === "watermark_text"
        iconName: "text"
        iconTint: "#5AC8FA"
        title: I18n.t("watermark_text")
        RowLayout {
            Layout.fillWidth: true
            AppTextField { id: wmPathField; placeholderText: I18n.t("watermark_image"); onEditingFinished: scheduleSettingsSync() }
            SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickWatermark() }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            FieldLabel { text: I18n.t("position") }
            AppComboBox { id: wmPosCombo; model: controller.positionOptions; currentIndex: 3; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("opacity") }
            AppSpinBox { id: wmOpacitySpin; from: 0; to: 100; value: 80; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("scale") }
            AppSpinBox { id: wmScaleSpin; from: 1; to: 100; value: 30; onValueChanged: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("text") }
            AppTextField { id: textWatermarkField; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("text_pos") }
            AppComboBox { id: textPosCombo; model: controller.positionOptions; currentIndex: 3; onActivated: scheduleSettingsSync() }
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
            SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickFont() }
        }
    }

    Panel {
        id: metadataHooksPanel
        objectName: "settingsPage_metadata_hooks"
        visible: settingsRoot.page === "metadata_hooks"
        iconName: "file"
        iconTint: "#8E8E93"
        title: I18n.t("metadata_hooks")
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
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
        id: privacySecurityPanel
        objectName: "settingsPage_privacy_security"
        visible: settingsRoot.page === "privacy_security"
        iconName: "lock"
        iconTint: "#007AFF"
        title: I18n.t("privacy_security")
        FieldLabel { text: I18n.t("blur_regions") }
        AppTextField { id: privacyBlurRegionsField; placeholderText: "x:y:w:h; x:y:w:h"; onEditingFinished: scheduleSettingsSync() }
        AppCheckBox {
            id: aiBlurCheck
            text: I18n.t("ai_blur_detection")
            onToggled: scheduleSettingsSync()
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("checksum_algorithm") }
            AppComboBox { id: checksumCombo; model: ["none", "md5", "sha256"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox { id: secureDeleteCheck; text: I18n.t("secure_delete_original"); onToggled: scheduleSettingsSync() }
            AppCheckBox { text: I18n.t("sanitize_metadata"); checked: stripMetadataCheck.checked; onToggled: { stripMetadataCheck.checked = checked; scheduleSettingsSync() } }
        }
        Label {
            Layout.fillWidth: true
            text: I18n.t("privacy_security_hint")
            color: Theme.accentWarn
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
    }

    Panel {
        id: cloudIntegrationPanel
        objectName: "settingsPage_cloud_integration"
        visible: settingsRoot.page === "cloud_integration"
        iconName: "cloud"
        iconTint: "#32ADE6"
        title: I18n.t("cloud_integration")
        AppSwitch { id: cloudUploadCheck; text: I18n.t("cloud_upload_enabled") + " (Pro)"; enabled: backend ? backend.proFeaturesEnabled : false; onToggled: scheduleSettingsSync() }
        Label {
            Layout.fillWidth: true
            text: backend && backend.proFeaturesEnabled ? I18n.t("cloud_pro_enabled") : I18n.t("cloud_pro_required")
            color: backend && backend.proFeaturesEnabled ? Theme.textMuted : Theme.accentWarn
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("cloud_provider") }
            AppComboBox { id: cloudProviderCombo; model: ["rclone", "Google Drive", "OneDrive", "Dropbox", "S3/MinIO", "FTP/SFTP"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("cloud_rclone_path") }
            AppTextField { id: cloudRclonePathField; text: "rclone"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: I18n.t("cloud_remote_path") }
            AppTextField { id: cloudRemotePathField; placeholderText: "remote:path"; onEditingFinished: scheduleSettingsSync() }
        }
        Label {
            Layout.fillWidth: true
            text: I18n.t("cloud_hint")
            color: Theme.textMuted
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
    }

    Panel {
        id: appUpdatePanel
        objectName: "settingsPage_app_update"
        visible: settingsRoot.page === "app_update"
        iconName: "refresh"
        iconTint: "#007AFF"
        title: I18n.t("app_update")

        Label {
            Layout.fillWidth: true
            text: I18n.t("app_update_hint")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeSm
            wrapMode: Text.Wrap
        }
        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: backend && backend.sourceUpdateChecking
            visible: running
        }
        Label {
            Layout.fillWidth: true
            text: backend ? backend.sourceUpdateStatus : ""
            color: backend && backend.sourceUpdateAvailable ? Theme.statusSuccess : Theme.textSecondary
            font.pixelSize: Theme.fontSizeSm
            wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            visible: backend && backend.sourceUpdateCurrentCommit.length > 0 && backend.sourceUpdateRemoteCommit.length > 0
            text: backend ? backend.sourceUpdateCurrentCommit.slice(0, 7) + " → " + backend.sourceUpdateRemoteCommit.slice(0, 7) : ""
            color: Theme.textDisabled
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton {
                iconName: "refresh"
                text: I18n.t("check_update")
                enabled: backend && !backend.sourceUpdateChecking
                onClicked: backend.checkSourceUpdate()
            }
            PrimaryButton {
                text: I18n.t("apply_update")
                visible: backend && backend.sourceUpdateAvailable
                enabled: backend && !backend.sourceUpdateChecking
                onClicked: backend.applySourceUpdate()
            }
            PrimaryButton {
                text: I18n.t("restart_app")
                visible: backend && backend.sourceUpdateRestartRequired
                onClicked: backend.restartAfterSourceUpdate()
            }
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: toolsLayout.implicitHeight + Theme.space3 * 2
            radius: Theme.radiusSm
            color: Theme.panelSecondary
            border.width: 1
            border.color: Theme.borderMuted

            ColumnLayout {
                id: toolsLayout
                anchors.fill: parent
                anchors.margins: Theme.space3
                spacing: Theme.space2
                Label { text: I18n.t("external_tools"); color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; font.weight: Font.DemiBold }
                GridLayout {
                    Layout.fillWidth: true
                    columns: settingsRoot.compactFields ? 1 : 2
                    rowSpacing: Theme.space2
                    columnSpacing: Theme.space3
                    FieldLabel { text: "FFmpeg" }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { Layout.fillWidth: true; text: backend && backend.ffmpegPath.length > 0 ? I18n.t("tool_ready") : I18n.t("tool_missing"); color: backend && backend.ffmpegPath.length > 0 ? Theme.statusSuccess : Theme.accentWarn; font.pixelSize: Theme.fontMeta }
                        SecondaryButton { text: I18n.t("configure"); implicitHeight: 28; onClicked: backend && backend.pickFfmpeg() }
                        SecondaryButton { iconName: "download"; text: I18n.t("install"); implicitHeight: 28; onClicked: backend && backend.updateFfmpeg() }
                    }
                    FieldLabel { text: "7-Zip" }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { Layout.fillWidth: true; text: backend && backend.archive && backend.archive.has7z ? I18n.t("tool_ready") : I18n.t("tool_missing"); color: backend && backend.archive && backend.archive.has7z ? Theme.statusSuccess : Theme.accentWarn; font.pixelSize: Theme.fontMeta }
                        SecondaryButton { text: I18n.t("configure"); implicitHeight: 28; onClicked: backend && backend.archive && backend.archive.pick7Zip() }
                        SecondaryButton { iconName: "download"; text: I18n.t("install"); implicitHeight: 28; onClicked: Qt.openUrlExternally("https://www.7-zip.org/") }
                    }
                    FieldLabel { text: "WinRAR CLI" }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { Layout.fillWidth: true; text: backend && backend.archive && backend.archive.hasRar ? I18n.t("tool_ready") : I18n.t("tool_missing"); color: backend && backend.archive && backend.archive.hasRar ? Theme.statusSuccess : Theme.accentWarn; font.pixelSize: Theme.fontMeta }
                        SecondaryButton { text: I18n.t("configure"); implicitHeight: 28; onClicked: backend && backend.archive && backend.archive.pickRar() }
                        SecondaryButton { iconName: "download"; text: I18n.t("install"); implicitHeight: 28; onClicked: Qt.openUrlExternally("https://www.rarlab.com/") }
                    }
                }
                Label { Layout.fillWidth: true; text: I18n.t("archive_tools_hint"); color: Theme.textMuted; font.pixelSize: Theme.fontMeta; wrapMode: Text.Wrap }
            }
        }
    }

    Panel {
        id: commercialLicensePanel
        objectName: "settingsPage_commercial_license"
        visible: settingsRoot.page === "commercial_license"
        iconName: "key"
        iconTint: "#FF9500"
        title: I18n.t("commercial_license")
        Label {
            Layout.fillWidth: true
            text: backend ? backend.licenseStatusText : ""
            color: backend && backend.licenseActive ? Theme.statusSuccess : backend && backend.trialActive ? Theme.accentWarn : Theme.textSecondary
            font.pixelSize: Theme.fontSizeSm
            wrapMode: Text.WordWrap
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("license_plan") }
            Label { Layout.fillWidth: true; text: backend ? backend.licensePlan : ""; color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
            FieldLabel { text: I18n.t("license_holder") }
            Label { Layout.fillWidth: true; text: backend ? backend.licenseHolder : ""; color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
            FieldLabel { text: I18n.t("license_expires") }
            Label { Layout.fillWidth: true; text: backend ? backend.licenseExpiresAt : ""; color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
            FieldLabel { text: I18n.t("trial") }
            Label { Layout.fillWidth: true; text: backend ? backend.trialRemainingText : ""; color: Theme.textSecondary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
            FieldLabel { text: I18n.t("commercial_export") }
            Label { Layout.fillWidth: true; text: backend && backend.commercialExportAllowed ? I18n.t("allowed") : I18n.t("license_required"); color: backend && backend.commercialExportAllowed ? Theme.statusSuccess : Theme.accentWarn; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
        }
        AppTextField {
            id: licenseKeyField
            placeholderText: I18n.t("license_key")
            echoMode: TextInput.Password
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton {
                iconName: "key"; text: I18n.t("activate_key")
                onClicked: backend && backend.activateLicenseKey(licenseKeyField.text)
            }
            SecondaryButton {
                text: I18n.t("offline_file")
                onClicked: backend && backend.loadOfflineLicenseFile()
            }
            SecondaryButton {
                iconName: "sparkles"; text: I18n.t("start_trial")
                enabled: backend ? !backend.licenseActive : false
                onClicked: backend && backend.startTrial()
            }
            SecondaryButton {
                iconName: "trash"; text: I18n.t("remove")
                enabled: backend ? backend.licenseActive : false
                onClicked: backend && backend.clearLicense()
            }
        }
        Label {
            Layout.fillWidth: true
            text: I18n.t("pro_features_hint")
            color: Theme.textMuted
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
        AppCheckBox {
            text: I18n.t("paid_auto_update")
            checked: backend ? backend.paidAutoUpdateEnabled : false
            enabled: backend ? backend.commercialExportAllowed : false
            onToggled: {
                if (backend)
                    backend.paidAutoUpdateEnabled = checked
            }
        }
        AppTextField {
            text: backend ? backend.paidUpdateManifestUrl : ""
            placeholderText: I18n.t("paid_update_manifest_url")
            onEditingFinished: {
                if (backend)
                    backend.paidUpdateManifestUrl = text
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton {
                iconName: "refresh"; text: I18n.t("check_update")
                enabled: backend ? backend.commercialExportAllowed : false
                onClicked: backend && backend.checkPaidUpdate()
            }
            SecondaryButton {
                text: I18n.t("open_update")
                enabled: backend ? backend.paidUpdateAvailable : false
                onClicked: backend && backend.openPaidUpdateDownload()
            }
        }
        Label {
            Layout.fillWidth: true
            text: backend ? backend.paidUpdateStatus : ""
            color: backend && backend.paidUpdateAvailable ? Theme.statusSuccess : Theme.textSecondary
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
    }

    Panel {
        id: selectedOverridePanel
        objectName: "settingsPage_selected_override"
        visible: settingsRoot.page === "selected_override"
        iconName: "sliders"
        iconTint: "#AF52DE"
        title: I18n.t("selected_override")
        AppTextField { id: overrideOutputTemplateField; placeholderText: I18n.t("output_template_override") }
        AppSpinBox { id: overrideCrfSpin; from: 0; to: 51; value: 23 }
        AppTextField { id: overrideAudioBitrateField; placeholderText: I18n.t("audio_bitrate_override") }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton {
                iconName: "save"; text: I18n.t("save")
                enabled: controller.selectedPath.length > 0
                onClicked: backend && backend.saveTaskOverrideByPath(controller.selectedPath, {
                    output_template: overrideOutputTemplateField.text,
                    crf: overrideCrfSpin.value,
                    audio_bitrate: overrideAudioBitrateField.text
                })
            }
            SecondaryButton {
                text: I18n.t("batch_override")
                enabled: controller.selectedPaths.length > 1
                onClicked: backend && backend.saveBulkOverride(controller.selectedPaths, {
                    output_template: overrideOutputTemplateField.text,
                    crf: overrideCrfSpin.value,
                    audio_bitrate: overrideAudioBitrateField.text
                })
            }
            SecondaryButton { iconName: "trash"; text: I18n.t("clear"); enabled: controller.selectedPath.length > 0; onClicked: backend && backend.clearTaskOverrideByPath(controller.selectedPath) }
        }
    }

    Panel {
        id: ffmpegWatchPanel
        objectName: "settingsPage_ffmpeg_watch"
        visible: settingsRoot.page === "ffmpeg_watch"
        iconName: "clock"
        iconTint: "#5856D6"
        title: I18n.t("ffmpeg_watch")
        AppTextField { id: ffmpegPathField; text: backend ? backend.ffmpegPath : ""; onEditingFinished: { if (backend) backend.ffmpegPath = text } }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton { iconName: "folder"; text: I18n.t("choose"); onClicked: backend && backend.pickFfmpeg() }
            SecondaryButton { iconName: "refresh"; text: I18n.t("refresh"); onClicked: backend && backend.refreshEncoders() }
            SecondaryButton { iconName: "download"; text: I18n.t("update_ffmpeg"); onClicked: backend && backend.updateFfmpeg() }
        }
        Label { Layout.fillWidth: true; text: backend ? backend.encoderInfo : ""; color: Theme.textMuted; wrapMode: Text.WordWrap; font.pixelSize: Theme.fontMeta }
        AppTextField { id: watchFolderField; text: backend ? backend.watchFolder : ""; placeholderText: I18n.t("watch_folder"); onEditingFinished: { if (backend) backend.watchFolder = text } }
        AppCheckBox {
            text: I18n.t("watch_auto_convert")
            checked: backend ? backend.watchAutoConvertEnabled : false
            onToggled: {
                if (backend)
                    backend.watchAutoConvertEnabled = checked
            }
        }
        FieldLabel { text: I18n.t("folder_rules") }
        AppTextArea {
            id: watchRulesArea
            Layout.preferredHeight: 92
            text: backend ? backend.watchRulesText : ""
            placeholderText: "Downloads -> mp4\nCamera -> h265\nAudio -> mp3"
            onActiveFocusChanged: {
                if (!activeFocus && backend)
                    backend.watchRulesText = text
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton {
                text: I18n.t("apply_rules")
                onClicked: {
                    if (backend)
                        backend.watchRulesText = watchRulesArea.text
                }
            }
            SecondaryButton {
                text: I18n.t("reset_rules")
                onClicked: {
                    if (backend) {
                        backend.resetWatchRules()
                        watchRulesArea.text = backend.watchRulesText
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            AppCheckBox {
                text: I18n.t("scheduler")
                checked: backend ? backend.schedulerEnabled : false
                onToggled: {
                    if (backend)
                        backend.schedulerEnabled = checked
                }
            }
            AppComboBox {
                Layout.preferredWidth: 150
                model: controller.schedulerModeOptions
                currentIndex: backend ? Math.max(0, find(backend.schedulerMode)) : 0
                onActivated: {
                    if (backend)
                        backend.schedulerMode = currentText
                }
            }
            AppTextField {
                Layout.preferredWidth: 92
                text: backend ? backend.schedulerTime : "23:00"
                placeholderText: "23:00"
                onEditingFinished: {
                    if (backend)
                        backend.schedulerTime = text
                }
            }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("scheduler_cpu") }
            AppSpinBox {
                from: 1
                to: 100
                value: backend ? backend.schedulerCpuLimit : 40
                onValueChanged: {
                    if (backend)
                        backend.schedulerCpuLimit = value
                }
            }
            FieldLabel { text: I18n.t("scheduler_gpu") }
            AppSpinBox {
                from: 1
                to: 100
                value: backend ? backend.schedulerGpuLimit : 30
                onValueChanged: {
                    if (backend)
                        backend.schedulerGpuLimit = value
                }
            }
            FieldLabel { text: I18n.t("after_completion") }
            AppComboBox {
                model: controller.completionActionOptions
                currentIndex: backend ? Math.max(0, find(backend.completionAction)) : 0
                onActivated: {
                    if (backend)
                        backend.completionAction = currentText
                }
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            AppCheckBox {
                id: trayEnabledCheck
                text: I18n.t("enable_tray")
                checked: backend ? backend.trayEnabled : false
                onToggled: {
                    if (backend)
                        backend.trayEnabled = checked
                }
            }
            AppCheckBox {
                id: pushNotificationsCheck
                text: I18n.t("push_notifications")
                checked: backend ? backend.pushNotificationsEnabled : true
                onToggled: {
                    if (backend)
                        backend.pushNotificationsEnabled = checked
                }
            }
        }
        AppCheckBox {
            text: I18n.t("webhook_channels")
            checked: backend ? backend.webhookEnabled : false
            onToggled: {
                if (backend)
                    backend.webhookEnabled = checked
            }
        }
        AppTextField {
            text: backend ? backend.webhookUrl : ""
            placeholderText: I18n.t("generic_webhook_url")
            onEditingFinished: {
                if (backend)
                    backend.webhookUrl = text
            }
        }
        AppTextField {
            text: backend ? backend.discordWebhookUrl : ""
            placeholderText: I18n.t("discord_webhook_url")
            onEditingFinished: {
                if (backend)
                    backend.discordWebhookUrl = text
            }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: settingsRoot.compactFields ? 1 : 2
            rowSpacing: 8
            columnSpacing: 8
            AppTextField {
                text: backend ? backend.telegramBotToken : ""
                placeholderText: I18n.t("telegram_bot_token")
                echoMode: TextInput.Password
                onEditingFinished: {
                    if (backend)
                        backend.telegramBotToken = text
                }
            }
            AppTextField {
                text: backend ? backend.telegramChatId : ""
                placeholderText: I18n.t("telegram_chat_id")
                onEditingFinished: {
                    if (backend)
                        backend.telegramChatId = text
                }
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton { iconName: "folder"; text: I18n.t("choose"); onClicked: backend && backend.pickWatchFolder() }
            SecondaryButton { text: backend && backend.watchRunning ? I18n.t("stop_watch") : I18n.t("start_watch"); onClicked: backend && (backend.watchRunning ? backend.stopWatching() : backend.startWatching()) }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.space2
            SecondaryButton { iconName: "download"; text: I18n.t("import"); onClicked: backend && backend.importProject() }
            SecondaryButton { iconName: "share"; text: I18n.t("export"); onClicked: backend && backend.exportProject(collectSettings()) }
        }
    }
    }
}
