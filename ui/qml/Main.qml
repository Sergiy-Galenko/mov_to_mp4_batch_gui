import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "components"

ApplicationWindow {
    id: root
    visible: true
    visibility: Window.Maximized
    minimumWidth: 760
    minimumHeight: 700
    title: I18n.t("app.title")
    color: Theme.bgBase

    palette.window: Theme.bgBase
    palette.base: Theme.input
    palette.text: Theme.textPrimary
    palette.button: Theme.bgSurface
    palette.buttonText: Theme.textPrimary
    palette.highlight: Theme.accentPrimary
    palette.highlightedText: Theme.textOnAccent

    property bool hasBackend: backend !== null
    property url appLogoSource: Qt.resolvedUrl("../../assets/app-logo.png")
    property bool sidebarCollapsed: false
    property bool compactMode: width < Theme.compactBreakpoint || (backend && backend.layoutMode === "compact")
    property int activeSection: 0
    property string globalSearchText: ""
    property var globalSearchResults: []
    property var toastHistory: []
    property bool logErrorsOnly: false
    property var validationResult: ({ ok: true, errors: {}, warnings: [], summary: "OK" })
    property bool formValid: true
    property string queueSearchText: ""
    property string queueStatusFilter: "all"
    property bool queueShowThumbnail: true
    property bool queueShowMetrics: true
    property bool queueShowActions: true
    property bool queueShowSize: true
    property bool queueShowDuration: true
    property bool queueShowCodec: true
    property bool queueShowOutput: true
    property bool queueShowProgress: true
    property real queueDropZoneHeight: 0
    property string toastText: ""
    property string activeWorkspaceMode: "all"
    property string selectedPath: ""
    property string selectedName: ""
    property string selectedMediaType: ""
    property string selectedThumbnailSource: ""
    property string selectedPreviewFormat: ""
    property int selectedIndex: -1
    property var selectedPaths: []
    property int lastSelectedIndex: -1
    property string selectedPreset: ""
    property real sharedShimmerPhase: 0
    property bool highLoadMode: backend ? backend.queueCount > 50 : false
    property int _langVersion: 0
    property string quickConvertPath: ""
    property string quickConvertName: ""
    property string quickConvertMediaType: "video"
    property string quickConvertFormat: ""
    property int activeNavIndex: 0
    property string pendingSettingsTarget: ""
    property bool advancedSettingsExpanded: false
    property var navigationItems: [
        { title: "queue", icon: "📁", page: 0, target: "" },
        { title: "analytics", icon: "📊", page: 1, target: "" },
        { title: "presets", icon: "🎛️", page: 2, target: "" },
        { title: "ffmpeg", icon: "🧰", page: 3, target: "" },
        { title: "downloads", icon: "⬇️", page: 4, target: "" },
        { title: "smart_convert", icon: "🧠", page: 5, target: "smart_convert" },
        { title: "device_profiles", icon: "📱", page: 5, target: "device_profiles" },
        { title: "video_editor", icon: "✂️", page: 5, target: "video_editor" },
        { title: "subtitle_tools", icon: "📝", page: 5, target: "subtitle_tools" },
        { title: "privacy_security", icon: "🔐", page: 5, target: "privacy_security" },
        { title: "cloud_integration", icon: "☁️", page: 5, target: "cloud_integration" },
        { title: "commercial_license", icon: "🔑", page: 5, target: "commercial_license" },
        { title: "run", icon: "🚀", page: 5, target: "run" },
        { title: "core", icon: "⚙️", page: 5, target: "core" },
        { title: "output", icon: "📤", page: 5, target: "output" },
        { title: "video", icon: "🎬", page: 5, target: "video" },
        { title: "audio_subtitles", icon: "🔊", page: 5, target: "audio_subtitles" },
        { title: "images_sheets", icon: "🖼️", page: 5, target: "images_sheets" },
        { title: "watermark_text", icon: "✍️", page: 5, target: "watermark_text" },
        { title: "metadata_hooks", icon: "🏷️", page: 5, target: "metadata_hooks" },
        { title: "selected_override", icon: "🧩", page: 5, target: "selected_override" },
        { title: "ffmpeg_watch", icon: "🛠️", page: 5, target: "ffmpeg_watch" }
    ]

    property var operationOptions: ["convert", "audio_only", "auto_subtitle", "subtitle_extract", "subtitle_burn", "thumbnail", "contact_sheet"]
    property var videoFormats: ["mp4", "mkv", "webm", "mov", "avi", "gif", "mpg", "m2ts"]
    property var imageFormats: ["jpg", "png", "webp", "bmp", "tiff"]
    property var audioFormats: ["mp3", "m4a", "aac", "wav", "flac", "opus"]
    property var subtitleFormats: ["srt", "ass", "vtt"]
    property var textFormats: ["txt", "md", "html", "json", "csv", "tsv", "rtf", "pdf", "docx", "doc", "odt", "xlsx", "xls", "ods", "pptx", "ppt", "odp"]
    property var codecOptions: ["auto", "H.264 (AVC)", "H.265 (HEVC)", "ProRes", "MPEG-2", "AV1", "VP9 (WebM)"]
    property var audioCodecOptions: ["auto", "aac", "ac3", "opus", "mp3", "copy"]
    property var smartContentTypes: ["auto", "live_action", "animation", "screencast"]
    property var smartQualityTargets: ["small", "balanced", "quality"]
    property var smartQualityMetrics: ["none", "ssim", "vmaf"]
    property var hwOptions: ["auto", "cpu", "NVIDIA (NVENC)", "Intel (QSV)", "AMD (AMF)"]
    property var performanceProfiles: ["Quality", "Balanced", "Fast", "Small file"]
    property var deviceProfiles: ["None", "iPhone 14/15/16", "iPad Pro", "Apple TV 4K HDR", "Android H.264 baseline", "Samsung TV", "PlayStation 5", "Xbox Series X", "Chromecast / Fire TV", "GoPro import", "DJI Drone import", "Steam Deck", "DVD compatible", "Blu-ray compatible"]
    property var rotateCanonicalOptions: ["0", "90° вправо", "90° вліво", "180°"]
    property var rotateOptions: ["0", I18n.t("rotate_right"), I18n.t("rotate_left"), "180°"]
    property var portraitCanonicalOptions: ["Вимкнено", "9:16 (1080x1920) - crop", "9:16 (1080x1920) - blur", "9:16 (720x1280) - crop", "9:16 (720x1280) - blur"]
    property var portraitOptions: [I18n.t("off"), "9:16 (1080x1920) - crop", "9:16 (1080x1920) - blur", "9:16 (720x1280) - crop", "9:16 (720x1280) - blur"]
    property var positionCanonicalOptions: ["Верх-ліворуч", "Верх-праворуч", "Низ-ліворуч", "Низ-праворуч", "Центр"]
    property var positionOptions: [I18n.t("pos_top_left"), I18n.t("pos_top_right"), I18n.t("pos_bottom_left"), I18n.t("pos_bottom_right"), I18n.t("pos_center")]

    property var schedulerModeOptions: ["time", "idle", "time_or_idle", "time_and_idle"]
    property var completionActionOptions: ["none", "open_output", "sleep", "shutdown"]

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
        if (!backend)
            return
        if (!backend.ensureOutputDirSelected())
            return
        if (!validateForm())
            return
        var settings = collectSettings()
        var preflight = backend.refreshPreflight(settings)
        if (!preflight.ok)
            return
        backend.startConversion(settings)
    }

    function outputFormatKeyFor(mediaType) {
        if (mediaType === "image") return "out_image_fmt"
        if (mediaType === "audio") return "out_audio_fmt"
        if (mediaType === "subtitle") return "out_subtitle_fmt"
        if (mediaType === "text") return "out_text_fmt"
        return "out_video_fmt"
    }

    function formatOptionsFor(mediaType) {
        if (mediaType === "image") return root.imageFormats
        if (mediaType === "audio") return root.audioFormats
        if (mediaType === "subtitle") return root.subtitleFormats
        if (mediaType === "text") return root.textFormats
        return root.videoFormats
    }

    function currentFormatFor(mediaType) {
        var options = formatOptionsFor(mediaType)
        var settings = collectSettings()
        var value = settings[outputFormatKeyFor(mediaType)]
        if (value && options.indexOf(value) >= 0)
            return value
        return options.length > 0 ? options[0] : ""
    }

    function quickOverrideMap(format) {
        var overrideMap = { operation: "convert" }
        overrideMap[outputFormatKeyFor(root.quickConvertMediaType)] = format
        return overrideMap
    }

    function quickSettingsMap(format) {
        var settings = collectSettings()
        settings.operation = "convert"
        settings[outputFormatKeyFor(root.quickConvertMediaType)] = format
        return settings
    }

    function workspaceMediaType() {
        if (root.activeWorkspaceMode === "photo") return "image"
        if (root.activeWorkspaceMode === "video") return "video"
        if (root.activeWorkspaceMode === "text") return "text"
        return "all"
    }

    function workspaceTitle() {
        if (root.activeWorkspaceMode === "photo") return I18n.t("workspace_photo")
        if (root.activeWorkspaceMode === "video") return I18n.t("workspace_video")
        if (root.activeWorkspaceMode === "text") return I18n.t("workspace_text")
        return I18n.t("queue")
    }

    function clearSelectionIfOutsideWorkspace() {
        var mediaType = workspaceMediaType()
        if (mediaType === "all" || root.selectedMediaType.length === 0 || root.selectedMediaType === mediaType)
            return
        root.selectedPath = ""
        root.selectedName = ""
        root.selectedMediaType = ""
        root.selectedThumbnailSource = ""
        root.selectedPreviewFormat = ""
        root.selectedPaths = []
        root.selectedIndex = -1
        if (backend)
            backend.selectQueueIndex(-1)
    }

    function addFilesForWorkspace() {
        if (!backend)
            return
        var mediaType = workspaceMediaType()
        if (mediaType === "all")
            backend.addFiles()
        else
            backend.addFilesForType(mediaType)
    }

    function addFolderForWorkspace() {
        if (!backend)
            return
        var mediaType = workspaceMediaType()
        if (mediaType === "all") {
            backend.addFolder()
            return
        }
        backend.folderTypeFilter = mediaType
        backend.addFolderFiltered()
    }

    function openSelectedSettings() {
        if (root.selectedMediaType === "image") {
            root.openSidebarSection(5, "images_sheets", root.navIndexFor(5, "images_sheets"))
        } else if (root.selectedMediaType === "video") {
            root.openSidebarSection(5, "video_editor", root.navIndexFor(5, "video_editor"))
        } else if (root.selectedMediaType === "text") {
            root.openSidebarSection(5, "core", root.navIndexFor(5, "core"))
        }
    }

    function saveSelectedFormat(format) {
        if (!backend || root.selectedPath.length === 0 || !format)
            return
        var overrideMap = { operation: "convert" }
        overrideMap[outputFormatKeyFor(root.selectedMediaType)] = format
        backend.updateTaskOverrideByPath(root.selectedPath, overrideMap)
        backend.refreshOutputPreview(collectSettings())
    }

    function convertSelectedFormat(format) {
        if (!backend || root.selectedPath.length === 0 || !format)
            return
        root.quickConvertPath = root.selectedPath
        root.quickConvertName = root.selectedName || root.selectedPath
        root.quickConvertMediaType = root.selectedMediaType || "video"
        root.quickConvertFormat = format
        root.convertQuickFile()
    }

    function openQuickConvert(path, name, mediaType, index) {
        root.quickConvertPath = path || ""
        root.quickConvertName = name || path || ""
        root.quickConvertMediaType = mediaType || "video"
        root.selectedPath = root.quickConvertPath
        root.selectedName = root.quickConvertName
        root.selectedMediaType = root.quickConvertMediaType
        root.selectedPreviewFormat = currentFormatFor(root.selectedMediaType)
        root.selectedIndex = index
        root.selectedPaths = root.quickConvertPath.length > 0 ? [root.quickConvertPath] : []
        root.lastSelectedIndex = index
        if (backend && root.quickConvertPath.length > 0)
            backend.selectQueuePath(root.quickConvertPath)

        var options = formatOptionsFor(root.quickConvertMediaType)
        var preferred = currentFormatFor(root.quickConvertMediaType)
        root.quickConvertFormat = options.indexOf(preferred) >= 0 ? preferred : (options.length > 0 ? options[0] : "")
        quickConvertPopup.open()
    }

    function saveQuickConvertOverride() {
        if (!backend || root.quickConvertPath.length === 0 || root.quickConvertFormat.length === 0)
            return
        backend.updateTaskOverrideByPath(root.quickConvertPath, quickOverrideMap(root.quickConvertFormat))
        backend.refreshOutputPreview(collectSettings())
    }

    function convertQuickFile() {
        if (!backend || root.quickConvertPath.length === 0 || root.quickConvertFormat.length === 0)
            return
        if (!backend.ensureOutputDirSelected())
            return
        var settings = quickSettingsMap(root.quickConvertFormat)
        backend.updateTaskOverrideByPath(root.quickConvertPath, quickOverrideMap(root.quickConvertFormat))
        backend.startConversionForPath(root.quickConvertPath, settings)
        quickConvertPopup.close()
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

    function setComboCanonical(combo, value, canonicalOptions) {
        if (!combo || value === undefined || value === null || !canonicalOptions)
            return
        var idx = canonicalOptions.indexOf(String(value))
        if (idx >= 0)
            combo.currentIndex = idx
        else
            root.setComboText(combo, value)
    }

    function canonicalOption(canonicalOptions, index, fallback) {
        if (canonicalOptions && index >= 0 && index < canonicalOptions.length)
            return canonicalOptions[index]
        return fallback
    }

    function applyPreset(preset) {
        if (settingsPanel)
            settingsPanel.applyPreset(preset)
    }

    function collectSettings() {
        return settingsPanel ? settingsPanel.collectSettings() : ({})
    }

    function isPathSelected(path) {
        return selectedPaths.indexOf(path) >= 0
    }

    function selectQueuePath(path, index, modifiers, name, mediaType, thumbnailSource) {
        var next = selectedPaths.slice()
        var ctrl = (modifiers & Qt.ControlModifier) !== 0
        var shift = (modifiers & Qt.ShiftModifier) !== 0
        if (shift && backend && lastSelectedIndex >= 0) {
            next = []
            var first = Math.min(lastSelectedIndex, index)
            var last = Math.max(lastSelectedIndex, index)
            for (var i = first; i <= last; ++i) {
                var rangePath = backend.queuePathAt(i)
                if (rangePath.length > 0)
                    next.push(rangePath)
            }
        } else if (ctrl) {
            var existing = next.indexOf(path)
            if (existing >= 0)
                next.splice(existing, 1)
            else
                next.push(path)
        } else {
            next = [path]
        }
        selectedPaths = next
        selectedPath = path
        selectedName = name || path
        selectedMediaType = mediaType || ""
        selectedThumbnailSource = thumbnailSource || ""
        selectedPreviewFormat = selectedMediaType.length > 0 ? currentFormatFor(selectedMediaType) : ""
        selectedIndex = index
        lastSelectedIndex = index
        if (backend)
            backend.selectQueuePath(path)
    }

    function navIndexFor(pageIndex, target) {
        for (var i = 0; i < navigationItems.length; ++i) {
            var item = navigationItems[i]
            if (item.page === pageIndex && String(item.target || "") === String(target || ""))
                return i
        }
        return -1
    }

    function openSidebarSection(pageIndex, target, navIndex) {
        root.activeSection = pageIndex
        var resolvedNav = navIndex >= 0 ? navIndex : navIndexFor(pageIndex, target)
        if (resolvedNav >= 0)
            root.activeNavIndex = resolvedNav
        if (pageIndex === 5) {
            root.pendingSettingsTarget = target || "run"
            root.advancedSettingsExpanded = ["run", "core", "output", ""].indexOf(root.pendingSettingsTarget) < 0
            settingsScrollTargetTimer.restart()
        }
    }

    function openTopMode(mode) {
        if (mode === "photo") {
            root.activeWorkspaceMode = "photo"
            root.clearSelectionIfOutsideWorkspace()
            openSidebarSection(0, "", 0)
        } else if (mode === "video") {
            root.activeWorkspaceMode = "video"
            root.clearSelectionIfOutsideWorkspace()
            openSidebarSection(0, "", 0)
        } else if (mode === "text") {
            root.activeWorkspaceMode = "text"
            root.clearSelectionIfOutsideWorkspace()
            openSidebarSection(0, "", 0)
        } else if (mode === "convert") {
            root.activeWorkspaceMode = "all"
            openSidebarSection(0, "", 0)
        } else if (mode === "montage")
            openSidebarSection(5, "video_editor", navIndexFor(5, "video_editor"))
        else if (mode === "downloads")
            openSidebarSection(4, "", navIndexFor(4, ""))
        else if (mode === "analytics")
            openSidebarSection(1, "", navIndexFor(1, ""))
    }

    function topModeActive(mode) {
        if (mode === "photo")
            return activeSection === 0 && root.activeWorkspaceMode === "photo"
        if (mode === "video")
            return activeSection === 0 && root.activeWorkspaceMode === "video"
        if (mode === "text")
            return activeSection === 0 && root.activeWorkspaceMode === "text"
        if (mode === "convert")
            return activeSection === 0 && root.activeWorkspaceMode === "all"
        if (mode === "montage")
            return activeSection === 5 && pendingSettingsTarget === "video_editor"
        if (mode === "downloads")
            return activeSection === 4
        if (mode === "analytics")
            return activeSection === 1
        return false
    }

    function themeModeIndex(mode) {
        if (mode === "light")
            return 1
        if (mode === "auto")
            return 2
        if (mode === "high_contrast")
            return 3
        return 0
    }

    function currentLanguageCode() {
        var code = backend ? (backend.currentLanguage || backend.uiLanguage) : I18n.language
        return I18n.normalize(code)
    }

    function languageButtonLabel(revision) {
        var code = currentLanguageCode()
        if (code === "uk")
            return "UA"
        return code.toUpperCase()
    }

    function languageActive(code) {
        return currentLanguageCode() === I18n.normalize(code)
    }

    function setAppLanguage(code) {
        var normalized = I18n.normalize(code)
        if (backend)
            backend.setLanguage(normalized)
        else
            I18n.setLanguage(normalized)
        root._langVersion += 1
    }

    function runGlobalSearch(text) {
        globalSearchText = String(text || "")
        globalSearchResults = backend ? backend.globalSearch(globalSearchText) : []
        if (globalSearchText.length >= 2)
            globalSearchPopup.open()
        else
            globalSearchPopup.close()
    }

    function activateSearchResult(result) {
        if (!result)
            return
        openSidebarSection(Number(result.page || 0), String(result.target || ""), -1)
        globalSearchPopup.close()
    }

    function queueItemMatches(name, path, mediaType, status) {
        var workspaceType = workspaceMediaType()
        if (workspaceType !== "all" && mediaType !== workspaceType)
            return false
        var needle = String(queueSearchText || "").trim().toLowerCase()
        if (needle.length > 0) {
            var haystack = [name, path, mediaType, status].join(" ").toLowerCase()
            if (haystack.indexOf(needle) < 0)
                return false
        }
        var filter = String(queueStatusFilter || "all")
        if (filter === "all")
            return true
        if (filter === "pending")
            return status === "queued" || status === "ready" || status === "analyzing"
        if (filter === "processing")
            return status === "running" || status === "paused"
        if (filter === "done")
            return status === "success"
        return status === filter
    }

    function showToast(message) {
        toastText = String(message || "")
        if (toastText.length > 0) {
            var next = toastHistory.slice()
            next.unshift({
                time: new Date().toLocaleTimeString(Qt.locale(), "hh:mm:ss"),
                message: toastText
            })
            toastHistory = next.slice(0, 30)
            toastTimer.restart()
        }
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

    Timer {
        id: settingsScrollTargetTimer
        interval: 40
        repeat: false
        onTriggered: {
            if (settingsPanel && settingsScroll && root.activeSection === 5)
                settingsScroll.contentItem.contentY = settingsPanel.sectionY(root.pendingSettingsTarget)
        }
    }

    Timer {
        id: toastTimer
        interval: 3600
        repeat: false
        onTriggered: root.toastText = ""
    }

    Connections {
        target: backend
        function onPresetLoaded(data) { applyPreset(data) }
        function onLanguageChanged() { root._langVersion += 1 }
        function onUiLanguageChanged() {
            I18n.setLanguage(backend.uiLanguage)
            root._langVersion += 1
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
        function onToastRequested(message) {
            root.showToast(message)
        }
        function onThemeChanged() {
            if (topThemeCombo)
                topThemeCombo.currentIndex = root.themeModeIndex(backend.themeMode)
        }
    }

    Component.onCompleted: {
        if (backend) {
            I18n.language = backend.uiLanguage
            backend.setupSystemTray()
            backend.restoreSession()
            backend.refreshEncoders()
            scheduleSettingsSync()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: topHeader
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: Theme.bgPrimary
            border.width: 0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space5
                anchors.rightMargin: Theme.space5
                spacing: Theme.space4

                Image {
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 38
                    source: root.appLogoSource
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    smooth: true
                }

                Label {
                    text: I18n.t("app.title")
                    color: Theme.textPrimary
                    font.family: Theme.displayFont
                    font.pixelSize: Theme.fontSizeLg
                    font.bold: true
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 24
                    color: Theme.borderSubtle
                }

                RowLayout {
                    spacing: 4
                    TopModeButton { mode: "convert"; text: I18n.t("convert") }
                    TopModeButton { mode: "photo"; text: I18n.t("workspace_photo") }
                    TopModeButton { mode: "video"; text: I18n.t("workspace_video") }
                    TopModeButton { mode: "text"; text: I18n.t("workspace_text") }
                    TopModeButton { mode: "montage"; text: I18n.t("workspace_montage") }
                    TopModeButton { mode: "downloads"; text: I18n.t("downloads") }
                    TopModeButton { mode: "analytics"; text: I18n.t("analytics") }
                }

                Item { Layout.fillWidth: true }

                RowLayout {
                    spacing: Theme.space3

                    StatusPill { 
                        visible: root.width > 900
                        text: backend && backend.isRunning ? "⏳ " + I18n.t("live") : "✅ " + I18n.t("idle")
                        accent: backend && backend.isRunning ? Theme.statusRunning : Theme.statusSuccess 
                    }

                    AppTextField {
                        id: globalSearchField
                        Layout.preferredWidth: 200
                        placeholderText: I18n.t("global_search")
                        text: root.globalSearchText
                        onTextChanged: root.runGlobalSearch(text)
                        Keys.onReturnPressed: {
                            if (root.globalSearchResults.length > 0)
                                root.activateSearchResult(root.globalSearchResults[0])
                        }
                    }
                    
                    SecondaryButton {
                        Layout.preferredWidth: 50
                        text: "🔔 " + root.toastHistory.length
                        onClicked: notificationCenterPopup.open()
                    }

                    GhostButton {
                        id: languageButton
                        Layout.preferredWidth: 68
                        text: "🌐 " + root.languageButtonLabel(root._langVersion)
                        onClicked: languagePopup.open()

                        Popup {
                            id: languagePopup
                            y: languageButton.height + 6
                            width: 196
                            padding: 8
                            focus: true
                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                            background: Rectangle {
                                radius: Theme.radiusInput + 2
                                color: Theme.panelAlt
                                border.width: 1
                                border.color: Theme.borderStrong
                            }

                            contentItem: ColumnLayout {
                                spacing: 4

                                Repeater {
                                    model: backend ? backend.availableLanguages : []

                                    delegate: Button {
                                        id: languageOptionButton
                                        Layout.fillWidth: true
                                        implicitHeight: 38
                                        text: modelData.label || ""
                                        hoverEnabled: true
                                        onClicked: {
                                            root.setAppLanguage(modelData.code)
                                            languagePopup.close()
                                        }

                                        background: Rectangle {
                                            radius: Theme.radiusSm
                                            color: root.languageActive(modelData.code)
                                                   ? Theme.accentSoft
                                                   : languageOptionButton.hovered ? Theme.overlayHover : Theme.transparent
                                            border.width: root.languageActive(modelData.code) ? 1 : 0
                                            border.color: Theme.accentPrimary
                                        }

                                        contentItem: RowLayout {
                                            spacing: 8

                                            Label {
                                                Layout.fillWidth: true
                                                text: modelData.label || ""
                                                color: Theme.textPrimary
                                                font.pixelSize: Theme.fontSizeSm
                                                elide: Text.ElideRight
                                            }

                                            Label {
                                                visible: root.languageActive(modelData.code)
                                                text: "✓"
                                                color: Theme.accentPrimary
                                                font.pixelSize: Theme.fontSizeSm
                                                font.bold: true
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    GhostButton {
                        Layout.preferredWidth: 44
                        text: "📖"
                        onClicked: tutorialPopup.open()
                    }

                    GhostButton {
                        Layout.preferredWidth: 44
                        text: "🌓"
                        onClicked: {
                            if (backend) backend.themeMode = backend.themeMode === "light" ? "dark" : "light"
                        }
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderSubtle }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            SidebarPanel {
                Layout.fillHeight: true
                visible: root.activeSection !== 0 // Only visible in advanced sections
                collapsed: root.sidebarCollapsed
                activeIndex: root.activeNavIndex
                navigationItems: root.navigationItems
                onSectionRequested: function(pageIndex, target, navIndex) { root.openSidebarSection(pageIndex, target, navIndex) }
                onAddFilesRequested: backend && backend.addFiles()
                onAddFolderRequested: backend && backend.addFolder()
                onDedupeRequested: backend && backend.deduplicateQueueByHash()
            }

            Rectangle { 
                visible: root.activeSection !== 0
                Layout.preferredWidth: 1; 
                Layout.fillHeight: true; 
                color: Theme.borderSubtle 
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: root.activeSection

                QueueScreen {}
                AnalyticsScreen {}
                PresetsScreen {}
                FfmpegScreen {}
                YoutubeScreen {}
                ScrollView {
                    id: settingsScroll
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: settingsScroll.availableWidth
                        spacing: Theme.space3
                        anchors.margins: Theme.space3

                        SettingsPanel {
                            id: settingsPanel
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 88
            color: Theme.bgElevated
            border.width: 1
            border.color: Theme.borderSubtle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space5
                anchors.rightMargin: Theme.space5
                spacing: Theme.space5

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        
                        Label {
                            text: backend ? backend.totalProgressText : "--"
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeMd
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        
                        Label {
                            text: "ETA: " + (backend ? backend.sessionEtaText : "--:--")
                            color: Theme.textSecondary
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontSizeSm
                        }
                    }

                    ShimmerBar {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 8
                        value: backend ? backend.totalProgress : 0
                        active: backend ? backend.isRunning : false
                        highLoadMode: root.highLoadMode
                        shimmerPhase: root.sharedShimmerPhase
                        fillColor: Theme.accentPrimary
                    }
                }

                RowLayout {
                    Layout.preferredWidth: 280
                    spacing: 12
                    
                    SecondaryButton {
                        Layout.preferredWidth: 44
                            text: "📁"
                        onClicked: backend && backend.pickOutputDir()
                    }
                    
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label {
                            text: I18n.t("output_folder")
                            color: Theme.textDisabled
                            font.pixelSize: 11
                        }
                        Label {
                            Layout.fillWidth: true
                            text: backend && backend.outputDirConfigured ? backend.outputDir : I18n.t("output_folder_required")
                            color: backend && backend.outputDirConfigured ? Theme.textSecondary : Theme.statusWarning
                            font.pixelSize: Theme.fontSizeSm
                            elide: Text.ElideMiddle
                        }
                    }
                }

                RowLayout {
                    spacing: 8
                    
                    SecondaryButton {
                        Layout.preferredWidth: 48
                        text: backend && backend.isPaused ? "▶️" : "⏸️"
                        enabled: backend && backend.isRunning
                        onClicked: backend && (backend.isPaused ? backend.resumeConversion() : backend.pauseConversion())
                    }
                    
                    SecondaryButton {
                        Layout.preferredWidth: 48
                        text: "⏹️"
                        enabled: backend && backend.isRunning
                        onClicked: backend && backend.stopConversion()
                    }
                    
                    PrimaryButton {
                        Layout.preferredWidth: 160
                        Layout.preferredHeight: 48
                        text: "🚀 " + (backend && backend.isRunning ? I18n.t("running") : I18n.t("start"))
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                        enabled: backend ? (backend.queueCount > 0 && !backend.isRunning && formValid) : false
                        onClicked: root.startIfValid()
                    }
                }
            }
        }
    }

    Rectangle {
        z: 1000
        visible: root.toastText.length > 0
        opacity: visible ? 1 : 0
        width: Math.min(root.width - 48, toastLabel.implicitWidth + 32)
        height: Math.max(42, toastLabel.implicitHeight + 18)
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 18
        anchors.bottomMargin: 18
        radius: Theme.radiusMd
        color: Theme.bgElevated
        border.width: 1
        border.color: Theme.accent

        Label {
            id: toastLabel
            anchors.fill: parent
            anchors.margins: 10
            text: root.toastText
            color: Theme.textPrimary
            font.pixelSize: Theme.fontSmall
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    Popup {
        id: globalSearchPopup
        z: 1100
        modal: false
        focus: true
        width: 520
        height: Math.min(420, searchResultsList.contentHeight + 24)
        x: Math.max(12, Math.min(root.width - width - 12, globalSearchField.mapToItem(root, 0, 0).x))
        y: globalSearchField.mapToItem(root, 0, globalSearchField.height + 8).y
        padding: 8
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusPanel
            color: Theme.bgElevated
            border.width: 1
            border.color: Theme.borderStrong
        }

        contentItem: ListView {
            id: searchResultsList
            clip: true
            model: root.globalSearchResults
            spacing: 4
            delegate: ItemDelegate {
                width: searchResultsList.width
                height: 54
                onClicked: root.activateSearchResult(modelData)
                background: Rectangle {
                    radius: Theme.radiusSm
                    color: parent.hovered ? Theme.overlayHover : Theme.transparent
                }
                contentItem: ColumnLayout {
                    spacing: 2
                    Label {
                        Layout.fillWidth: true
                        text: modelData.kind + " · " + modelData.title
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeSm
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: modelData.detail
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontMeta
                        elide: Text.ElideMiddle
                    }
                }
            }
        }
    }

    Popup {
        id: notificationCenterPopup
        z: 1100
        modal: false
        focus: true
        width: 420
        height: 420
        x: root.width - width - 18
        y: topHeader.height + 10
        padding: 12
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusPanel
            color: Theme.bgElevated
            border.width: 1
            border.color: Theme.borderStrong
        }

        contentItem: ColumnLayout {
            spacing: Theme.space2
            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: I18n.t("notifications")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeLg
                    font.bold: true
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    Layout.preferredWidth: 86
                    text: I18n.t("clear")
                    enabled: root.toastHistory.length > 0
                    onClicked: root.toastHistory = []
                }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.toastHistory
                spacing: 6
                delegate: Rectangle {
                    width: ListView.view.width
                    height: Math.max(48, messageLabel.implicitHeight + 18)
                    radius: Theme.radiusSm
                    color: Theme.bgSecondary
                    border.width: 1
                    border.color: Theme.borderSubtle
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 2
                        Label {
                            text: modelData.time
                            color: Theme.textDisabled
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontMeta
                        }
                        Label {
                            id: messageLabel
                            Layout.fillWidth: true
                            text: modelData.message
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeSm
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: quickConvertPopup
        modal: true
        focus: true
        width: Math.min(root.width - 48, 560)
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - implicitHeight) / 2)
        padding: 16
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        onOpened: {
            var options = root.formatOptionsFor(root.quickConvertMediaType)
            quickFormatCombo.currentIndex = options.length > 0 ? Math.max(0, options.indexOf(root.quickConvertFormat)) : -1
        }

        background: Rectangle {
            radius: Theme.radiusMd
            color: Theme.bgSecondary
            border.width: 1
            border.color: Theme.accent
        }

        contentItem: ColumnLayout {
            width: quickConvertPopup.width - quickConvertPopup.leftPadding - quickConvertPopup.rightPadding
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: I18n.t("quick_convert")
                color: Theme.textPrimary
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontHeading
                font.bold: true
                elide: Text.ElideRight
            }

            Label {
                Layout.fillWidth: true
                text: I18n.t("quick_convert_hint")
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSmall
                wrapMode: Text.WordWrap
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.borderSubtle
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 10

                FieldLabel { text: I18n.t("selected_file") }
                Label {
                    Layout.fillWidth: true
                    text: root.quickConvertName
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSmall
                    elide: Text.ElideMiddle
                }

                FieldLabel { text: I18n.t("media_type") }
                Label {
                    Layout.fillWidth: true
                    text: (root.quickConvertMediaType || "media").toUpperCase()
                    color: Theme.textSecondary
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontMeta
                    elide: Text.ElideRight
                }

                FieldLabel { text: I18n.t("output_format") }
                AppComboBox {
                    id: quickFormatCombo
                    model: root.formatOptionsFor(root.quickConvertMediaType)
                    onActivated: root.quickConvertFormat = currentText
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                SecondaryButton {
                    text: I18n.t("cancel")
                    onClicked: quickConvertPopup.close()
                }
                SecondaryButton {
                    text: I18n.t("save_format")
                    enabled: root.quickConvertPath.length > 0 && quickFormatCombo.currentText.length > 0
                    onClicked: {
                        root.quickConvertFormat = quickFormatCombo.currentText
                        root.saveQuickConvertOverride()
                        quickConvertPopup.close()
                    }
                }
                PrimaryButton {
                    text: I18n.t("convert_this_file")
                    enabled: backend ? (!backend.isRunning && root.quickConvertPath.length > 0 && quickFormatCombo.currentText.length > 0) : false
                    onClicked: {
                        root.quickConvertFormat = quickFormatCombo.currentText
                        root.convertQuickFile()
                    }
                }
            }
        }
    }

    component QueueScreen: ScrollView {
        id: queueScreen
        clip: true

        ColumnLayout {
            width: queueScreen.availableWidth
            spacing: 12
            anchors.margins: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Label {
                    Layout.fillWidth: true
                    text: root.workspaceTitle()
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
                Label {
                    visible: root.selectedPaths.length > 1
                    text: I18n.t("selected") + ": " + root.selectedPaths.length
                    color: Theme.accentPrimary
                    font.family: Theme.monoFont
                    font.pixelSize: Theme.fontMeta
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    text: I18n.t("move_top")
                    visible: root.selectedPaths.length > 1
                    onClicked: backend && backend.moveSelectedPathsTop(root.selectedPaths)
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    text: I18n.t("move_up")
                    visible: root.selectedPaths.length > 1
                    onClicked: backend && backend.moveSelectedPathsUp(root.selectedPaths)
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    text: I18n.t("move_down")
                    visible: root.selectedPaths.length > 1
                    onClicked: backend && backend.moveSelectedPathsDown(root.selectedPaths)
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    text: I18n.t("move_bottom")
                    visible: root.selectedPaths.length > 1
                    onClicked: backend && backend.moveSelectedPathsBottom(root.selectedPaths)
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    text: I18n.t("batch_remove")
                    visible: root.selectedPaths.length > 1
                    onClicked: {
                        if (backend)
                            backend.removeSelectedPaths(root.selectedPaths)
                        root.selectedPaths = []
                        root.selectedPath = ""
                        root.selectedName = ""
                        root.selectedMediaType = ""
                        root.selectedThumbnailSource = ""
                        root.selectedPreviewFormat = ""
                        root.selectedIndex = -1
                    }
                }
                SecondaryButton {
                    Layout.fillWidth: false
                    text: I18n.t("batch_override")
                    visible: root.selectedPaths.length > 1
                    onClicked: root.openSidebarSection(5, "selected_override", -1)
                }
                SecondaryButton { Layout.fillWidth: false; text: I18n.t("add"); onClicked: root.addFilesForWorkspace() }
                SecondaryButton { Layout.fillWidth: false; text: I18n.t("folder"); onClicked: root.addFolderForWorkspace() }
                SecondaryButton {
                    Layout.fillWidth: false
                    Layout.preferredWidth: 132
                    text: I18n.t("convert_all")
                    enabled: backend ? (backend.queueCount > 0 && !backend.isRunning) : false
                    onClicked: root.startIfValid()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: backend && !backend.outputDirConfigured ? 56 : 0
                visible: backend ? !backend.outputDirConfigured : false
                radius: Theme.radiusPanel
                color: Theme.warningSoft
                border.width: 1
                border.color: Theme.accentWarn
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10
                    Label {
                        Layout.fillWidth: true
                        text: I18n.t("output_folder_required_detail")
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSmall
                        wrapMode: Text.WordWrap
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: I18n.t("choose_output_folder")
                        onClicked: backend && backend.ensureOutputDirSelected()
                    }
                }
            }

            Panel {
                title: "1-2-3"
                GridLayout {
                    Layout.fillWidth: true
                    columns: root.compactMode ? 1 : 3
                    rowSpacing: 8
                    columnSpacing: 8
                    SecondaryButton {
                        Layout.fillWidth: true
                        text: "1. " + I18n.t("add_files")
                        onClicked: root.addFilesForWorkspace()
                    }
                    AppComboBox {
                        id: wizardFormatCombo
                        Layout.fillWidth: true
                        model: root.formatOptionsFor(root.workspaceMediaType() === "all" ? "video" : root.workspaceMediaType())
                        onActivated: {
                            if (settingsPanel)
                                settingsPanel.setOutputFormatFor(root.workspaceMediaType() === "all" ? "video" : root.workspaceMediaType(), currentText)
                        }
                    }
                    PrimaryButton {
                        Layout.fillWidth: true
                        text: "3. " + I18n.t("start")
                        enabled: backend ? (backend.queueCount > 0 && !backend.isRunning) : false
                        onClicked: {
                            if (settingsPanel)
                                settingsPanel.setOutputFormatFor(root.workspaceMediaType() === "all" ? "video" : root.workspaceMediaType(), wizardFormatCombo.currentText)
                            root.startIfValid()
                        }
                    }
                }
            }

            Panel {
                title: I18n.t("queue_tools")
                RowLayout {
                    Layout.fillWidth: true
                    AppTextField {
                        id: queueSearchField
                        placeholderText: I18n.t("queue_search")
                        text: root.queueSearchText
                        onTextChanged: root.queueSearchText = text
                    }
                    AppComboBox {
                        id: queueStatusFilterCombo
                        Layout.preferredWidth: 150
                        model: ["all", "pending", "processing", "done", "failed", "skipped", "cancelled"]
                        onActivated: root.queueStatusFilter = currentText
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: I18n.t("errors_only")
                        enabled: backend ? backend.failedCount > 0 : false
                        onClicked: {
                            root.queueStatusFilter = "failed"
                            queueStatusFilterCombo.currentIndex = 4
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    AppCheckBox { text: I18n.t("show_thumbnail"); checked: root.queueShowThumbnail; onToggled: root.queueShowThumbnail = checked }
                    AppCheckBox { text: I18n.t("queue_show_size"); checked: root.queueShowSize; onToggled: root.queueShowSize = checked }
                    AppCheckBox { text: I18n.t("queue_show_duration"); checked: root.queueShowDuration; onToggled: root.queueShowDuration = checked }
                    AppCheckBox { text: I18n.t("queue_show_codec"); checked: root.queueShowCodec; onToggled: root.queueShowCodec = checked }
                    AppCheckBox { text: I18n.t("queue_show_output"); checked: root.queueShowOutput; onToggled: root.queueShowOutput = checked }
                }
                RowLayout {
                    Layout.fillWidth: true
                    AppCheckBox { text: I18n.t("queue_show_progress"); checked: root.queueShowProgress; onToggled: root.queueShowProgress = checked }
                    AppCheckBox { text: I18n.t("show_metrics"); checked: root.queueShowMetrics; onToggled: root.queueShowMetrics = checked }
                    AppCheckBox { text: I18n.t("show_actions"); checked: root.queueShowActions; onToggled: root.queueShowActions = checked }
                    Item { Layout.fillWidth: true }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: "🛡️ " + I18n.t("preflight")
                        onClicked: backend && backend.refreshPreflight(collectSettings())
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: "📌 " + I18n.t("priority")
                        onClicked: backend && backend.sortQueueByPriority()
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: I18n.t("retry")
                        visible: backend ? backend.failedCount > 0 : false
                        onClicked: backend && backend.retryFailed()
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: "🧹 " + I18n.t("cleanup_done")
                        enabled: backend ? backend.queueCount > 0 : false
                        onClicked: backend && backend.cleanupQueue("done")
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: "🧹 " + I18n.t("cleanup_failed")
                        enabled: backend ? backend.queueCount > 0 : false
                        onClicked: backend && backend.cleanupQueue("failed")
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: "🧹 " + I18n.t("cleanup_missing")
                        enabled: backend ? backend.queueCount > 0 : false
                        onClicked: backend && backend.cleanupQueue("missing")
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: "📊 " + I18n.t("refresh_preview")
                        enabled: backend ? backend.queueCount > 0 : false
                        onClicked: backend && backend.refreshOutputPreview(collectSettings())
                    }
                    Item { Layout.fillWidth: true }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: backend && backend.failedCount > 0 ? 34 : 0
                    visible: backend ? backend.failedCount > 0 : false
                    radius: Theme.radiusButton
                    color: Theme.dangerSoft
                    border.width: 1
                    border.color: Theme.accentError
                    Label {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: Text.AlignVCenter
                        text: I18n.t("failed_items") + ": " + (backend ? backend.failedCount : 0)
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontMeta
                        elide: Text.ElideRight
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: backend && backend.hasLastError ? 92 : 0
                    visible: backend ? backend.hasLastError : false
                    radius: Theme.radiusPanel
                    color: Theme.dangerSoft
                    border.width: 1
                    border.color: Theme.accentError
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Label {
                                Layout.fillWidth: true
                                text: backend ? backend.lastErrorTitle : ""
                                color: Theme.textPrimary
                                font.pixelSize: Theme.fontSizeSm
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            Label {
                                Layout.fillWidth: true
                                text: backend ? I18n.t("reason") + ": " + backend.lastErrorDetails : ""
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontSizeSm
                                maximumLineCount: 2
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                            }
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 142
                            text: I18n.t("copy_log")
                            onClicked: backend && backend.copyLastErrorLog()
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 76
                            text: I18n.t("clear")
                            onClicked: backend && backend.clearLastError()
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Panel {
                    title: "🛡️ " + I18n.t("preflight")
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: backend ? backend.preflightSummary : ""
                            color: backend && backend.preflightOk ? Theme.statusSuccess : Theme.accentError
                            font.pixelSize: Theme.fontSizeSm
                            wrapMode: Text.WordWrap
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 110
                            text: I18n.t("check")
                            onClicked: backend && backend.refreshPreflight(collectSettings())
                        }
                    }
                    Repeater {
                        model: backend ? backend.preflightErrors : []
                        delegate: Label {
                            Layout.fillWidth: true
                            text: "❌ " + modelData
                            color: Theme.accentError
                            font.pixelSize: Theme.fontMeta
                            wrapMode: Text.WordWrap
                        }
                    }
                    Repeater {
                        model: backend ? backend.preflightWarnings : []
                        delegate: Label {
                            Layout.fillWidth: true
                            text: "⚠️ " + modelData
                            color: Theme.accentWarn
                            font.pixelSize: Theme.fontMeta
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Panel {
                    title: "📊 " + I18n.t("output_preview")
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Label {
                        Layout.fillWidth: true
                        text: backend ? backend.outputPreviewText : ""
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeSm
                        wrapMode: Text.WordWrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: backend ? I18n.t("output") + ": " + backend.selectedPreviewOutput : ""
                        color: Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                        elide: Text.ElideMiddle
                    }
                    Label {
                        Layout.fillWidth: true
                        text: backend ? "FFmpeg: " + backend.selectedPreviewCommand : ""
                        color: Theme.textDisabled
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                        maximumLineCount: 2
                        wrapMode: Text.WrapAnywhere
                        elide: Text.ElideRight
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        SecondaryButton {
                            Layout.fillWidth: false
                            text: "📋 " + I18n.t("copy_command")
                            onClicked: backend && backend.copyDryRunCommand(collectSettings())
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            text: "📄 Script"
                            onClicked: backend && backend.exportCommandScript(collectSettings())
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            Panel {
                id: selectedPreviewPanel
                visible: root.selectedPath.length > 0 && ["image", "video", "text"].indexOf(root.selectedMediaType) >= 0
                title: root.selectedMediaType === "image" ? I18n.t("photo_preview")
                     : root.selectedMediaType === "video" ? I18n.t("video_preview")
                     : I18n.t("text_preview")

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: Math.min(520, Math.max(320, queueScreen.availableWidth * 0.44))
                        Layout.preferredHeight: 300
                        radius: Theme.radiusPanel
                        color: Theme.input
                        border.width: 1
                        border.color: Theme.borderSubtle
                        clip: true

                        Image {
                            anchors.fill: parent
                            anchors.margins: 10
                            source: (root.selectedMediaType === "image" || root.selectedMediaType === "video") ? root.selectedThumbnailSource : ""
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            visible: source.toString().length > 0
                        }

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 10
                            visible: root.selectedMediaType === "text"
                            clip: true
                            Label {
                                width: selectedPreviewPanel.width > 0 ? Math.max(280, selectedPreviewPanel.width * 0.38) : 360
                                text: backend ? backend.readTextPreview(root.selectedPath) : ""
                                color: Theme.textPrimary
                                font.family: Theme.monoFont
                                font.pixelSize: Theme.fontMeta
                                wrapMode: Text.WrapAnywhere
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            width: parent.width - 28
                            visible: root.selectedMediaType !== "text" && root.selectedThumbnailSource.length === 0
                            text: root.selectedMediaType === "video" ? I18n.t("preview_frame_pending") : I18n.t("preview_unavailable")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSmall
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Label {
                            Layout.fillWidth: true
                            text: root.selectedName || root.selectedPath
                            color: Theme.textPrimary
                            font.pixelSize: Theme.fontSizeLg
                            font.bold: true
                            elide: Text.ElideMiddle
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.selectedPath
                            color: Theme.textSecondary
                            font.family: Theme.monoFont
                            font.pixelSize: Theme.fontMeta
                            elide: Text.ElideMiddle
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: 8
                            columnSpacing: 8

                            FieldLabel { text: I18n.t("media_type") }
                            Label {
                                Layout.fillWidth: true
                                text: root.selectedMediaType.toUpperCase()
                                color: Theme.textSecondary
                                font.family: Theme.monoFont
                                font.pixelSize: Theme.fontMeta
                            }

                            FieldLabel { text: I18n.t("output_format") }
                            AppComboBox {
                                id: selectedPreviewFormatCombo
                                Layout.fillWidth: true
                                model: root.formatOptionsFor(root.selectedMediaType)
                                currentIndex: Math.max(0, find(root.selectedPreviewFormat))
                                onActivated: root.selectedPreviewFormat = currentText
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            SecondaryButton {
                                text: I18n.t("save_format")
                                enabled: root.selectedPath.length > 0 && selectedPreviewFormatCombo.currentText.length > 0
                                onClicked: root.saveSelectedFormat(selectedPreviewFormatCombo.currentText)
                            }
                            PrimaryButton {
                                text: I18n.t("convert_this_file")
                                enabled: backend ? (!backend.isRunning && root.selectedPath.length > 0 && selectedPreviewFormatCombo.currentText.length > 0) : false
                                onClicked: root.convertSelectedFormat(selectedPreviewFormatCombo.currentText)
                            }
                            SecondaryButton {
                                text: I18n.t("change")
                                onClicked: root.openSelectedSettings()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root.selectedMediaType === "image"
                            spacing: 8
                            SecondaryButton { text: I18n.t("photo_quality"); onClicked: root.openSidebarSection(5, "images_sheets", root.navIndexFor(5, "images_sheets")) }
                            SecondaryButton { text: I18n.t("resize_crop"); onClicked: root.openSidebarSection(5, "video", root.navIndexFor(5, "video")) }
                            SecondaryButton { text: I18n.t("watermark_text"); onClicked: root.openSidebarSection(5, "watermark_text", root.navIndexFor(5, "watermark_text")) }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root.selectedMediaType === "video"
                            spacing: 8
                            SecondaryButton { text: I18n.t("video_editor"); onClicked: root.openSidebarSection(5, "video_editor", root.navIndexFor(5, "video_editor")) }
                            SecondaryButton { text: I18n.t("trim_size"); onClicked: root.openSidebarSection(5, "video", root.navIndexFor(5, "video")) }
                            SecondaryButton { text: I18n.t("audio_subtitles"); onClicked: root.openSidebarSection(5, "audio_subtitles", root.navIndexFor(5, "audio_subtitles")) }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root.selectedMediaType === "text"
                            spacing: 8
                            SecondaryButton { text: I18n.t("text_formats"); onClicked: root.openSidebarSection(5, "core", root.navIndexFor(5, "core")) }
                            SecondaryButton { text: I18n.t("output"); onClicked: root.openSidebarSection(5, "output", root.navIndexFor(5, "output")) }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(360, root.height - 360)
                radius: Theme.radiusPanel
                color: Theme.bgSurface
                border.width: 1
                border.color: Theme.bgBorder
                clip: true

                DropArea {
                    anchors.fill: parent
                    visible: backend ? backend.queueCount === 0 : true
                    enabled: visible
                    z: 10
                    onDropped: function(drop) {
                        if (drop.hasUrls) {
                            backend && backend.addDroppedUrls(drop.urls)
                            drop.acceptProposedAction()
                        }
                    }
                }

                DropArea {
                    id: queueAppendDropArea
                    objectName: "queueAppendDropArea"
                    anchors.fill: parent
                    visible: backend ? backend.queueCount > 0 : false
                    enabled: visible
                    keys: ["text/uri-list"]
                    z: 30
                    onDropped: function(drop) {
                        if (drop.hasUrls) {
                            backend && backend.addDroppedUrls(drop.urls)
                            drop.acceptProposedAction()
                        }
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 10
                    visible: queueAppendDropArea.containsDrag
                    z: 29
                    radius: Theme.radiusMd
                    color: Theme.accentSoft
                    border.width: 1
                    border.color: Theme.accent
                    opacity: 0.94

                    ColumnLayout {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 32, 520)
                        spacing: Theme.space2

                        Label {
                            Layout.fillWidth: true
                            text: I18n.t("drop_append_title")
                            color: Theme.textPrimary
                            font.family: Theme.displayFont
                            font.pixelSize: Theme.fontSizeLg
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }

                        Label {
                            Layout.fillWidth: true
                            text: I18n.t("drop_append_hint")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontSizeSm
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                ColumnLayout {
                    id: emptyQueueState
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 28, 680)
                    visible: backend ? backend.queueCount === 0 : true
                    spacing: Theme.space3

                    DropZone {
                        objectName: "queueDropZone"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 260
                        Component.onCompleted: root.queueDropZoneHeight = height
                        onHeightChanged: root.queueDropZoneHeight = height
                        onFilesDropped: function(urls) { backend && backend.addDroppedUrls(urls) }
                        onClicked: root.addFilesForWorkspace()
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.space2
                        PrimaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 150
                            text: I18n.t("add_files")
                            onClicked: root.addFilesForWorkspace()
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 150
                            text: I18n.t("add_folder")
                            onClicked: root.addFolderForWorkspace()
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 150
                            text: I18n.t("youtube_url")
                            onClicked: root.openTopMode("downloads")
                        }
                    }
                }

                ListView {
                    id: queueList
                    anchors.fill: parent
                    anchors.margins: 10
                    visible: backend ? backend.queueCount > 0 : false
                    model: backend ? backend.queueModel : null
                    clip: true
                    spacing: 8
                    cacheBuffer: 400
                    reuseItems: true
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: QueueItemCard {
                        property bool matchesQueueFilter: root.queueItemMatches(model.name, model.path, model.mediaType, model.status)
                        visible: matchesQueueFilter
                        height: matchesQueueFilter ? implicitHeight : 0
                        fileName: model.name
                        filePath: model.path
                        mediaType: model.mediaType
                        status: model.status
                        errorText: model.errorText
                        outputPath: model.outputPath || model.previewOutput
                        durationText: model.durationText
                        sizeText: model.sizeText
                        thumbnailSource: model.thumbnailSource
                        progress: model.progress
                        etaText: model.etaText
                        speedText: model.speedText
                        predictedSizeText: model.predictedSizeText
                        compressionText: model.compressionText
                        smartRecommendation: model.smartRecommendation
                        pinned: model.pinned
                        priority: model.priority
                        exitCode: model.exitCode
                        hasOverride: model.hasOverride
                        selected: root.isPathSelected(model.path)
                        highLoadMode: root.highLoadMode
                        showThumbnail: root.queueShowThumbnail
                        showMetrics: root.queueShowMetrics
                        showActions: root.queueShowActions
                        showSize: root.queueShowSize
                        showDuration: root.queueShowDuration
                        showCodec: root.queueShowCodec
                        showOutput: root.queueShowOutput
                        showProgress: root.queueShowProgress
                        shimmerPhase: root.sharedShimmerPhase
                        itemIndex: index
                        onSelectedRequested: function(path, modifiers) {
                            root.selectQueuePath(path, index, modifiers, model.name, model.mediaType, model.thumbnailSource)
                        }
                        onRetryRequested: function(path) { backend && backend.retryTaskPath(path) }
                        onSkipRequested: function(path) { backend && backend.skipCurrentFile() }
                        onRemoveRequested: function(path) {
                            if (root.selectedPath === path) {
                                root.selectedPath = ""
                                root.selectedName = ""
                                root.selectedMediaType = ""
                                root.selectedThumbnailSource = ""
                                root.selectedPreviewFormat = ""
                            }
                            backend && backend.removeTaskPath(path)
                        }
                        onOverrideRequested: function(path) {
                            root.selectedPath = path
                            root.selectedIndex = index
                            root.openSidebarSection(5, "selected_override", -1)
                            if (backend)
                                backend.selectQueuePath(path)
                        }
                        onOpenOutputRequested: function(path) {
                            backend && backend.openOutputForPath(path)
                        }
                        onQuickConvertRequested: function(path, name, mediaType) {
                            root.openQuickConvert(path, name, mediaType, index)
                        }
                        onMoveRequested: function(path, targetIndex) {
                            if (backend)
                                backend.movePathToIndex(path, targetIndex)
                        }
                        onPinnedRequested: function(path) { backend && backend.toggleTaskPinned(path) }
                        onPriorityRequested: function(path, priority) { backend && backend.setTaskPriority(path, priority) }
                    }
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

            LogPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
            }
        }
    }

    component AnalyticsScreen: Item {
        AnalyticsPanel {
            anchors.fill: parent
            anchors.margins: 12
            speedHistory: backend ? backend.speedHistory : []
            fileTimings: backend ? backend.fileTimings : []
            codecDistribution: backend ? backend.codecDistribution : ({})
            resourceHistory: backend ? backend.resourceHistory : []
        }
    }

    component PresetsScreen: ScrollView {
        id: presetsScreen
        clip: true

        ColumnLayout {
            width: presetsScreen.availableWidth
            spacing: 12
            anchors.margins: 12

            Label {
                Layout.fillWidth: true
                text: I18n.t("presets")
                color: Theme.textPrimary
                font.family: Theme.displayFont
                font.pixelSize: Theme.fontHeading
                font.bold: true
            }

            PresetsBar {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                model: backend ? backend.presetsModel : null
                activePreset: root.selectedPreset
                onPresetSelected: function(name) {
                    root.selectedPreset = name
                    if (backend)
                        backend.loadPreset(name)
                }
            }

            Panel {
                title: I18n.t("presets")
                AppComboBox { id: presetScreenCombo; model: backend ? backend.presetsModel : null }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton { text: I18n.t("load"); onClicked: { root.selectedPreset = presetScreenCombo.currentText; backend && backend.loadPreset(presetScreenCombo.currentText) } }
                    SecondaryButton { text: I18n.t("save"); onClicked: backend && backend.savePreset(presetScreenCombo.currentText || "Custom", collectSettings()) }
                    SecondaryButton { text: I18n.t("delete"); onClicked: backend && backend.deletePreset(presetScreenCombo.currentText) }
                }
            }

            LogPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
            }
        }
    }

    component FfmpegScreen: ScrollView {
        id: ffmpegScreen
        clip: true

        ColumnLayout {
            width: ffmpegScreen.availableWidth
            spacing: 12
            anchors.margins: 12

            Panel {
                title: I18n.t("ffmpeg_watch")
                AppTextField { id: ffmpegScreenPathField; text: backend ? backend.ffmpegPath : ""; onEditingFinished: { if (backend) backend.ffmpegPath = text } }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton { text: I18n.t("choose"); onClicked: backend && backend.pickFfmpeg() }
                    SecondaryButton { text: I18n.t("refresh"); onClicked: backend && backend.refreshEncoders() }
                    SecondaryButton { text: I18n.t("update_ffmpeg"); onClicked: backend && backend.updateFfmpeg() }
                }
                Label { Layout.fillWidth: true; text: backend ? backend.encoderInfo : ""; color: Theme.textMuted; wrapMode: Text.WordWrap; font.pixelSize: Theme.fontMeta }
                AppTextField { id: ffmpegScreenWatchField; text: backend ? backend.watchFolder : ""; placeholderText: I18n.t("watch_folder"); onEditingFinished: { if (backend) backend.watchFolder = text } }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton { text: I18n.t("choose"); onClicked: backend && backend.pickWatchFolder() }
                    SecondaryButton { text: backend && backend.watchRunning ? I18n.t("stop_watch") : I18n.t("start_watch"); onClicked: backend && (backend.watchRunning ? backend.stopWatching() : backend.startWatching()) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton { text: I18n.t("import"); onClicked: backend && backend.importProject() }
                    SecondaryButton { text: I18n.t("export"); onClicked: backend && backend.exportProject(collectSettings()) }
                }
            }

            LogPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
            }
        }
    }

    component YoutubeScreen: ScrollView {
        id: youtubeScreen
        clip: true

        ColumnLayout {
            width: youtubeScreen.availableWidth
            spacing: 12
            anchors.margins: 12

            YoutubeDownloadPanel {}

            LogPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 260
            }
        }
    }

    component YoutubeDownloadPanel: Panel {
        title: I18n.t("youtube_download")
        property string selectedDownloadMode: "video"

        function downloadOptions(urlText) {
            return {
                url: urlText,
                mode: selectedDownloadMode,
                quality: youtubeQualityCombo.currentText,
                playlist: youtubePlaylistCheck.checked,
                subtitles: youtubeSubtitlesCheck.checked,
                cookies_file: youtubeCookiesField.text,
                rate_limit_kbps: youtubeRateLimitSpin.value
            }
        }

        function startDownload(mode) {
            if (!backend)
                return
            if (!backend.ensureOutputDirSelected())
                return
            var options = downloadOptions(youtubeUrlField.text)
            options.mode = mode || selectedDownloadMode
            backend.downloadYoutubeAdvanced(options)
        }

        function appendDownloadText(value) {
            var text = String(value || "").trim()
            if (!text.length)
                return
            youtubeUrlField.text = youtubeUrlField.text.length > 0 ? youtubeUrlField.text + "\n" + text : text
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: backend && !backend.outputDirConfigured ? 56 : 0
            visible: backend ? !backend.outputDirConfigured : false
            radius: Theme.radiusPanel
            color: Theme.warningSoft
            border.width: 1
            border.color: Theme.accentWarn
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Label {
                    Layout.fillWidth: true
                    text: I18n.t("output_folder_required_detail")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
                }
                SecondaryButton {
                    text: I18n.t("choose_output_folder")
                    enabled: backend ? !backend.youtubeDownloadRunning : false
                    onClicked: backend && backend.ensureOutputDirSelected()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Button {
                id: youtubeVideoSegment
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                text: "🎬 " + I18n.t("video")
                hoverEnabled: true
                onClicked: selectedDownloadMode = "video"
                background: Rectangle {
                    radius: Theme.radiusButton
                    color: selectedDownloadMode === "video" ? Theme.accentSoft : Theme.bgElevated
                    border.width: 1
                    border.color: selectedDownloadMode === "video" ? Theme.accent : Theme.borderSubtle
                }
                contentItem: Label {
                    text: youtubeVideoSegment.text
                    color: selectedDownloadMode === "video" ? Theme.textPrimary : Theme.textSecondary
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Theme.fontSizeLg
                    font.bold: selectedDownloadMode === "video"
                }
            }
            Button {
                id: youtubeAudioSegment
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                text: "🎧 " + I18n.t("audio_only")
                hoverEnabled: true
                onClicked: selectedDownloadMode = "audio"
                background: Rectangle {
                    radius: Theme.radiusButton
                    color: selectedDownloadMode === "audio" ? Theme.accentSoft : Theme.bgElevated
                    border.width: 1
                    border.color: selectedDownloadMode === "audio" ? Theme.accent : Theme.borderSubtle
                }
                contentItem: Label {
                    text: youtubeAudioSegment.text
                    color: selectedDownloadMode === "audio" ? Theme.textPrimary : Theme.textSecondary
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Theme.fontSizeLg
                    font.bold: selectedDownloadMode === "audio"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            AppComboBox {
                id: youtubeHistoryCombo
                Layout.fillWidth: true
                model: backend ? backend.youtubeDownloadHistory : []
                enabled: backend ? backend.youtubeDownloadHistory.length > 0 : false
                onActivated: youtubeUrlField.text = currentText
            }
            SecondaryButton {
                text: I18n.t("clear")
                enabled: backend ? backend.youtubeDownloadHistory.length > 0 : false
                onClicked: backend && backend.clearYoutubeHistory()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            SecondaryButton {
                Layout.fillWidth: true
                text: I18n.t("import_urls")
                enabled: backend ? true : false
                onClicked: backend && backend.importDownloadUrlsFromFile(downloadOptions(""))
            }
            SecondaryButton {
                Layout.fillWidth: true
                text: backend && backend.ytdlpUpdateRunning ? I18n.t("updating_ytdlp") : I18n.t("update_ytdlp")
                enabled: backend ? !backend.ytdlpUpdateRunning : false
                onClicked: backend && backend.updateYtdlp()
            }
            SecondaryButton {
                Layout.fillWidth: true
                text: I18n.t("retry_failed")
                enabled: backend ? backend.youtubeDownloadQueue.length > 0 : false
                onClicked: backend && backend.retryFailedYoutubeDownloads()
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            visible: backend ? backend.youtubeDownloadHistory.length > 0 : false
            Repeater {
                model: backend ? backend.youtubeDownloadHistory : []
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    radius: Theme.radiusSm
                    color: Theme.bgElevated
                    border.width: 1
                    border.color: Theme.borderSubtle
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8
                        Label {
                            Layout.fillWidth: true
                            text: modelData
                            color: Theme.textSecondary
                            font.pixelSize: Theme.fontMeta
                            elide: Text.ElideMiddle
                        }
                        SecondaryButton {
                            Layout.fillWidth: false
                            Layout.preferredWidth: 104
                            text: I18n.t("retry")
                            onClicked: {
                                youtubeUrlField.text = modelData
                                startDownload(selectedDownloadMode)
                            }
                        }
                    }
                }
            }
        }
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: youtubeUrlField.implicitHeight

            AppTextField {
                id: youtubeUrlField
                anchors.fill: parent
                placeholderText: I18n.t("youtube_url")
                enabled: backend ? true : false
            }

            DropArea {
                anchors.fill: parent
                onDropped: function(drop) {
                    var value = ""
                    if (drop.hasText)
                        value = String(drop.text || "").trim()
                    if (value.indexOf("http://") >= 0 || value.indexOf("https://") >= 0) {
                        appendDownloadText(value)
                        drop.acceptProposedAction()
                    } else if (drop.hasUrls && drop.urls.length > 0) {
                        backend && backend.addDroppedDownloadUrls(drop.urls, downloadOptions(""))
                        drop.acceptProposedAction()
                    }
                }
            }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: 8
            columnSpacing: 8
            FieldLabel { text: I18n.t("youtube_quality") }
            AppComboBox {
                id: youtubeQualityCombo
                model: ["best", "1080p", "720p", "audio_only"]
                currentIndex: 0
                enabled: backend ? true : false
            }
            FieldLabel { text: I18n.t("speed_limit_kbps") }
            AppSpinBox {
                id: youtubeRateLimitSpin
                from: 0
                to: 102400
                stepSize: 256
                value: 0
                editable: true
                enabled: backend ? true : false
            }
            FieldLabel { text: I18n.t("youtube.cookies_file") }
            RowLayout {
                Layout.fillWidth: true
                AppTextField {
                    id: youtubeCookiesField
                    text: backend ? backend.youtubeCookiesPath : ""
                    enabled: backend ? true : false
                    onEditingFinished: backend && backend.setYoutubeCookiesPath(text)
                }
                SecondaryButton {
                    text: "..."
                    Layout.preferredWidth: 42
                    enabled: backend ? true : false
                    onClicked: backend && backend.pickYoutubeCookies()
                }
            }
        }
        Label {
            Layout.fillWidth: true
            text: backend ? "🍪 " + backend.youtubeCookiesStatus : "🍪 Cookies: --"
            color: backend && backend.youtubeCookiesStatus.indexOf("Cookies: підключено") >= 0 ? Theme.statusSuccess : Theme.textMuted
            font.pixelSize: Theme.fontMeta
            elide: Text.ElideRight
        }
        RowLayout {
            Layout.fillWidth: true
            AppCheckBox {
                id: youtubePlaylistCheck
                text: I18n.t("youtube.playlist")
                enabled: backend ? true : false
            }
            AppCheckBox {
                id: youtubeSubtitlesCheck
                text: I18n.t("youtube.subtitles")
                enabled: backend ? true : false
            }
            SecondaryButton {
                Layout.fillWidth: false
                Layout.preferredWidth: 150
                text: I18n.t("youtube.preview_source")
                enabled: backend && String(youtubeUrlField.text).trim().length > 0
                onClicked: backend && backend.previewYoutubePlaylist(youtubeUrlField.text, youtubePlaylistCheck.checked, youtubeCookiesField.text)
            }
        }
        Label {
            Layout.fillWidth: true
            visible: backend ? backend.youtubePlaylistPreview.length > 0 : false
            text: backend ? "📦 " + backend.youtubePlaylistPreview : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.fontMeta
            wrapMode: Text.WordWrap
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 116 : 0
            visible: backend ? Object.keys(backend.youtubePreviewInfo).length > 0 : false
            radius: Theme.radiusPanel
            color: Theme.bgSurface
            border.width: 1
            border.color: Theme.borderSubtle
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 148
                    Layout.fillHeight: true
                    radius: Theme.radiusSm
                    color: Theme.input
                    clip: true
                    Image {
                        anchors.fill: parent
                        source: backend && backend.youtubePreviewInfo.thumbnail ? backend.youtubePreviewInfo.thumbnail : ""
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        visible: source.toString().length > 0
                    }
                    Label {
                        anchors.centerIn: parent
                        width: parent.width - 16
                        visible: !(backend && backend.youtubePreviewInfo.thumbnail)
                        text: backend && backend.youtubePreviewInfo.source_type ? backend.youtubePreviewInfo.source_type : "URL"
                        color: Theme.textMuted
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Label {
                        Layout.fillWidth: true
                        text: backend ? (backend.youtubePreviewInfo.title || backend.youtubePreviewInfo.error || "") : ""
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeSm
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: backend ? ((backend.youtubePreviewInfo.source_type || "source") + " | " + (backend.youtubePreviewInfo.duration_text || "--:--") + " | " + (backend.youtubePreviewInfo.quality_summary || "")) : ""
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontMeta
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: backend ? ("items: " + (backend.youtubePreviewInfo.count || 1) + " | " + (backend.youtubePreviewInfo.extractor || "")) : ""
                        color: Theme.textMuted
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        visible: backend ? !!backend.youtubePreviewInfo.hint : false
                        text: backend ? backend.youtubePreviewInfo.hint : ""
                        color: Theme.accentWarn
                        font.pixelSize: Theme.fontMeta
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton {
                Layout.fillWidth: true
                text: "⬇️ " + I18n.t("add_to_queue")
                enabled: backend && String(youtubeUrlField.text).trim().length > 0
                onClicked: startDownload(selectedDownloadMode)
            }
            SecondaryButton {
                text: I18n.t("cancel")
                enabled: backend ? backend.youtubeDownloadRunning : false
                onClicked: backend && backend.cancelYoutubeDownload()
            }
        }
        ProgressBar {
            Layout.fillWidth: true
            visible: backend ? backend.youtubeDownloadRunning || backend.youtubeDownloadProgress > 0 : false
            from: 0
            to: 1
            value: backend ? backend.youtubeDownloadProgress : 0
        }
        Label {
            Layout.fillWidth: true
            text: backend ? backend.youtubeDownloadStatus : ""
            color: Theme.textMuted
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.fontMeta
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: backend && backend.youtubeDownloadQueue.length > 0
                ? Math.min(480, 58 + backend.youtubeDownloadQueue.length * 112)
                : 128
            radius: Theme.radiusPanel
            color: Theme.bgSurface
            border.width: 1
            border.color: Theme.borderSubtle
            ColumnLayout {
                id: downloadQueueColumn
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                Label {
                    Layout.fillWidth: true
                    text: "⬇️ " + I18n.t("download_queue")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeSm
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    visible: backend ? backend.youtubeDownloadQueue.length === 0 : true
                    text: I18n.t("no_active_downloads")
                    color: Theme.textMuted
                    font.pixelSize: Theme.fontMeta
                }
                Repeater {
                    model: backend ? backend.youtubeDownloadQueue : []
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 104
                        radius: Theme.radiusSm
                        color: Theme.bgElevated
                        border.width: 1
                        border.color: modelData.status === "failed" ? Theme.accentError
                                      : modelData.status === "done" ? Theme.statusSuccess
                                      : modelData.status === "running" ? Theme.accent
                                      : Theme.borderSubtle
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 5
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.mode + " | " + modelData.quality + " | " + modelData.statusText
                                    color: Theme.textPrimary
                                    font.pixelSize: Theme.fontSizeSm
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: Math.round((modelData.progress || 0) * 100) + "%"
                                    color: Theme.textSecondary
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontMeta
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: modelData.url
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontMeta
                                elide: Text.ElideMiddle
                            }
                            ProgressBar {
                                Layout.fillWidth: true
                                from: 0
                                to: 1
                                value: modelData.progress || 0
                            }
                            Label {
                                Layout.fillWidth: true
                                text: I18n.t("speed") + ": " + modelData.speedText + " | " + I18n.t("eta") + ": " + modelData.etaText + " | " + modelData.message
                                color: Theme.textMuted
                                font.pixelSize: Theme.fontMeta
                                elide: Text.ElideRight
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.rateLimitKbps > 0 ? I18n.t("limit") + ": " + modelData.rateLimitKbps + " KB/s" : I18n.t("limit") + ": " + I18n.t("none")
                                    color: Theme.textDisabled
                                    font.family: Theme.monoFont
                                    font.pixelSize: Theme.fontMeta
                                    elide: Text.ElideRight
                                }
                                SecondaryButton {
                                    Layout.fillWidth: false
                                    Layout.preferredWidth: 96
                                    text: I18n.t("retry")
                                    visible: modelData.status === "failed" || modelData.status === "cancelled"
                                    onClicked: backend && backend.retryYoutubeDownload(modelData.id)
                                }
                            }
                        }
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 170
            radius: Theme.radiusPanel
            color: Theme.bgSurface
            border.width: 1
            border.color: Theme.borderSubtle
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: I18n.t("download_log")
                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontSizeSm
                        font.bold: true
                    }
                    SecondaryButton {
                        Layout.fillWidth: false
                        text: I18n.t("clear")
                        onClicked: backend && backend.clearYoutubeDownloadLog()
                    }
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: backend ? backend.youtubeDownloadLog : []
                    clip: true
                    spacing: 4
                    delegate: Label {
                        width: ListView.view.width
                        text: modelData
                        color: modelData.indexOf("[ERROR]") >= 0 ? Theme.accentError : modelData.indexOf("[WARN]") >= 0 ? Theme.accentWarn : Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.fontMeta
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    // StatusPill, TopModeButton, Panel, FieldLabel, LogPanel
    // are now in ui/qml/components/ as standalone QML files.

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
            if (preset.out_text_fmt) root.setComboText(outTextFmt, preset.out_text_fmt)
            if (preset.audio_bitrate) audioBitrateField.text = preset.audio_bitrate
            if (preset.audio_codec) root.setComboText(audioCodecCombo, preset.audio_codec)
            if (preset.audio_track_index !== undefined) audioTrackSpin.value = Number(preset.audio_track_index) + 1
            if (preset.crf !== undefined) crfSpin.value = Number(preset.crf)
            if (preset.preset) root.setComboText(presetCombo, preset.preset)
            if (preset.performance_profile) root.setComboText(performanceProfileCombo, preset.performance_profile)
            targetSizeField.text = preset.target_size_mb || ""
            if (preset.cpu_load_limit !== undefined) cpuLimitSpin.value = Number(preset.cpu_load_limit)
            if (preset.gpu_load_limit !== undefined) gpuLimitSpin.value = Number(preset.gpu_load_limit)
            smartConvertCheck.checked = !!preset.smart_convert_enabled
            root.setComboText(smartContentTypeCombo, preset.smart_content_type || "auto")
            root.setComboText(smartQualityTargetCombo, preset.smart_quality_target || "balanced")
            smartReencodeCheck.checked = preset.smart_reencode_detection === undefined ? true : !!preset.smart_reencode_detection
            smartTwoPassCheck.checked = !!preset.smart_two_pass
            smartIntegrityCheck.checked = !!preset.smart_integrity_check
            root.setComboText(smartQualityMetricCombo, preset.smart_quality_metric || "none")
            smartAbTestCheck.checked = !!preset.smart_ab_test
            smartAbCrfsField.text = preset.smart_ab_crfs || "18,23,28"
            if (preset.smart_ab_duration !== undefined) smartAbDurationSpin.value = Number(preset.smart_ab_duration)
            if (preset.portrait) root.setComboCanonical(portraitCombo, preset.portrait, root.portraitCanonicalOptions)
            if (preset.img_quality !== undefined) imgQualitySpin.value = Number(preset.img_quality)
            overwriteCheck.checked = !!preset.overwrite
            fastCopyCheck.checked = !!preset.fast_copy
            skipExistingCheck.checked = !!preset.skip_existing
            root.setComboText(collisionPolicyCombo, preset.output_collision_policy || (preset.overwrite ? "overwrite" : preset.skip_existing ? "stop" : "index"))
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
            if (preset.rotate) root.setComboCanonical(rotateCombo, preset.rotate, root.rotateCanonicalOptions)
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
            if (preset.wm_pos) root.setComboCanonical(wmPosCombo, preset.wm_pos, root.positionCanonicalOptions)
            if (preset.wm_opacity !== undefined) wmOpacitySpin.value = Number(preset.wm_opacity)
            if (preset.wm_scale !== undefined) wmScaleSpin.value = Number(preset.wm_scale)
            textWatermarkField.text = preset.text_wm || ""
            if (preset.text_pos) root.setComboCanonical(textPosCombo, preset.text_pos, root.positionCanonicalOptions)
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
            if (preset.device_profile) root.setComboText(deviceProfileCombo, preset.device_profile)
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
            root.setComboText(editorDenoiseCombo, preset.editor_denoise || "none")
            editorBrightnessField.text = preset.editor_brightness || ""
            editorContrastField.text = preset.editor_contrast || ""
            editorSaturationField.text = preset.editor_saturation || ""
            editorGammaField.text = preset.editor_gamma || ""
            editorLutPathField.text = preset.editor_lut_path || ""
            cloudUploadCheck.checked = !!preset.cloud_upload_enabled
            root.setComboText(cloudProviderCombo, preset.cloud_provider || "rclone")
            cloudRclonePathField.text = preset.cloud_rclone_path || "rclone"
            cloudRemotePathField.text = preset.cloud_remote_path || ""
            root.scheduleSettingsSync()
        }

        function setOutputFormatFor(mediaType, format) {
            if (!format || format.length === 0)
                return
            if (mediaType === "image")
                root.setComboText(outImageFmt, format)
            else if (mediaType === "audio")
                root.setComboText(outAudioFmt, format)
            else if (mediaType === "subtitle")
                root.setComboText(outSubtitleFmt, format)
            else if (mediaType === "text")
                root.setComboText(outTextFmt, format)
            else
                root.setComboText(outVideoFmt, format)
            root.scheduleSettingsSync()
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
                portrait: root.canonicalOption(root.portraitCanonicalOptions, portraitCombo.currentIndex, portraitCombo.currentText),
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
                rotate: root.canonicalOption(root.rotateCanonicalOptions, rotateCombo.currentIndex, rotateCombo.currentText),
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
                wm_pos: root.canonicalOption(root.positionCanonicalOptions, wmPosCombo.currentIndex, wmPosCombo.currentText),
                wm_opacity: wmOpacitySpin.value,
                wm_scale: wmScaleSpin.value,
                text_wm: textWatermarkField.text,
                text_pos: root.canonicalOption(root.positionCanonicalOptions, textPosCombo.currentIndex, textPosCombo.currentText),
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
                device_profile: deviceProfileCombo.currentText,
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
            root._langVersion += 1
        }

        function loadTaskOverride(data) {
            overrideOutputTemplateField.text = data.output_template || ""
            if (data.crf !== undefined)
                overrideCrfSpin.value = Number(data.crf)
            overrideAudioBitrateField.text = data.audio_bitrate || ""
        }

        function sectionY(section) {
            var target = String(section || "run")
            var panel = runPanel
            if (["smart_convert", "device_profiles", "video_editor", "subtitle_tools", "privacy_security", "cloud_integration", "commercial_license", "video", "audio_subtitles", "images_sheets", "watermark_text", "metadata_hooks", "selected_override", "ffmpeg_watch"].indexOf(target) >= 0)
                advancedToolsSection.expanded = true
            if (target === "smart_convert") panel = smartConvertPanel
            else if (target === "device_profiles") panel = deviceProfilesPanel
            else if (target === "video_editor") panel = videoEditorPanel
            else if (target === "subtitle_tools") panel = subtitleToolsPanel
            else if (target === "privacy_security") panel = privacySecurityPanel
            else if (target === "cloud_integration") panel = cloudIntegrationPanel
            else if (target === "commercial_license") panel = commercialLicensePanel
            else if (target === "core") panel = corePanel
            else if (target === "output") panel = outputPanel
            else if (target === "video") panel = videoPanel
            else if (target === "audio_subtitles") panel = audioSubtitlesPanel
            else if (target === "images_sheets") panel = imagesSheetsPanel
            else if (target === "watermark_text") panel = watermarkTextPanel
            else if (target === "metadata_hooks") panel = metadataHooksPanel
            else if (target === "selected_override") panel = selectedOverridePanel
            else if (target === "ffmpeg_watch") panel = ffmpegWatchPanel
            return Math.max(0, panel.mapToItem(settingsRoot, 0, 0).y - Theme.space3)
        }

        Panel {
            id: runPanel
            title: I18n.t("run")
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: backend && backend.isRunning ? I18n.t("running") : I18n.t("start"); enabled: backend && !backend.isRunning && formValid; onClicked: startIfValid() }
                SecondaryButton { text: backend && backend.isPaused ? I18n.t("resume") : I18n.t("pause"); enabled: backend && backend.isRunning; onClicked: backend.isPaused ? backend.resumeConversion() : backend.pauseConversion() }
                SecondaryButton { text: I18n.t("skip"); enabled: backend && backend.isRunning; onClicked: backend.skipCurrentFile() }
                SecondaryButton { text: I18n.t("stop"); enabled: backend && backend.isRunning; onClicked: backend.stopConversion() }
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
            id: presetsSettingsPanel
            title: I18n.t("presets")
            AppComboBox { id: savedPresetCombo; model: backend ? backend.presetsModel : null }
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: I18n.t("load"); onClicked: { root.selectedPreset = savedPresetCombo.currentText; backend && backend.loadPreset(savedPresetCombo.currentText) } }
                SecondaryButton { text: I18n.t("save"); onClicked: backend && backend.savePreset(savedPresetCombo.currentText || "Custom", collectSettings()) }
                SecondaryButton { text: I18n.t("delete"); onClicked: backend && backend.deletePreset(savedPresetCombo.currentText) }
            }
        }

        Panel {
            id: smartConvertPanel
            title: I18n.t("smart_convert")
            AppCheckBox { id: smartConvertCheck; text: I18n.t("smart_convert_enabled"); onToggled: scheduleSettingsSync() }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                FieldLabel { text: I18n.t("smart_content_type") }
                AppComboBox { id: smartContentTypeCombo; model: root.smartContentTypes; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("smart_quality_target") }
                AppComboBox { id: smartQualityTargetCombo; model: root.smartQualityTargets; currentIndex: 1; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("smart_quality_metric") }
                AppComboBox { id: smartQualityMetricCombo; model: root.smartQualityMetrics; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("smart_ab_crfs") }
                AppTextField { id: smartAbCrfsField; text: "18,23,28"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("smart_ab_duration") }
                AppSpinBox { id: smartAbDurationSpin; from: 1; to: 120; value: 8; onValueChanged: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: smartReencodeCheck; text: I18n.t("smart_reencode_detection"); checked: true; onToggled: scheduleSettingsSync() }
                AppCheckBox { id: smartTwoPassCheck; text: I18n.t("smart_two_pass"); onToggled: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
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
            id: deviceProfilesPanel
            title: I18n.t("device_profiles")
            FieldLabel { text: I18n.t("device_profile") }
            AppComboBox { id: deviceProfileCombo; model: root.deviceProfiles; currentIndex: 0; onActivated: scheduleSettingsSync() }
            Label {
                Layout.fillWidth: true
                text: I18n.t("device_profile_hint")
                color: Theme.textMuted
                font.pixelSize: Theme.fontMeta
                wrapMode: Text.WordWrap
            }
        }

        Panel {
            id: corePanel
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
                FieldLabel { text: I18n.t("text") }
                AppComboBox { id: outTextFmt; model: root.textFormats; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("codec") }
                AppComboBox { id: codecCombo; model: root.codecOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("hw") }
                AppComboBox { id: hwCombo; model: root.hwOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("performance_profile") }
                AppComboBox { id: performanceProfileCombo; model: root.performanceProfiles; currentIndex: 1; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("target_size_mb") }
                AppTextField { id: targetSizeField; placeholderText: I18n.t("target_size_hint"); onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("cpu_load_limit") }
                AppSpinBox { id: cpuLimitSpin; from: 1; to: 100; value: 95; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("gpu_load_limit") }
                AppSpinBox { id: gpuLimitSpin; from: 1; to: 100; value: 98; onValueChanged: scheduleSettingsSync() }
                FieldLabel { text: "Disk reserve (MiB)" }
                AppSpinBox { id: diskSafetyMarginSpin; from: 0; to: 10240; value: 512; onValueChanged: scheduleSettingsSync() }
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
            id: outputPanel
            title: I18n.t("output")
            AppTextField { id: outputDirField; text: backend ? backend.outputDir : ""; placeholderText: I18n.t("output_folder_required"); onEditingFinished: { if (backend) backend.outputDir = text; scheduleSettingsSync() } }
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: I18n.t("choose"); onClicked: backend && backend.pickOutputDir() }
                SecondaryButton { text: I18n.t("open"); onClicked: backend && backend.openOutputDir() }
                SecondaryButton { text: I18n.t("preview"); onClicked: backend && backend.refreshOutputPreview(collectSettings()) }
                SecondaryButton { text: I18n.t("copy_rename"); onClicked: backend && backend.copyRenamePreview(collectSettings()) }
                SecondaryButton { text: "CSV"; onClicked: backend && backend.exportRenamePreviewCsv(collectSettings()) }
            }
            FieldLabel { text: I18n.t("template") }
            AppTextField { id: outputTemplateField; text: "{stem}"; onEditingFinished: scheduleSettingsSync() }
            FieldLabel { text: "Політика колізій" }
            AppComboBox {
                id: collisionPolicyCombo
                model: ["index", "parent", "stop", "overwrite"]
                currentIndex: 0
                onActivated: {
                    overwriteCheck.checked = currentText === "overwrite"
                    skipExistingCheck.checked = false
                    scheduleSettingsSync()
                }
            }
            AppCheckBox {
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

        CollapsibleSection {
            id: advancedToolsSection
            title: I18n.t("advanced_settings")
            subtitle: I18n.t("advanced_settings_hint")
            expanded: root.advancedSettingsExpanded

        Panel {
            id: videoPanel
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
            id: videoEditorPanel
            title: I18n.t("video_editor")
            RowLayout {
                Layout.fillWidth: true
                AppCheckBox { id: editorDeinterlaceCheck; text: I18n.t("editor_deinterlace"); onToggled: scheduleSettingsSync() }
                AppCheckBox { id: editorStabilizeCheck; text: I18n.t("editor_stabilize"); onToggled: scheduleSettingsSync() }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
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
            title: I18n.t("audio_subtitles")
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                FieldLabel { text: I18n.t("bitrate") }
                AppTextField { id: audioBitrateField; text: "192k"; onEditingFinished: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("audio_codec") }
                AppComboBox { id: audioCodecCombo; model: root.audioCodecOptions; currentIndex: 0; onActivated: scheduleSettingsSync() }
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
                FieldLabel { text: I18n.t("model"); visible: backend ? backend.isWhisperAvailable : true }
                AppComboBox { id: subtitleModelCombo; model: ["tiny", "base", "small", "medium", "large"]; currentIndex: 1; visible: backend ? backend.isWhisperAvailable : true; enabled: visible; onActivated: scheduleSettingsSync() }
                FieldLabel { text: I18n.t("engine"); visible: backend ? backend.isWhisperAvailable : true }
                AppComboBox { id: subtitleEngineCombo; model: ["auto", "whisper"]; currentIndex: 0; visible: backend ? backend.isWhisperAvailable : true; enabled: visible; onActivated: scheduleSettingsSync() }
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
            RowLayout {
                Layout.fillWidth: true
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
            title: I18n.t("subtitle_tools")
            GridLayout {
                Layout.fillWidth: true
                columns: 2
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
            AppCheckBox { id: subtitleStyleCheck; text: I18n.t("subtitle_style_enabled"); onToggled: scheduleSettingsSync() }
        }

        Panel {
            id: imagesSheetsPanel
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
            id: watermarkTextPanel
            title: I18n.t("watermark_text")
            RowLayout {
                Layout.fillWidth: true
                AppTextField { id: wmPathField; placeholderText: I18n.t("watermark_image"); onEditingFinished: scheduleSettingsSync() }
                SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickWatermark() }
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
                SecondaryButton { text: "..."; Layout.preferredWidth: 42; onClicked: backend && backend.pickFont() }
            }
        }

        Panel {
            id: metadataHooksPanel
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
            id: privacySecurityPanel
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
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                FieldLabel { text: I18n.t("checksum_algorithm") }
                AppComboBox { id: checksumCombo; model: ["none", "md5", "sha256"]; currentIndex: 0; onActivated: scheduleSettingsSync() }
            }
            RowLayout {
                Layout.fillWidth: true
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
            title: I18n.t("cloud_integration")
            AppCheckBox { id: cloudUploadCheck; text: I18n.t("cloud_upload_enabled") + " (Pro)"; enabled: backend ? backend.proFeaturesEnabled : false; onToggled: scheduleSettingsSync() }
            Label {
                Layout.fillWidth: true
                text: backend && backend.proFeaturesEnabled ? I18n.t("cloud_pro_enabled") : I18n.t("cloud_pro_required")
                color: backend && backend.proFeaturesEnabled ? Theme.textMuted : Theme.accentWarn
                font.pixelSize: Theme.fontMeta
                wrapMode: Text.WordWrap
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
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
            id: commercialLicensePanel
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
                columns: 2
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
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton {
                    text: I18n.t("activate_key")
                    onClicked: backend && backend.activateLicenseKey(licenseKeyField.text)
                }
                SecondaryButton {
                    text: I18n.t("offline_file")
                    onClicked: backend && backend.loadOfflineLicenseFile()
                }
                SecondaryButton {
                    text: I18n.t("start_trial")
                    enabled: backend ? !backend.licenseActive : false
                    onClicked: backend && backend.startTrial()
                }
                SecondaryButton {
                    text: I18n.t("remove")
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
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton {
                    text: I18n.t("check_update")
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
            title: I18n.t("selected_override")
            AppTextField { id: overrideOutputTemplateField; placeholderText: I18n.t("output_template_override") }
            AppSpinBox { id: overrideCrfSpin; from: 0; to: 51; value: 23 }
            AppTextField { id: overrideAudioBitrateField; placeholderText: I18n.t("audio_bitrate_override") }
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton {
                    text: I18n.t("save")
                    enabled: root.selectedPath.length > 0
                    onClicked: backend && backend.saveTaskOverrideByPath(root.selectedPath, {
                        output_template: overrideOutputTemplateField.text,
                        crf: overrideCrfSpin.value,
                        audio_bitrate: overrideAudioBitrateField.text
                    })
                }
                SecondaryButton {
                    text: I18n.t("batch_override")
                    enabled: root.selectedPaths.length > 1
                    onClicked: backend && backend.saveBulkOverride(root.selectedPaths, {
                        output_template: overrideOutputTemplateField.text,
                        crf: overrideCrfSpin.value,
                        audio_bitrate: overrideAudioBitrateField.text
                    })
                }
                SecondaryButton { text: I18n.t("clear"); enabled: root.selectedPath.length > 0; onClicked: backend && backend.clearTaskOverrideByPath(root.selectedPath) }
            }
        }

        Panel {
            id: ffmpegWatchPanel
            title: I18n.t("ffmpeg_watch")
            AppTextField { id: ffmpegPathField; text: backend ? backend.ffmpegPath : ""; onEditingFinished: { if (backend) backend.ffmpegPath = text } }
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: I18n.t("choose"); onClicked: backend && backend.pickFfmpeg() }
                SecondaryButton { text: I18n.t("refresh"); onClicked: backend && backend.refreshEncoders() }
                SecondaryButton { text: I18n.t("update_ffmpeg"); onClicked: backend && backend.updateFfmpeg() }
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
            RowLayout {
                Layout.fillWidth: true
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
                    model: root.schedulerModeOptions
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
                columns: 2
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
                    model: root.completionActionOptions
                    currentIndex: backend ? Math.max(0, find(backend.completionAction)) : 0
                    onActivated: {
                        if (backend)
                            backend.completionAction = currentText
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
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
                columns: 2
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
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: I18n.t("choose"); onClicked: backend && backend.pickWatchFolder() }
                SecondaryButton { text: backend && backend.watchRunning ? I18n.t("stop_watch") : I18n.t("start_watch"); onClicked: backend && (backend.watchRunning ? backend.stopWatching() : backend.startWatching()) }
            }
            RowLayout {
                Layout.fillWidth: true
                SecondaryButton { text: I18n.t("import"); onClicked: backend && backend.importProject() }
                SecondaryButton { text: I18n.t("export"); onClicked: backend && backend.exportProject(collectSettings()) }
            }
        }
        }
    }

    WhatsNewPopup {
        id: whatsNewPopup
    }
    
    TutorialPopup {
        id: tutorialPopup
    }
}
