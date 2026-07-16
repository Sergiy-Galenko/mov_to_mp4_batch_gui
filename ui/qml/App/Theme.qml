pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property string activeMode: (typeof backend !== "undefined" && backend) ? backend.effectiveThemeMode : "dark"
    readonly property bool lightMode: activeMode === "light"
    readonly property bool highContrastMode: activeMode === "high_contrast"

    // Semantic desktop colour tokens. Legacy aliases below keep existing controls compatible.
    // Dark mode: black and green surfaces. Light mode: white and blue surfaces.
    readonly property color windowBackground: highContrastMode ? "#000000" : lightMode ? "#F4F8FF" : "#050907"
    readonly property color sidebarBackground: highContrastMode ? "#000000" : lightMode ? "#FFFFFF" : "#07140F"
    readonly property color panelBackground: highContrastMode ? "#000000" : lightMode ? "#FFFFFF" : "#0B2018"
    readonly property color panelSecondary: highContrastMode ? "#0A0A0A" : lightMode ? "#EFF6FF" : "#102D21"
    readonly property color borderDefault: highContrastMode ? "#FFFFFF" : lightMode ? "#BFDBFE" : "#2E6249"
    readonly property color borderMuted: highContrastMode ? "#A8A8A8" : lightMode ? "#DBEAFE" : "#1E4936"

    readonly property color bgPrimary: windowBackground
    readonly property color bgSecondary: panelBackground
    readonly property color bgElevated: panelSecondary
    readonly property color borderSubtle: borderMuted
    readonly property color borderStrong: borderDefault

    readonly property color textPrimary: highContrastMode ? "#FFFFFF" : lightMode ? "#102A56" : "#F0FFF6"
    readonly property color textSecondary: highContrastMode ? "#FFFFFF" : lightMode ? "#3D5E8B" : "#B8D9C4"
    readonly property color textDisabled: highContrastMode ? "#C8C8C8" : lightMode ? "#6B88B3" : "#7EAB90"
    readonly property color textOnAccent: "#FFFFFF"

    readonly property color accent: highContrastMode ? "#FFFF00" : (typeof backend !== "undefined" && backend ? backend.accentColor : "#2563EB")
    readonly property color accentHover: highContrastMode ? "#FFFF66" : lightMode ? "#1D4ED8" : "#3B82F6"
    readonly property color accentPressed: highContrastMode ? "#D6D600" : lightMode ? "#1E40AF" : "#1D4ED8"

    readonly property color statusSuccess: highContrastMode ? "#00FF00" : lightMode ? "#15803D" : "#4ADE80"
    readonly property color statusWarning: highContrastMode ? "#FFFF00" : lightMode ? "#A16207" : "#FACC15"
    readonly property color statusError: highContrastMode ? "#FF5555" : lightMode ? "#DC2626" : "#FB7185"
    readonly property color statusRunning: accent

    readonly property int fontSizeXs: 12
    readonly property int fontSizeSm: 13
    readonly property int fontSizeMd: 14
    readonly property int fontSizeLg: 16
    readonly property int fontSizeXl: 20

    readonly property int space1: 4
    readonly property int space2: 8
    readonly property int space3: 12
    readonly property int space4: 16
    readonly property int space5: 24
    readonly property int space6: 32

    readonly property int radiusSm: 4
    readonly property int radiusMd: 6
    readonly property int radiusLg: 8

    readonly property string displayFont: "Segoe UI"
    readonly property string bodyFont: "Segoe UI"
    readonly property string monoFont: "JetBrains Mono"

    readonly property int titlebarHeight: 52
    readonly property int sidebarWidth: 236
    readonly property int compactBreakpoint: 1120
    readonly property int maxWidth: 1480
    readonly property int buttonHeight: 36
    readonly property int inputHeight: 36
    readonly property int checkboxSize: 18
    readonly property int cardPadding: space3
    readonly property int sectionPadding: space4

    readonly property color transparent: "transparent"
    readonly property color input: highContrastMode ? "#000000" : lightMode ? "#FFFFFF" : "#07140F"
    readonly property color inputHover: highContrastMode ? "#101010" : lightMode ? "#F8FBFF" : "#0D261B"
    readonly property color panelHover: highContrastMode ? "#171717" : lightMode ? "#E8F1FF" : "#143A2A"
    readonly property color accentSoft: highContrastMode ? "#292900" : lightMode ? "#DBEAFE" : "#102B47"
    readonly property color successSoft: highContrastMode ? "#003300" : lightMode ? "#DCFCE7" : "#123D29"
    readonly property color warningSoft: highContrastMode ? "#3A3200" : lightMode ? "#FEF3C7" : "#453C0D"
    readonly property color dangerSoft: highContrastMode ? "#3A0000" : lightMode ? "#FEE2E2" : "#4A1C28"
    readonly property color disabledBg: highContrastMode ? "#080808" : lightMode ? "#E1ECFC" : "#163626"
    readonly property color selectionBackground: highContrastMode ? "#292900" : lightMode ? "#DBEAFE" : "#102B47"
    readonly property color selection: selectionBackground
    readonly property color progressTrack: highContrastMode ? "#000000" : lightMode ? "#D8E8FF" : "#1E4936"
    readonly property color progressHighlight: accent
    readonly property color overlayHover: highContrastMode ? "#171717" : lightMode ? "#E8F1FF" : "#143A2A"
    readonly property color overlayPressed: highContrastMode ? "#222222" : lightMode ? "#D8E8FF" : "#1E4936"
    readonly property color subtleFill: highContrastMode ? "#050505" : lightMode ? "#F8FBFF" : "#0D261B"

    readonly property int fontMeta: fontSizeXs
    readonly property int fontSmall: fontSizeSm
    readonly property int fontBody: fontSizeMd
    readonly property int fontTitle: fontSizeLg
    readonly property int fontHeading: fontSizeXl
    readonly property int fontDisplay: 28

    readonly property int space0: space1
    readonly property int radiusButton: radiusSm
    readonly property int radiusInput: radiusSm
    readonly property int radiusPanel: radiusMd
    readonly property int radiusCard: radiusMd
    readonly property int radiusSection: radiusMd
    readonly property int radiusPill: 999

    readonly property color bgBase: bgPrimary
    readonly property color bgSurface: bgSecondary
    readonly property color bgBorder: borderSubtle
    readonly property color accentPrimary: accent
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
    readonly property color focusRing: highContrastMode ? "#FFFF00" : lightMode ? "#2563EB" : "#60A5FA"
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
