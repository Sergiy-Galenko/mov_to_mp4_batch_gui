import QtQuick 2.15
import QtQml 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "components"
import "layout" as AppLayout
import "screens" as AppScreens

ApplicationWindow {
    id: root
    visible: true
    width: 1240
    height: 840
    visibility: Window.Windowed
    // Keep the OS window controls, resizing, fullscreen and Windows Snap.
    flags: Qt.platform.os === "osx"
        ? Qt.Window | Qt.ExpandedClientAreaHint | Qt.NoTitleBarBackgroundHint | Qt.WindowFullscreenButtonHint
        : Qt.Window
    topPadding: 0
    bottomPadding: 0
    leftPadding: 0
    rightPadding: 0
    font.family: Theme.bodyFont
    minimumWidth: (backend && backend.displayMetrics && backend.displayMetrics.availableWidth)
        ? Math.min(760, Math.max(600, backend.displayMetrics.availableWidth - 20))
        : 760
    minimumHeight: (backend && backend.displayMetrics && backend.displayMetrics.availableHeight)
        ? Math.min(680, Math.max(520, backend.displayMetrics.availableHeight - 40))
        : 680
    title: I18n.t("app.title")
    color: Theme.bgBase

    palette.windowText: Theme.textPrimary
    palette.alternateBase: Theme.panelSecondary
    palette.placeholderText: Theme.textDisabled
    palette.toolTipBase: Theme.panelSecondary
    palette.toolTipText: Theme.textPrimary
    palette.accent: Theme.accent
    palette.window: Theme.bgBase
    palette.base: Theme.input
    palette.text: Theme.textPrimary
    palette.button: Theme.bgSurface
    palette.buttonText: Theme.textPrimary
    palette.highlight: Theme.accentPrimary
    palette.highlightedText: Theme.textOnAccent

    readonly property bool appearanceOpen: themeEditorLoader.item !== null && themeEditorLoader.item.visible
    readonly property bool notificationsOpen: notificationCenterPopup.visible

    function openAppearance() {
        if (themeEditorLoader.item) themeEditorLoader.item.open()
        else themeEditorLoader.active = true
    }

    Loader {
        id: themeEditorLoader
        active: false
        source: "components/ThemeEditorDialog.qml"
        onLoaded: item.open()
    }

    Shortcut {
        sequence: "Ctrl+Alt+0"
        context: Qt.ApplicationShortcut
        onActivated: if (backend) { backend.themeMode = "dark"; backend.resetThemeColors() }
    }

    onXChanged: if (root.visible && root.visibility === Window.Windowed) windowStateTimer.restart()
    onYChanged: if (root.visible && root.visibility === Window.Windowed) windowStateTimer.restart()
    onWidthChanged: if (root.visible && root.visibility === Window.Windowed) windowStateTimer.restart()
    onHeightChanged: if (root.visible && root.visibility === Window.Windowed) windowStateTimer.restart()

    Timer {
        id: windowStateTimer
        interval: 600
        repeat: false
        onTriggered: {
            if (backend && root.visibility === Window.Windowed && root.width >= root.minimumWidth) {
                backend.saveWindowState(root.x, root.y, root.width, root.height)
            }
        }
    }

    Connections {
        target: backend
        function onDisplayMetricsChanged() {
            if (backend && backend.autoDisplayAdaptation) {
                backend.applyDisplayAdaptation()
                if (backend.displayMetrics && backend.displayMetrics.recommendedSidebarCollapsed) {
                    root.sidebarCollapsed = true
                }
            }
        }
        function onSourceUpdateChanged() {
            if (backend && root.pendingSettingsTarget !== "app_update" && (backend.sourceUpdateAvailable || backend.sourceUpdateRestartRequired))
                sourceUpdateDialog.open()
        }
    }

    property bool hasBackend: backend !== null
    property url appLogoSource: Qt.resolvedUrl("../../assets/app-logo-v2.png")
    property bool sidebarCollapsed: false
    property bool compactMode: width < Theme.compactBreakpoint || (backend && (backend.layoutMode === "compact" || (backend.autoDisplayAdaptation && backend.displayMetrics && backend.displayMetrics.category === "compact")))
    property int activeSection: 0
    property string globalSearchText: ""
    property var globalSearchResults: []
    property int globalSearchIndex: 0
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
    property var selectedDetails: ({})
    property string selectedTextPreview: ""
    property int selectedIndex: -1

    onQueueSearchTextChanged: {
        if (queueSearchText.length === 0) syncQueueFilter()
        else queueSearchTimer.restart()
    }

    Timer {
        id: queueSearchTimer
        interval: 180
        onTriggered: root.syncQueueFilter()
    }
    onQueueStatusFilterChanged: syncQueueFilter()
    onActiveWorkspaceModeChanged: syncQueueFilter()

    function syncQueueFilter() {
        queueSearchTimer.stop()
        if (backend)
            backend.setQueueFilter(root.queueSearchText, root.queueStatusFilter, workspaceMediaType())
    }

    function refreshSelectedDetails() {
        if (!backend || !root.selectedPath) {
            root.selectedDetails = ({})
            return
        }
        var details = backend.queueItemDetails(root.selectedPath)
        root.selectedDetails = details
        root.selectedThumbnailSource = details.thumbnail || ""
        root.selectedPreviewFormat = details.format || currentFormatFor(root.selectedMediaType)
    }

    function retainVisibleSelection() {
        if (!backend || root.selectedPaths.length === 0)
            return
        var visible = backend.visibleQueuePaths
        var next = root.selectedPaths.filter(function(path) { return visible.indexOf(path) >= 0 })
        if (next.length === 0 && root.selectedPaths.length > 0) {
            clearQueueSelection()
        } else {
            root.selectedPaths = next
            if (root.selectedPath && visible.indexOf(root.selectedPath) < 0)
                clearQueueSelection()
        }
    }

    property var selectedPaths: []
    property int lastSelectedIndex: -1
    property string selectedPreset: ""
    property real sharedShimmerPhase: 0
    property bool highLoadMode: backend ? backend.queueCount > 50 || (backend.autoTuneEnabled && !!backend.systemProfile.result.recommendation && backend.systemProfile.result.recommendation.low_resource_mode) : false
    property int _langVersion: 0
    property string quickConvertPath: ""
    property string quickConvertName: ""
    property string quickConvertMediaType: "video"
    property string quickConvertFormat: ""
    property int activeNavIndex: 0
    property string pendingSettingsTarget: "core"
    property var navigationHistory: [{ page: 0, target: "", nav: 0 }]
    property int navigationCursor: 0
    readonly property bool canNavigateBack: navigationCursor > 0
    readonly property bool canNavigateForward: navigationCursor < navigationHistory.length - 1

    function currentSectionTitle() {
        if (activeSection === 0) return workspaceTitle()
        if (activeNavIndex >= 0 && activeNavIndex < navigationItems.length)
            return I18n.t(navigationItems[activeNavIndex].title)
        return I18n.t("settings")
    }

    function navigateHistory(direction) {
        var next = navigationCursor + direction
        if (next < 0 || next >= navigationHistory.length) return
        navigationCursor = next
        var item = navigationHistory[next]
        showSection(item.page, item.target, item.nav)
    }

    function showSection(pageIndex, target, navIndex) {
        activeSection = pageIndex
        activeNavIndex = navIndex >= 0 ? navIndex : navIndexFor(pageIndex, target)
        if (pageIndex === 5) {
            pendingSettingsTarget = target || "core"
            settingsScrollTargetTimer.restart()
        }
    }
    property var navigationItems: [
        { title: "nav_queue", icon: "queue", tint: "#007AFF", page: 0, target: "", group: "nav_workspace", primary: true },
        { title: "nav_montage", icon: "film", tint: "#AF52DE", page: 0, target: "montage", group: "nav_workspace" },
        { title: "nav_telegram_note", icon: "telegram", tint: "#2AABEE", page: 6, target: "", group: "nav_workspace" },
        { title: "nav_archive", icon: "archive", tint: "#FF9500", page: 7, target: "", group: "nav_workspace", primary: true },
        { title: "nav_downloads", icon: "download", tint: "#34C759", page: 4, target: "", group: "nav_workspace", primary: true },
        { title: "nav_presets", icon: "sliders", tint: "#AF52DE", page: 2, target: "", group: "nav_workspace" },
        { title: "nav_analytics", icon: "chart", tint: "#FF9500", page: 1, target: "", group: "nav_workspace" },
        { title: "nav_core", icon: "settings", tint: "#8E8E93", page: 5, target: "core", group: "nav_conversion", primary: true },
        { title: "nav_output", icon: "folder", tint: "#007AFF", page: 5, target: "output", group: "nav_conversion", primary: true },
        { title: "nav_video", icon: "video", tint: "#AF52DE", page: 5, target: "video", group: "nav_conversion" },
        { title: "nav_audio_subtitles", icon: "audio", tint: "#FF2D55", page: 5, target: "audio_subtitles", group: "nav_conversion" },
        { title: "nav_images_sheets", icon: "image", tint: "#34C759", page: 5, target: "images_sheets", group: "nav_conversion" },
        { title: "nav_watermark_text", icon: "text", tint: "#32ADE6", page: 5, target: "watermark_text", group: "nav_conversion" },
        { title: "nav_smart_convert", icon: "sparkles", tint: "#AF52DE", page: 5, target: "smart_convert", group: "nav_advanced" },
        { title: "nav_video_editor", icon: "crop", tint: "#FF9500", page: 5, target: "video_editor", group: "nav_advanced" },
        { title: "nav_subtitle_tools", icon: "subtitle", tint: "#007AFF", page: 5, target: "subtitle_tools", group: "nav_advanced" },
        { title: "nav_privacy_security", icon: "lock", tint: "#007AFF", page: 5, target: "privacy_security", group: "nav_advanced" },
        { title: "nav_ffmpeg", icon: "settings", tint: "#8E8E93", page: 3, target: "", group: "nav_automation" },
        { title: "nav_ffmpeg_watch", icon: "clock", tint: "#5856D6", page: 5, target: "ffmpeg_watch", group: "nav_automation" },
        { title: "nav_cloud_integration", icon: "cloud", tint: "#32ADE6", page: 5, target: "cloud_integration", group: "nav_automation" },
        { title: "nav_metadata_hooks", icon: "file", tint: "#8E8E93", page: 5, target: "metadata_hooks", group: "nav_automation" },
        { title: "nav_app_update", icon: "refresh", tint: "#007AFF", page: 5, target: "app_update", group: "nav_application" },
        { title: "nav_commercial_license", icon: "key", tint: "#FF9500", page: 5, target: "commercial_license", group: "nav_application" }
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
    property var hwOptions: ["auto", "cpu", "Apple (VideoToolbox)", "NVIDIA (NVENC)", "Intel (QSV)", "AMD (AMF)", "Linux (VA-API)"]
    property var performanceProfiles: ["Quality", "Balanced", "Fast", "Small file"]
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
        running: root.visible && root.active && !root.highLoadMode && backend && backend.isRunning
    }

    property alias settingsHistory: settingsHistory
    readonly property var watchedSettings: settingsPanel ? settingsPanel.collectSettings() : ({})
    onWatchedSettingsChanged: settingsHistory.schedule()
    UndoHistory {
        id: settingsHistory
        objectName: "settingsUndoHistory"
        capture: function() { return root.collectSettings() }
        restore: function(state) { settingsPanel.applyPreset(state) }
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

    function fieldError(name) {
        return validationResult && validationResult.errors && validationResult.errors[name]
            ? String(validationResult.errors[name]) : ""
    }

    function startIfValid() {
        if (!backend)
            return
        if (!backend.ensureOutputDirSelected())
            return
        if (!validateForm())
            return
        var settings = collectSettings()
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
        return I18n.t("nav_queue")
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

    function openArchive() {
        root.openSidebarSection(7, "", root.navIndexFor(7, ""))
    }

    function checkSourceUpdate() {
        sourceUpdateDialog.open()
        if (backend)
            backend.checkSourceUpdate()
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
        refreshSelectedDetails()
        root.selectedTextPreview = backend && root.selectedMediaType === "text" ? backend.readTextPreview(root.selectedPath) : ""
        var preferred = root.selectedPreviewFormat || currentFormatFor(root.quickConvertMediaType)
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
        index = backend ? backend.queueIndexForPath(path) : index
        var ctrl = (modifiers & (Qt.ControlModifier | Qt.MetaModifier)) !== 0
        var shift = (modifiers & Qt.ShiftModifier) !== 0
        if (shift && backend && lastSelectedIndex >= 0) {
            var visiblePaths = backend.visibleQueuePaths
            var anchor = visiblePaths.indexOf(backend.queuePathAt(lastSelectedIndex))
            var clicked = visiblePaths.indexOf(path)
            next = anchor >= 0 && clicked >= 0 ? visiblePaths.slice(Math.min(anchor, clicked), Math.max(anchor, clicked) + 1) : [path]
        } else if (ctrl) {
            var existing = next.indexOf(path)
            if (existing >= 0)
                next.splice(existing, 1)
            else
                next.push(path)
        } else {
            next = [path]
        }
        if (next.length === 0) { clearQueueSelection(); return }
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
        refreshSelectedDetails()
        root.selectedTextPreview = backend && selectedMediaType === "text" ? backend.readTextPreview(path) : ""
    }

    function clearQueueSelection() {
        root.selectedDetails = ({})
        root.selectedTextPreview = ""
        root.selectedPaths = []
        root.selectedPath = ""
        root.selectedName = ""
        root.selectedMediaType = ""
        root.selectedThumbnailSource = ""
        root.selectedPreviewFormat = ""
        root.selectedIndex = -1
        root.lastSelectedIndex = -1
        if (backend)
            backend.selectQueueIndex(-1)
    }

    function removeQueuePath(path) {
        if (!path || !backend)
            return
        backend.removeTaskPath(path)
        if (root.selectedPaths.indexOf(path) >= 0) {
            var next = root.selectedPaths.slice()
            next.splice(next.indexOf(path), 1)
            root.selectedPaths = next
        }
        if (root.selectedPath === path)
            root.clearQueueSelection()
    }

    function removeSelectedPaths() {
        if (!backend || root.selectedPaths.length === 0)
            return
        backend.removeSelectedPaths(root.selectedPaths)
        root.clearQueueSelection()
    }

    function convertSelectedPaths() {
        if (!backend || root.selectedPaths.length === 0 || backend.isRunning)
            return
        if (!backend.ensureOutputDirSelected() || !validateForm())
            return
        backend.startConversionForPaths(root.selectedPaths, collectSettings())
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
        if (target === "montage") {
            openMontageEditor("")
            return
        }
        var resolvedNav = navIndex >= 0 ? navIndex : navIndexFor(pageIndex, target)
        var current = navigationHistory[navigationCursor]
        if (!current || current.page !== pageIndex || current.target !== target) {
            var history = navigationHistory.slice(0, navigationCursor + 1)
            history.push({ page: pageIndex, target: target, nav: resolvedNav })
            if (history.length > 50) history.shift()
            navigationHistory = history
            navigationCursor = history.length - 1
        }
        showSection(pageIndex, target, resolvedNav)
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
        } else if (mode === "montage") {
            openMontageEditor("")
        } else if (mode === "downloads") {
            openSidebarSection(4, "", navIndexFor(4, ""))
        } else if (mode === "analytics") {
            openSidebarSection(1, "", navIndexFor(1, ""))
        }
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
            return montageEditorDialog.visible
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
        var needle = globalSearchText.trim().toLowerCase()
        var sections = needle.length < 2 ? [] : navigationItems.filter(function(item) {
            return (I18n.t(item.title) + " " + (item.target || "")).toLowerCase().indexOf(needle) >= 0
        }).map(function(item) {
            return { kind: I18n.t(item.group), title: I18n.t(item.title), detail: I18n.t(item.group), page: item.page, target: item.target }
        })
        globalSearchResults = sections.concat(backend ? backend.globalSearch(globalSearchText) : [])
        globalSearchIndex = 0
        if (needle.length >= 2 && globalSearchResults.length > 0)
            globalSearchPopup.open()
        else
            globalSearchPopup.close()
    }

    function activateSearchResult(result) {
        if (!result)
            return
        openSidebarSection(Number(result.page || 0), String(result.target || ""), -1)
        globalSearchText = ""
        if (appSidebar && appSidebar.searchField)
            appSidebar.searchField.clear()
        globalSearchPopup.close()
    }

    function moveGlobalSearchSelection(delta) {
        if (!globalSearchResults.length)
            return
        globalSearchIndex = (globalSearchIndex + delta + globalSearchResults.length) % globalSearchResults.length
        globalSearchPopup.open()
    }

    function activateSelectedSearchResult() {
        if (globalSearchResults.length)
            activateSearchResult(globalSearchResults[globalSearchIndex])
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

    function openNotifications() {
        notificationCenterPopup.open()
    }

    Timer {
        id: settingsSyncTimer
        interval: 260
        repeat: false
        onTriggered: {
            validateForm()
            if (backend)
                backend.refreshOutputPreview(collectSettings())
            root.refreshSelectedDetails()
        }
    }

    Timer {
        id: settingsScrollTargetTimer
        interval: 40
        repeat: false
        onTriggered: {
            if (settingsPanel && settingsScroll && root.activeSection === 5)
                settingsScroll.contentItem.contentY = 0
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
        function onAutoProfileReady(data) {
            settingsHistory.flush()
            settingsHistory.restoring = true
            settingsPanel.applyWorkload(data)
            settingsHistory.rebase({concurrency_limit: data.concurrency_limit,
                cpu_load_limit: data.cpu_load_limit, gpu_load_limit: data.gpu_load_limit})
            settingsHistory.restoring = false
        }
        function onPresetLoaded(data) { applyPreset(data) }
        function onQueueFilterChanged() { root.retainVisibleSelection() }
        function onSelectedDetailsChanged() { root.refreshSelectedDetails() }
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
            root.refreshSelectedDetails()
        }
        function onToastRequested(message) {
            root.showToast(message)
        }
        function onThemeChanged() { root._langVersion += 1 }
    }

    Component.onCompleted: {
        if (backend) {
            var geom = backend.optimalWindowGeometry()
            if (geom) {
                if (geom.width && geom.width >= root.minimumWidth) root.width = geom.width
                if (geom.height && geom.height >= root.minimumHeight) root.height = geom.height
                if (geom.x !== undefined && geom.x >= 0) root.x = geom.x
                if (geom.y !== undefined && geom.y >= 0) root.y = geom.y
            }
            if (backend.autoDisplayAdaptation) {
                backend.applyDisplayAdaptation()
                if (backend.displayMetrics && backend.displayMetrics.recommendedSidebarCollapsed) {
                    root.sidebarCollapsed = true
                }
            }
            I18n.language = backend.uiLanguage
            backend.setupSystemTray()
            backend.restoreSession()
            backend.refreshEncoders()
            backend.startSystemScan()
            scheduleSettingsSync()
            syncQueueFilter()
            Qt.callLater(function() { settingsHistory.reset() })
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppLayout.AppTitleBar {
            id: appHeader
            Layout.fillWidth: true
            appRoot: root
            logoSource: root.appLogoSource
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderMuted }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            SidebarPanel {
                id: appSidebar
                appRoot: root
                Layout.fillHeight: true
                collapsed: root.sidebarCollapsed
                activeIndex: root.activeNavIndex
                navigationItems: root.navigationItems
                onSectionRequested: function(pageIndex, target, navIndex) { root.openSidebarSection(pageIndex, target, navIndex) }
                onAddFilesRequested: root.addFilesForWorkspace()
                onAddFolderRequested: root.addFolderForWorkspace()
                onArchiveRequested: root.openArchive()
                onUpdateRequested: root.checkSourceUpdate()
                onDedupeRequested: backend && backend.deduplicateQueueByHash()
            }

            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.borderMuted }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: root.activeSection

                AppScreens.QueueScreen { id: queueScreen; appRoot: root }
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
                        spacing: Theme.space5
                        Item { Layout.preferredHeight: Theme.space2 }
                        SettingsPanel {
                    controller: root
                            id: settingsPanel
                            objectName: "settingsPages"
                            Layout.fillWidth: true
                            Layout.maximumWidth: 1000
                            Layout.alignment: Qt.AlignHCenter
                            Layout.leftMargin: Theme.space5
                            Layout.rightMargin: Theme.space5
                        }
                        Item { Layout.preferredHeight: Theme.space5 }

                    }
                }
                AppScreens.TelegramNoteScreen { id: telegramNoteScreen; appRoot: root }
                AppScreens.ArchiveScreen {
                    id: archiveScreen
                    objectName: "archiveScreen"
                    appRoot: root
                }
            }
        }

        AppLayout.BottomActionBar {
            Layout.fillWidth: true
            appRoot: root
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
        focus: false
        width: appSidebar && appSidebar.searchField
            ? Math.min(360, appSidebar.searchField.width)
            : Math.min(360, root.width - 24)
        height: Math.min(260, Math.max(68, root.globalSearchResults.length * 58 + 16), Math.max(0, root.height - y - 12))
        x: Math.max(12, Math.min(root.width - width - 12, appSidebar.searchField.mapToItem(root.contentItem, 0, 0).x))
        y: appSidebar.searchField.mapToItem(root.contentItem, 0, appSidebar.searchField.height + 8).y
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
                    color: parent.hovered || index === root.globalSearchIndex ? Theme.overlayHover : Theme.transparent
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
        y: appHeader.height + 10
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
        Overlay.modal: Rectangle { color: Theme.modalScrim }
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
                    text: I18n.t("close")
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

            PresetManagerPanel {
                service: backend
                settingsProvider: function() { return root.collectSettings() }
                onPresetSelected: function(name) { root.selectedPreset = name }
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
                    SecondaryButton { iconName: "folder"; text: I18n.t("choose"); onClicked: backend && backend.pickFfmpeg() }
                    SecondaryButton { iconName: "refresh"; text: I18n.t("refresh"); onClicked: backend && backend.refreshEncoders() }
                    SecondaryButton { iconName: "download"; text: I18n.t("update_ffmpeg"); onClicked: backend && backend.updateFfmpeg() }
                }
                Label { Layout.fillWidth: true; text: backend ? backend.encoderInfo : ""; color: Theme.textMuted; wrapMode: Text.WordWrap; font.pixelSize: Theme.fontMeta }
                AppTextField { id: ffmpegScreenWatchField; text: backend ? backend.watchFolder : ""; placeholderText: I18n.t("watch_folder"); onEditingFinished: { if (backend) backend.watchFolder = text } }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton { iconName: "folder"; text: I18n.t("choose"); onClicked: backend && backend.pickWatchFolder() }
                    SecondaryButton { text: backend && backend.watchRunning ? I18n.t("stop_watch") : I18n.t("start_watch"); onClicked: backend && (backend.watchRunning ? backend.stopWatching() : backend.startWatching()) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    SecondaryButton { iconName: "download"; text: I18n.t("import"); onClicked: backend && backend.importProject() }
                    SecondaryButton { iconName: "share"; text: I18n.t("export"); onClicked: backend && backend.exportProject(collectSettings()) }
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
            visible: String(youtubeUrlField.text).trim().length > 0 || (backend && backend.youtubeDownloadHistory.length > 0)
            Layout.fillWidth: true
            spacing: 8
            AppButton {
                id: youtubeVideoSegment
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                text: I18n.t("video")
                iconName: "film"
                highlighted: selectedDownloadMode === "video"
                font.pixelSize: Theme.fontSizeLg
                hoverEnabled: true
                onClicked: selectedDownloadMode = "video"
            }
            AppButton {
                id: youtubeAudioSegment
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                text: I18n.t("audio_only")
                iconName: "music"
                highlighted: selectedDownloadMode === "audio"
                font.pixelSize: Theme.fontSizeLg
                hoverEnabled: true
                onClicked: selectedDownloadMode = "audio"
            }
        }

        RowLayout {
            visible: backend && backend.youtubeDownloadHistory.length > 0
            Layout.fillWidth: true
            AppComboBox {
                id: youtubeHistoryCombo
                Layout.fillWidth: true
                model: backend ? backend.youtubeDownloadHistory : []
                enabled: backend ? backend.youtubeDownloadHistory.length > 0 : false
                onActivated: youtubeUrlField.text = currentText
            }
            SecondaryButton {
                iconName: "trash"; text: I18n.t("clear")
                enabled: backend ? backend.youtubeDownloadHistory.length > 0 : false
                onClicked: backend && backend.clearYoutubeHistory()
            }
        }
        RowLayout {
            visible: String(youtubeUrlField.text).trim().length > 0 || (backend && backend.youtubeDownloadHistory.length > 0)
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
        Label {
            visible: String(youtubeUrlField.text).trim().length === 0
            Layout.fillWidth: true
            text: I18n.t("youtube_empty_prompt")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSizeSm
            wrapMode: Text.WordWrap
        }
        GridLayout {
            visible: String(youtubeUrlField.text).trim().length > 0
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
            visible: String(youtubeUrlField.text).trim().length > 0
            Layout.fillWidth: true
            text: backend ? backend.youtubeCookiesStatus : "Cookies: --"
            color: backend && backend.youtubeCookiesStatus.indexOf("Cookies: підключено") >= 0 ? Theme.statusSuccess : Theme.textMuted
            font.pixelSize: Theme.fontMeta
            elide: Text.ElideRight
        }
        RowLayout {
            visible: String(youtubeUrlField.text).trim().length > 0
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
                text: backend ? backend.youtubePlaylistPreview : ""
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
                        text: backend ? String(backend.youtubePreviewInfo.hint || "") : ""
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
                text: I18n.t("add_to_queue")
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
                    text: I18n.t("download_queue")
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



    Dialog {
        id: sourceUpdateDialog
        objectName: "sourceUpdateDialog"
        parent: Overlay.overlay
        modal: true
        focus: true
        width: Math.min(520, root.width - Theme.space6 * 2)
        title: "Оновлення застосунку"
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Theme.panelBackground
            radius: Theme.radiusMd
            border.width: 1
            border.color: Theme.borderDefault
        }

        contentItem: ColumnLayout {
            spacing: Theme.space3

            Label {
                Layout.fillWidth: true
                text: backend && backend.sourceUpdateRestartRequired
                    ? "Оновлення вже завантажено"
                    : backend && backend.sourceUpdateAvailable
                        ? "Доступна нова версія з гілки main"
                        : "Перевірка оновлень"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSizeMd
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: backend && backend.sourceUpdateChecking
                visible: running
            }
            Label {
                Layout.fillWidth: true
                text: backend ? backend.sourceUpdateStatus : "Підключення до GitHub…"
                color: Theme.textSecondary
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
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space2
                Item { Layout.fillWidth: true }
                SecondaryButton {
                    text: I18n.t("cancel")
                    visible: !(backend && backend.sourceUpdateRestartRequired)
                    enabled: !(backend && backend.sourceUpdateChecking)
                    onClicked: sourceUpdateDialog.close()
                }
                PrimaryButton {
                    text: "Оновити"
                    visible: backend && backend.sourceUpdateAvailable
                    enabled: backend && !backend.sourceUpdateChecking
                    onClicked: backend.applySourceUpdate()
                }
                PrimaryButton {
                    text: "Перезапустити"
                    visible: backend && backend.sourceUpdateRestartRequired
                    onClicked: backend.restartAfterSourceUpdate()
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

    ShortcutCheatSheetModal {
        id: shortcutCheatSheet
    }

    MontageEditorDialog {
        id: montageEditorDialog
        objectName: "montageEditorDialog"
        transientParent: root
    }

    function openMontageEditor(path) {
        var target = path || ""
        if (!target && root.selectedPath && (root.selectedMediaType === "video" || root.selectedMediaType === "image")) {
            target = root.selectedPath
        }
        if (!target && root.selectedPath) {
            target = root.selectedPath
        }
        if (!target && backend && backend.visibleQueuePaths && backend.visibleQueuePaths.length > 0) {
            for (var i = 0; i < backend.visibleQueuePaths.length; ++i) {
                var candidate = String(backend.visibleQueuePaths[i])
                var ext = candidate.slice(candidate.lastIndexOf(".")).toLowerCase()
                if ([".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".ts", ".m2ts",
                     ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"].indexOf(ext) >= 0) {
                    target = candidate
                    break
                }
            }
            if (!target) target = String(backend.visibleQueuePaths[0])
        }
        if (!target && backend) {
            target = backend.pickVideoFile()
        }
        montageEditorDialog.openForFile(target || "")
    }


    function shortcutAllowed(action) {
        var editing = root.activeFocusItem && (root.activeFocusItem.selectByMouse !== undefined || root.activeFocusItem.inputMethodHints !== undefined)
        if (editing && ["select_all", "paste_paths", "remove_selected", "clear_queue", "deduplicate", "move_up", "move_down"].indexOf(action) >= 0)
            return false
        return true
    }

    function runShortcut(action) {
        if (!backend)
            return
        if (action === "start_conversion") startIfValid()
        else if (action === "stop_conversion") backend.stopConversion()
        else if (action === "pause_resume") { if (backend.isRunning) backend.isPaused ? backend.resumeConversion() : backend.pauseConversion() }
        else if (action === "skip_file") backend.skipCurrentFile()
        else if (action === "retry_failed") backend.retryFailed()
        else if (action === "add_files") addFilesForWorkspace()
        else if (action === "add_folder") addFolderForWorkspace()
        else if (action === "remove_selected") removeSelectedPaths()
        else if (action === "select_all") root.selectedPaths = backend.visibleQueuePaths.slice()
        else if (action === "clear_queue") { backend.clearQueue(); clearQueueSelection() }
        else if (action === "deduplicate") backend.deduplicateQueueByHash()
        else if (action === "move_up") backend.moveSelectedPathsUp(root.selectedPaths)
        else if (action === "move_down") backend.moveSelectedPathsDown(root.selectedPaths)
        else if (action === "queue_search") { root.openSidebarSection(0, "", 0); queueScreen.focusSearch() }
        else if (action === "toggle_sidebar") root.sidebarCollapsed = !root.sidebarCollapsed
        else if (action === "save_preset") backend.savePreset(root.selectedPreset || "Custom", collectSettings())
        else if (action === "export_project") backend.exportProject(collectSettings())
        else if (action === "import_project") backend.importProject()
        else if (action === "export_log") backend.exportLog()
        else if (action === "open_output_dir") backend.openOutputDir()
        else if (action === "toggle_beginner_mode") backend.beginnerMode = !backend.beginnerMode
        else if (action === "paste_paths") backend.pasteFromClipboard()
        else {
            var pages = { nav_queue: 0, nav_analytics: 1, nav_presets: 2, nav_ffmpeg: 3, nav_youtube: 4, nav_settings: 5, nav_telegram_note: 6 }
            if (pages[action] !== undefined) openSidebarSection(pages[action], "", -1)
        }
    }

    Instantiator {
        model: backend ? backend.allShortcuts : []
        delegate: Shortcut {
            required property var modelData
            sequence: modelData.key
            enabled: root.shortcutAllowed(modelData.action) && sequence.toString().length > 0
            onActivated: root.runShortcut(modelData.action)
        }
    }

    Shortcut {
        sequence: "?"
        onActivated: shortcutCheatSheet.open()
    }

    Shortcut {
        sequence: "F1"
        onActivated: shortcutCheatSheet.open()
    }
}
