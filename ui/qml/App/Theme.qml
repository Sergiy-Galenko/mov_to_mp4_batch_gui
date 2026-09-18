pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property bool reducedMotion: (typeof backend !== "undefined" && backend && backend.autoTuneEnabled
        && backend.systemProfile && backend.systemProfile.result.recommendation
        && backend.systemProfile.result.recommendation.low_resource_mode) || false
    readonly property string platformName: (typeof backend !== "undefined" && backend) ? backend.platformName : (Qt.platform.os === "osx" ? "macos" : Qt.platform.os)
    readonly property bool isMac: platformName === "macos"
    readonly property bool isWindows: platformName === "windows"
    readonly property color navigationSelection: isMac ? accent : selectionBackground
    readonly property color navigationText: isMac ? textOnAccent : textPrimary
    readonly property int navigationHeight: Math.round((isMac ? 36 : 40) * fontScale)
    readonly property int panelBorderWidth: highContrastMode ? 2 : isMac ? 0 : 1

    readonly property string activeMode: (typeof backend !== "undefined" && backend) ? backend.effectiveThemeMode : "dark"
    readonly property bool lightMode: activeMode === "light"
    readonly property bool highContrastMode: activeMode === "high_contrast"
    readonly property bool oledMode: activeMode === "oled"
    readonly property bool obsidianMode: activeMode === "obsidian"
    readonly property bool midnightMode: activeMode === "midnight"

    readonly property var colors: (typeof backend !== "undefined" && backend) ? backend.themePalette : ({})
    readonly property real fontScale: (typeof backend !== "undefined" && backend) ? backend.fontScale : 1
    readonly property real spacingScale: (typeof backend !== "undefined" && backend) ? backend.layoutConfig.spacing_scale : 1
    function colorToken(name, fallback) { return colors[name] || fallback }

    readonly property color accent: colorToken("accent", "#EEEEEE")
    readonly property color accentHover: colorToken("accentHover", "#EFEFEF")
    readonly property color accentPressed: colorToken("accentPressed", "#C7C7C7")
    readonly property color accentSoft: colorToken("accentSoft", "#3F3F3F")
    readonly property color borderDefault: colorToken("borderDefault", "#505050")
    readonly property color borderMuted: colorToken("borderMuted", "#333333")
    readonly property color dangerSoft: colorToken("dangerSoft", "#3D3D3D")
    readonly property color disabledBg: colorToken("disabledBg", "#242424")
    readonly property color input: colorToken("input", "#101010")
    readonly property color inputHover: colorToken("inputHover", "#1B1B1B")
    readonly property color mediaAudio: colorToken("mediaAudio", "#BDBDBD")
    readonly property color mediaFile: colorToken("mediaFile", "#BDBDBD")
    readonly property color mediaImage: colorToken("mediaImage", "#D6D6D6")
    readonly property color mediaOverlay: colorToken("mediaOverlay", "#101010")
    readonly property color mediaSubtitle: colorToken("mediaSubtitle", "#CCCCCC")
    readonly property color mediaVideo: colorToken("mediaVideo", "#E8E8E8")
    readonly property color modalScrim: colorToken("modalScrim", "#AA000000")
    readonly property color overlayHover: colorToken("overlayHover", "#252525")
    readonly property color overlayPressed: colorToken("overlayPressed", "#303030")
    readonly property color panelBackground: colorToken("panelBackground", "#181818")
    readonly property color panelHover: colorToken("panelHover", "#252525")
    readonly property color panelSecondary: colorToken("panelSecondary", "#242424")
    readonly property color progressHighlight: colorToken("progressHighlight", "#EEEEEE")
    readonly property color progressTrack: colorToken("progressTrack", "#333333")
    readonly property color selectionBackground: colorToken("selectionBackground", "#3F3F3F")
    readonly property color sidebarBackground: colorToken("sidebarBackground", "#111111")
    readonly property color statusError: colorToken("statusError", "#FFFFFF")
    readonly property color statusRunning: colorToken("statusRunning", "#EEEEEE")
    readonly property color statusSuccess: colorToken("statusSuccess", "#E0E0E0")
    readonly property color statusWarning: colorToken("statusWarning", "#C4C4C4")
    readonly property color subtleFill: colorToken("subtleFill", "#1E1E1E")
    readonly property color successSoft: colorToken("successSoft", "#383838")
    readonly property color textDisabled: colorToken("textDisabled", "#929292")
    readonly property color textOnAccent: colorToken("textOnAccent", "#111111")
    readonly property color textOnMedia: colorToken("textOnMedia", "#FFFFFF")
    readonly property color textPrimary: colorToken("textPrimary", "#F5F5F5")
    readonly property color textSecondary: colorToken("textSecondary", "#BDBDBD")
    readonly property color warningSoft: colorToken("warningSoft", "#343434")
    readonly property color windowBackground: colorToken("windowBackground", "#0C0C0C")

    readonly property color bgPrimary: windowBackground
    readonly property color bgSecondary: panelBackground
    readonly property color bgElevated: panelSecondary
    readonly property color borderSubtle: borderMuted
    readonly property color borderStrong: borderDefault

    readonly property int fontSizeXs: Math.round(12 * fontScale)
    readonly property int fontSizeSm: Math.round(13 * fontScale)
    readonly property int fontSizeMd: Math.round(14 * fontScale)
    readonly property int fontSizeLg: Math.round(16 * fontScale)
    readonly property int fontSizeXl: Math.round(20 * fontScale)

    readonly property int space1: Math.round(4 * spacingScale)
    readonly property int space2: Math.round(8 * spacingScale)
    readonly property int space3: Math.round(12 * spacingScale)
    readonly property int space4: Math.round(16 * spacingScale)
    readonly property int space5: Math.round(24 * spacingScale)
    readonly property int space6: Math.round(32 * spacingScale)

    readonly property int radiusSm: isMac ? 5 : 4
    readonly property int radiusMd: isMac ? 10 : 6
    readonly property int radiusLg: isMac ? 14 : 8

    readonly property string displayFont: bodyFont
    readonly property string bodyFont: isWindows ? "Segoe UI" : Qt.application.font.family
    readonly property string monoFont: Qt.platform.os === "osx" ? "Menlo" : Qt.platform.os === "windows" ? "Consolas" : "monospace"

    readonly property int titlebarHeight: isMac ? 64 : 58
    readonly property int sidebarWidth: Math.round((isMac ? 268 : 252) * spacingScale)
    readonly property int compactBreakpoint: 1120
    readonly property int maxWidth: 1480
    readonly property int buttonHeight: Math.max(28, Math.round((isMac ? 30 : 34) * fontScale))
    readonly property int inputHeight: buttonHeight
    readonly property int checkboxSize: isMac ? 16 : 18
    readonly property int cardPadding: space3
    readonly property int sectionPadding: space4

    readonly property color focusRing: colorToken("focusRing", "#EEEEEE")
    readonly property color transparent: "transparent"
    readonly property color selection: selectionBackground

    readonly property int fontMeta: fontSizeXs
    readonly property int fontSmall: fontSizeSm
    readonly property int fontBody: fontSizeMd
    readonly property int fontTitle: fontSizeLg
    readonly property int fontHeading: fontSizeXl
    readonly property int fontDisplay: Math.round(28 * fontScale)

    readonly property int space0: space1
    readonly property int radiusButton: isMac ? 6 : 4
    readonly property int radiusInput: isMac ? 6 : 4
    readonly property int radiusPanel: isMac ? 12 : 8
    readonly property int radiusCard: radiusPanel
    readonly property int radiusSection: radiusPanel
    readonly property int radiusPill: 999

    readonly property color bgBase: bgPrimary
    readonly property color bgSurface: bgSecondary
    readonly property color bgBorder: borderSubtle
    readonly property color accentPrimary: accent
    readonly property color accentSecondary: accentHover
    readonly property color accentSuccess: statusSuccess
    readonly property color accentWarn: statusWarning
    readonly property color accentError: statusError
    readonly property color accentPurple: statusWarning
    readonly property color textMuted: textDisabled

    readonly property color bg: bgPrimary
    readonly property color bgDeep: bgPrimary
    readonly property color bgLift: bgSecondary
    readonly property color bgGrid: bgSecondary
    readonly property color panel: bgSecondary
    readonly property color panelAlt: bgElevated
    readonly property color section: bgSecondary
    readonly property color sectionAlt: bgElevated
    readonly property color hover: overlayHover
    readonly property color border: borderSubtle
    readonly property color text: textPrimary
    readonly property color muted: textSecondary
    readonly property color subtleText: textDisabled
    readonly property color accent2: statusSuccess
    readonly property color success: statusSuccess
    readonly property color warning: statusWarning
    readonly property color danger: statusError
    readonly property color running: statusRunning
    readonly property color runningSoft: accentSoft
    readonly property color purple: statusWarning
    readonly property color disabledText: textDisabled

    function statusColor(status) {
        if (status === "success" || status === "done")
            return statusSuccess
        if (status === "failed" || status === "cancelled")
            return statusError
        if (status === "skipped")
            return statusWarning
        if (status === "running" || status === "processing" || status === "analyzing" || status === "paused")
            return statusRunning
        return textSecondary
    }

    function statusFill(status) {
        if (status === "success" || status === "done")
            return successSoft
        if (status === "failed" || status === "cancelled")
            return dangerSoft
        if (status === "skipped")
            return warningSoft
        if (status === "running" || status === "processing" || status === "analyzing" || status === "paused")
            return accentSoft
        return subtleFill
    }
}
