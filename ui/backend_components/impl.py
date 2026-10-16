from __future__ import annotations

from PySide6 import QtCore

from .conversion_controls import ConversionControlsMixin
from .core import CoreMixin
from .downloads import DownloadsMixin
from .event_loop import EventLoopMixin
from .ffmpeg_paths import FfmpegPathsMixin
from .general_properties import GeneralPropertiesMixin
from .media_details import MediaDetailsMixin
from .queue_actions import QueueActionsMixin
from .queue_io import QueueIoMixin
from .queue_view import QueueViewMixin
from .setup import SetupMixin
from .theme_preferences import ThemePreferencesMixin
from .ui_preferences import UiPreferencesMixin


class Backend(
    CoreMixin,
    SetupMixin,
    GeneralPropertiesMixin,
    UiPreferencesMixin,
    ThemePreferencesMixin,
    QueueIoMixin,
    FfmpegPathsMixin,
    DownloadsMixin,
    QueueActionsMixin,
    MediaDetailsMixin,
    ConversionControlsMixin,
    QueueViewMixin,
    EventLoopMixin,
    QtCore.QObject,
):
    """QObject facade with ordinary feature mixins and an explicit Qt interface."""

    builtinPresetNames = GeneralPropertiesMixin.builtinPresetNames
    customPresetNames = GeneralPropertiesMixin.customPresetNames
    exportDiagnostics = QueueIoMixin.exportDiagnostics
    clearMediaCache = QueueIoMixin.clearMediaCache
    shutdown = CoreMixin.shutdown
    getWhisperModels = CoreMixin.getWhisperModels
    getWhisperDevices = CoreMixin.getWhisperDevices
    whisperEngineInstalled = CoreMixin.whisperEngineInstalled
    getWhisperEngine = CoreMixin.getWhisperEngine
    downloadWhisperModel = CoreMixin.downloadWhisperModel
    cancelWhisperDownload = CoreMixin.cancelWhisperDownload
    deleteWhisperModel = CoreMixin.deleteWhisperModel
    editorProject = SetupMixin.editorProject
    editorRender = SetupMixin.editorRender
    montageEditing = SetupMixin.montageEditing
    telegramNote = SetupMixin.telegramNote
    archive = SetupMixin.archive
    autoDependencySetup = SetupMixin.autoDependencySetup
    startDependencySetup = SetupMixin.startDependencySetup
    retryDependencySetup = SetupMixin.retryDependencySetup
    systemProfile = SetupMixin.systemProfile
    autoTuneEnabled = SetupMixin.autoTuneEnabled
    startSystemScan = SetupMixin.startSystemScan
    _apply_system_profile = SetupMixin._apply_system_profile
    autoTunePending = SetupMixin.autoTunePending
    _apply_pending_profile = SetupMixin._apply_pending_profile
    whisperSetup = SetupMixin.whisperSetup
    pickWhisperTestMedia = SetupMixin.pickWhisperTestMedia
    appTitle = GeneralPropertiesMixin.appTitle
    appVersion = GeneralPropertiesMixin.appVersion
    queueModel = GeneralPropertiesMixin.queueModel
    logModel = GeneralPropertiesMixin.logModel
    historyModel = GeneralPropertiesMixin.historyModel
    presetsModel = GeneralPropertiesMixin.presetsModel
    recentFoldersModel = GeneralPropertiesMixin.recentFoldersModel
    ffmpegPath = GeneralPropertiesMixin.ffmpegPath
    outputDir = GeneralPropertiesMixin.outputDir
    outputDirConfigured = GeneralPropertiesMixin.outputDirConfigured
    watchFolder = GeneralPropertiesMixin.watchFolder
    watchRunning = GeneralPropertiesMixin.watchRunning
    onboardingVisible = GeneralPropertiesMixin.onboardingVisible
    isWhisperAvailable = GeneralPropertiesMixin.isWhisperAvailable
    uiLanguage = GeneralPropertiesMixin.uiLanguage
    currentLanguage = GeneralPropertiesMixin.currentLanguage
    availableLanguages = GeneralPropertiesMixin.availableLanguages
    setLanguage = GeneralPropertiesMixin.setLanguage
    tr = GeneralPropertiesMixin.tr
    encoderInfo = GeneralPropertiesMixin.encoderInfo
    statusText = GeneralPropertiesMixin.statusText
    fileProgress = GeneralPropertiesMixin.fileProgress
    totalProgress = GeneralPropertiesMixin.totalProgress
    fileProgressText = GeneralPropertiesMixin.fileProgressText
    totalProgressText = GeneralPropertiesMixin.totalProgressText
    youtubeDownloadRunning = GeneralPropertiesMixin.youtubeDownloadRunning
    youtubeDownloadProgress = GeneralPropertiesMixin.youtubeDownloadProgress
    youtubeDownloadStatus = GeneralPropertiesMixin.youtubeDownloadStatus
    youtubeDownloadHistory = GeneralPropertiesMixin.youtubeDownloadHistory
    youtubeCookiesPath = GeneralPropertiesMixin.youtubeCookiesPath
    isRunning = GeneralPropertiesMixin.isRunning
    isPaused = GeneralPropertiesMixin.isPaused
    infoName = GeneralPropertiesMixin.infoName
    infoDuration = GeneralPropertiesMixin.infoDuration
    infoCodec = GeneralPropertiesMixin.infoCodec
    infoRes = GeneralPropertiesMixin.infoRes
    infoSize = GeneralPropertiesMixin.infoSize
    infoContainer = GeneralPropertiesMixin.infoContainer
    infoAnalysis = GeneralPropertiesMixin.infoAnalysis
    infoWarnings = GeneralPropertiesMixin.infoWarnings
    outputPreviewText = GeneralPropertiesMixin.outputPreviewText
    selectedPreviewSource = GeneralPropertiesMixin.selectedPreviewSource
    selectedPreviewOutput = GeneralPropertiesMixin.selectedPreviewOutput
    selectedPreviewCommand = GeneralPropertiesMixin.selectedPreviewCommand
    historyText = GeneralPropertiesMixin.historyText
    queueCount = GeneralPropertiesMixin.queueCount
    completedCount = GeneralPropertiesMixin.completedCount
    failedCount = GeneralPropertiesMixin.failedCount
    skippedCount = GeneralPropertiesMixin.skippedCount
    runningCount = GeneralPropertiesMixin.runningCount
    cancelledCount = GeneralPropertiesMixin.cancelledCount
    speedHistory = GeneralPropertiesMixin.speedHistory
    fileTimings = GeneralPropertiesMixin.fileTimings
    codecDistribution = GeneralPropertiesMixin.codecDistribution
    resourceHistory = GeneralPropertiesMixin.resourceHistory
    cpuLoadText = GeneralPropertiesMixin.cpuLoadText
    gpuLoadText = GeneralPropertiesMixin.gpuLoadText
    ramLoadText = GeneralPropertiesMixin.ramLoadText
    sessionElapsedText = GeneralPropertiesMixin.sessionElapsedText
    sessionEtaText = GeneralPropertiesMixin.sessionEtaText
    sessionAvgSpeedText = GeneralPropertiesMixin.sessionAvgSpeedText
    sessionInputText = GeneralPropertiesMixin.sessionInputText
    sessionOutputText = GeneralPropertiesMixin.sessionOutputText
    sessionSavedText = GeneralPropertiesMixin.sessionSavedText
    youtubeDownloadQueue = GeneralPropertiesMixin.youtubeDownloadQueue
    youtubeCookiesStatus = GeneralPropertiesMixin.youtubeCookiesStatus
    youtubePlaylistPreview = GeneralPropertiesMixin.youtubePlaylistPreview
    youtubePreviewInfo = GeneralPropertiesMixin.youtubePreviewInfo
    youtubeDownloadLog = GeneralPropertiesMixin.youtubeDownloadLog
    ytdlpUpdateRunning = GeneralPropertiesMixin.ytdlpUpdateRunning
    preflightOk = GeneralPropertiesMixin.preflightOk
    preflightSummary = GeneralPropertiesMixin.preflightSummary
    preflightErrors = GeneralPropertiesMixin.preflightErrors
    preflightWarnings = GeneralPropertiesMixin.preflightWarnings
    accentColor = UiPreferencesMixin.accentColor
    themeMode = UiPreferencesMixin.themeMode
    effectiveThemeMode = UiPreferencesMixin.effectiveThemeMode
    queueViewMode = UiPreferencesMixin.queueViewMode
    concurrencyLimit = UiPreferencesMixin.concurrencyLimit
    outputTemplate = UiPreferencesMixin.outputTemplate
    formatTrimSeconds = UiPreferencesMixin.formatTrimSeconds
    layoutMode = UiPreferencesMixin.layoutMode
    fontScale = UiPreferencesMixin.fontScale
    beginnerMode = UiPreferencesMixin.beginnerMode
    accentPresets = UiPreferencesMixin.accentPresets
    layoutConfig = UiPreferencesMixin.layoutConfig
    detectOsDarkMode = UiPreferencesMixin.detectOsDarkMode
    autoDetectTheme = UiPreferencesMixin.autoDetectTheme
    importTheme = UiPreferencesMixin.importTheme
    exportTheme = UiPreferencesMixin.exportTheme
    hasLastError = UiPreferencesMixin.hasLastError
    lastErrorTitle = UiPreferencesMixin.lastErrorTitle
    lastErrorDetails = UiPreferencesMixin.lastErrorDetails
    clearLastError = UiPreferencesMixin.clearLastError
    copyLastErrorLog = UiPreferencesMixin.copyLastErrorLog
    saveWindowState = UiPreferencesMixin.saveWindowState
    loadWindowState = UiPreferencesMixin.loadWindowState
    displayMetrics = UiPreferencesMixin.displayMetrics
    autoDisplayAdaptation = UiPreferencesMixin.autoDisplayAdaptation
    applyDisplayAdaptation = UiPreferencesMixin.applyDisplayAdaptation
    optimalWindowGeometry = UiPreferencesMixin.optimalWindowGeometry
    validateWindowBounds = UiPreferencesMixin.validateWindowBounds
    allShortcuts = UiPreferencesMixin.allShortcuts
    shortcutsByCategory = UiPreferencesMixin.shortcutsByCategory
    shortcutKey = UiPreferencesMixin.shortcutKey
    globalSearch = UiPreferencesMixin.globalSearch
    setShortcutKey = UiPreferencesMixin.setShortcutKey
    resetShortcut = UiPreferencesMixin.resetShortcut
    resetAllShortcuts = UiPreferencesMixin.resetAllShortcuts
    trayEnabled = UiPreferencesMixin.trayEnabled
    pushNotificationsEnabled = UiPreferencesMixin.pushNotificationsEnabled
    watchAutoConvertEnabled = UiPreferencesMixin.watchAutoConvertEnabled
    watchRulesText = UiPreferencesMixin.watchRulesText
    schedulerEnabled = UiPreferencesMixin.schedulerEnabled
    schedulerMode = UiPreferencesMixin.schedulerMode
    schedulerTime = UiPreferencesMixin.schedulerTime
    schedulerCpuLimit = UiPreferencesMixin.schedulerCpuLimit
    schedulerGpuLimit = UiPreferencesMixin.schedulerGpuLimit
    completionAction = UiPreferencesMixin.completionAction
    webhookEnabled = UiPreferencesMixin.webhookEnabled
    webhookUrl = UiPreferencesMixin.webhookUrl
    discordWebhookUrl = UiPreferencesMixin.discordWebhookUrl
    telegramBotToken = UiPreferencesMixin.telegramBotToken
    telegramChatId = UiPreferencesMixin.telegramChatId
    resetWatchRules = UiPreferencesMixin.resetWatchRules
    previewWatchRules = UiPreferencesMixin.previewWatchRules
    licenseStatusText = UiPreferencesMixin.licenseStatusText
    licensePlan = UiPreferencesMixin.licensePlan
    licenseHolder = UiPreferencesMixin.licenseHolder
    licenseId = UiPreferencesMixin.licenseId
    licenseExpiresAt = UiPreferencesMixin.licenseExpiresAt
    licenseActive = UiPreferencesMixin.licenseActive
    trialActive = UiPreferencesMixin.trialActive
    trialRemainingText = UiPreferencesMixin.trialRemainingText
    proFeaturesEnabled = UiPreferencesMixin.proFeaturesEnabled
    commercialExportAllowed = UiPreferencesMixin.commercialExportAllowed
    licenseFeatures = UiPreferencesMixin.licenseFeatures
    activateLicenseKey = UiPreferencesMixin.activateLicenseKey
    loadOfflineLicenseFile = UiPreferencesMixin.loadOfflineLicenseFile
    startTrial = UiPreferencesMixin.startTrial
    clearLicense = UiPreferencesMixin.clearLicense
    paidAutoUpdateEnabled = UiPreferencesMixin.paidAutoUpdateEnabled
    paidUpdateManifestUrl = UiPreferencesMixin.paidUpdateManifestUrl
    paidUpdateStatus = UiPreferencesMixin.paidUpdateStatus
    paidUpdateAvailable = UiPreferencesMixin.paidUpdateAvailable
    checkPaidUpdate = UiPreferencesMixin.checkPaidUpdate
    openPaidUpdateDownload = UiPreferencesMixin.openPaidUpdateDownload
    setupSystemTray = UiPreferencesMixin.setupSystemTray
    sourceUpdateChecking = UiPreferencesMixin.sourceUpdateChecking
    sourceUpdateAvailable = UiPreferencesMixin.sourceUpdateAvailable
    sourceUpdateRestartRequired = UiPreferencesMixin.sourceUpdateRestartRequired
    sourceUpdateStatus = UiPreferencesMixin.sourceUpdateStatus
    sourceUpdateCurrentCommit = UiPreferencesMixin.sourceUpdateCurrentCommit
    sourceUpdateRemoteCommit = UiPreferencesMixin.sourceUpdateRemoteCommit
    checkSourceUpdate = UiPreferencesMixin.checkSourceUpdate
    applySourceUpdate = UiPreferencesMixin.applySourceUpdate
    restartAfterSourceUpdate = UiPreferencesMixin.restartAfterSourceUpdate
    platformName = ThemePreferencesMixin.platformName
    themePalette = ThemePreferencesMixin.themePalette
    themeColorOverrides = ThemePreferencesMixin.themeColorOverrides
    themeColorDefinitions = ThemePreferencesMixin.themeColorDefinitions
    savedThemeNames = ThemePreferencesMixin.savedThemeNames
    setThemeColor = ThemePreferencesMixin.setThemeColor
    resetThemeColor = ThemePreferencesMixin.resetThemeColor
    resetThemeColors = ThemePreferencesMixin.resetThemeColors
    saveNamedTheme = ThemePreferencesMixin.saveNamedTheme
    loadNamedTheme = ThemePreferencesMixin.loadNamedTheme
    deleteNamedTheme = ThemePreferencesMixin.deleteNamedTheme
    importThemeFile = ThemePreferencesMixin.importThemeFile
    exportThemeFile = ThemePreferencesMixin.exportThemeFile
    folderTypeFilter = QueueIoMixin.folderTypeFilter
    folderExcludePatterns = QueueIoMixin.folderExcludePatterns
    addFolderFiltered = QueueIoMixin.addFolderFiltered
    pasteFromClipboard = QueueIoMixin.pasteFromClipboard
    saveQueueToFile = QueueIoMixin.saveQueueToFile
    loadQueueFromFile = QueueIoMixin.loadQueueFromFile
    generateMediaPreview = QueueIoMixin.generateMediaPreview
    refreshEncoders = FfmpegPathsMixin.refreshEncoders
    updateFfmpeg = FfmpegPathsMixin.updateFfmpeg
    pickFfmpeg = FfmpegPathsMixin.pickFfmpeg
    pickOutputDir = FfmpegPathsMixin.pickOutputDir
    ensureOutputDirSelected = FfmpegPathsMixin.ensureOutputDirSelected
    dismissOnboarding = FfmpegPathsMixin.dismissOnboarding
    useRecentFolder = FfmpegPathsMixin.useRecentFolder
    openOutputDir = FfmpegPathsMixin.openOutputDir
    openSourcePath = FfmpegPathsMixin.openSourcePath
    openOutputForPath = FfmpegPathsMixin.openOutputForPath
    copyLogLine = FfmpegPathsMixin.copyLogLine
    clearLog = FfmpegPathsMixin.clearLog
    openPathFromText = FfmpegPathsMixin.openPathFromText
    addFiles = DownloadsMixin.addFiles
    addFilesForType = DownloadsMixin.addFilesForType
    addDroppedUrls = DownloadsMixin.addDroppedUrls
    addFolder = DownloadsMixin.addFolder
    downloadYoutube = DownloadsMixin.downloadYoutube
    downloadYoutubeAdvanced = DownloadsMixin.downloadYoutubeAdvanced
    importDownloadUrlsFromFile = DownloadsMixin.importDownloadUrlsFromFile
    importDownloadUrlsFromFilePath = DownloadsMixin.importDownloadUrlsFromFilePath
    addDroppedDownloadUrls = DownloadsMixin.addDroppedDownloadUrls
    cancelYoutubeDownload = DownloadsMixin.cancelYoutubeDownload
    retryYoutubeDownload = DownloadsMixin.retryYoutubeDownload
    retryFailedYoutubeDownloads = DownloadsMixin.retryFailedYoutubeDownloads
    clearYoutubeDownloadLog = DownloadsMixin.clearYoutubeDownloadLog
    updateYtdlp = DownloadsMixin.updateYtdlp
    setYoutubeCookiesPath = DownloadsMixin.setYoutubeCookiesPath
    pickYoutubeCookies = DownloadsMixin.pickYoutubeCookies
    clearYoutubeHistory = DownloadsMixin.clearYoutubeHistory
    previewYoutubePlaylist = DownloadsMixin.previewYoutubePlaylist
    deduplicateQueue = QueueActionsMixin.deduplicateQueue
    deduplicateQueueByHash = QueueActionsMixin.deduplicateQueueByHash
    moveSelectedUp = QueueActionsMixin.moveSelectedUp
    moveSelectedDown = QueueActionsMixin.moveSelectedDown
    moveSelectedTop = QueueActionsMixin.moveSelectedTop
    moveSelectedBottom = QueueActionsMixin.moveSelectedBottom
    moveSelectedPathsUp = QueueActionsMixin.moveSelectedPathsUp
    moveSelectedPathsDown = QueueActionsMixin.moveSelectedPathsDown
    moveSelectedPathsTop = QueueActionsMixin.moveSelectedPathsTop
    moveSelectedPathsBottom = QueueActionsMixin.moveSelectedPathsBottom
    movePathToIndex = QueueActionsMixin.movePathToIndex
    removeSelected = QueueActionsMixin.removeSelected
    removeSelectedPaths = QueueActionsMixin.removeSelectedPaths
    removeTaskPath = QueueActionsMixin.removeTaskPath
    clearQueue = QueueActionsMixin.clearQueue
    exportLog = QueueActionsMixin.exportLog
    pickWatchFolder = QueueActionsMixin.pickWatchFolder
    startWatching = QueueActionsMixin.startWatching
    stopWatching = QueueActionsMixin.stopWatching
    selectQueueIndex = QueueActionsMixin.selectQueueIndex
    selectQueuePath = QueueActionsMixin.selectQueuePath
    queuePathAt = QueueActionsMixin.queuePathAt
    refreshPreflight = QueueActionsMixin.refreshPreflight
    cleanupQueue = QueueActionsMixin.cleanupQueue
    toggleTaskPinned = QueueActionsMixin.toggleTaskPinned
    setTaskPriority = QueueActionsMixin.setTaskPriority
    sortQueueByPriority = QueueActionsMixin.sortQueueByPriority
    pickWatermark = MediaDetailsMixin.pickWatermark
    pickCoverArt = MediaDetailsMixin.pickCoverArt
    pickAudioReplace = MediaDetailsMixin.pickAudioReplace
    pickFont = MediaDetailsMixin.pickFont
    pickSubtitle = MediaDetailsMixin.pickSubtitle
    pickVideoFile = MediaDetailsMixin.pickVideoFile
    pickMediaFile = MediaDetailsMixin.pickMediaFile
    readTextPreview = MediaDetailsMixin.readTextPreview
    targetSizeEstimate = MediaDetailsMixin.targetSizeEstimate
    validateSettings = MediaDetailsMixin.validateSettings
    refreshOutputPreview = MediaDetailsMixin.refreshOutputPreview
    renamePreviewRows = MediaDetailsMixin.renamePreviewRows
    copyRenamePreview = MediaDetailsMixin.copyRenamePreview
    exportRenamePreviewCsv = MediaDetailsMixin.exportRenamePreviewCsv
    restoreSession = MediaDetailsMixin.restoreSession
    exportProject = MediaDetailsMixin.exportProject
    importProject = MediaDetailsMixin.importProject
    exportCommandScript = MediaDetailsMixin.exportCommandScript
    copyDryRunCommand = MediaDetailsMixin.copyDryRunCommand
    clearHistory = MediaDetailsMixin.clearHistory
    exportHistoryReport = MediaDetailsMixin.exportHistoryReport
    openHistoryOutput = MediaDetailsMixin.openHistoryOutput
    loadHistorySettings = MediaDetailsMixin.loadHistorySettings
    rerunHistory = MediaDetailsMixin.rerunHistory
    getMontageSession = MediaDetailsMixin.getMontageSession
    requestMontageWaveform = MediaDetailsMixin.requestMontageWaveform
    saveMontageSession = MediaDetailsMixin.saveMontageSession
    applyMontageToTask = MediaDetailsMixin.applyMontageToTask
    requestMontageProxy = MediaDetailsMixin.requestMontageProxy
    isMontageProxyReady = MediaDetailsMixin.isMontageProxyReady
    getMontageProxyPath = MediaDetailsMixin.getMontageProxyPath
    getTimelineProject = MediaDetailsMixin.getTimelineProject
    saveTimelineProject = MediaDetailsMixin.saveTimelineProject
    renderTimelineProject = MediaDetailsMixin.renderTimelineProject
    diarizeMedia = MediaDetailsMixin.diarizeMedia
    applySpeakerAliases = MediaDetailsMixin.applySpeakerAliases
    exportDiarizedSubtitles = MediaDetailsMixin.exportDiarizedSubtitles
    generateStyledSubtitles = MediaDetailsMixin.generateStyledSubtitles
    translateSubtitles = MediaDetailsMixin.translateSubtitles
    calculateSmartReframe = MediaDetailsMixin.calculateSmartReframe
    trackAndBlurObject = MediaDetailsMixin.trackAndBlurObject
    startConversion = ConversionControlsMixin.startConversion
    startConversionForPath = ConversionControlsMixin.startConversionForPath
    startConversionForPaths = ConversionControlsMixin.startConversionForPaths
    retryFailed = ConversionControlsMixin.retryFailed
    retryTaskPath = ConversionControlsMixin.retryTaskPath
    stopConversion = ConversionControlsMixin.stopConversion
    pauseConversion = ConversionControlsMixin.pauseConversion
    resumeConversion = ConversionControlsMixin.resumeConversion
    skipCurrentFile = ConversionControlsMixin.skipCurrentFile
    skipTaskPath = ConversionControlsMixin.skipTaskPath
    loadPreset = ConversionControlsMixin.loadPreset
    savePreset = ConversionControlsMixin.savePreset
    importPresets = ConversionControlsMixin.importPresets
    exportPresets = ConversionControlsMixin.exportPresets
    deletePreset = ConversionControlsMixin.deletePreset
    saveTaskOverride = ConversionControlsMixin.saveTaskOverride
    saveTaskOverrideByPath = ConversionControlsMixin.saveTaskOverrideByPath
    updateTaskOverrideByPath = ConversionControlsMixin.updateTaskOverrideByPath
    saveBulkOverride = ConversionControlsMixin.saveBulkOverride
    clearTaskOverride = ConversionControlsMixin.clearTaskOverride
    clearTaskOverrideByPath = ConversionControlsMixin.clearTaskOverrideByPath
    filteredQueueModel = QueueViewMixin.filteredQueueModel
    visibleQueueCount = QueueViewMixin.visibleQueueCount
    visibleQueuePaths = QueueViewMixin.visibleQueuePaths
    setQueueFilter = QueueViewMixin.setQueueFilter
    queueIndexForPath = QueueViewMixin.queueIndexForPath
    queueItemDetails = QueueViewMixin.queueItemDetails
