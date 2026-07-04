pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property color bgPrimary: "#14161A"
    readonly property color bgSecondary: "#1C1F24"
    readonly property color bgElevated: "#22262C"
    readonly property color borderSubtle: "#2C3036"
    readonly property color borderStrong: "#3A3F47"

    readonly property color textPrimary: "#F0F1F3"
    readonly property color textSecondary: "#9BA1AA"
    readonly property color textDisabled: "#5A5F66"
    readonly property color textOnAccent: "#FFFFFF"

    readonly property color accent: "#3D8BFF"
    readonly property color accentHover: "#5B9DFF"
    readonly property color accentPressed: "#2E70D6"

    readonly property color statusSuccess: "#3FBF7F"
    readonly property color statusWarning: "#E0A93E"
    readonly property color statusError: "#E5584F"
    readonly property color statusRunning: "#3D8BFF"

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
    readonly property int radiusMd: 8
    readonly property int radiusLg: 12

    readonly property string displayFont: "Inter"
    readonly property string bodyFont: "Inter"
    readonly property string monoFont: "JetBrains Mono"

    readonly property int titlebarHeight: 56
    readonly property int sidebarWidth: 220
    readonly property int compactBreakpoint: 1120
    readonly property int maxWidth: 1480
    readonly property int buttonHeight: 36
    readonly property int inputHeight: 36
    readonly property int checkboxSize: 18
    readonly property int cardPadding: space3
    readonly property int sectionPadding: space4

    readonly property color transparent: "transparent"
    readonly property color input: "#171A1F"
    readonly property color inputHover: "#20242A"
    readonly property color panelHover: "#262B32"
    readonly property color accentSoft: "#1D2D45"
    readonly property color successSoft: "#1B3328"
    readonly property color warningSoft: "#352A18"
    readonly property color dangerSoft: "#361F20"
    readonly property color disabledBg: "#1A1D22"
    readonly property color selection: "#1F2D42"
    readonly property color progressTrack: "#111318"
    readonly property color progressHighlight: "#8EBBFF"
    readonly property color overlayHover: "#24282F"
    readonly property color overlayPressed: "#2B3038"
    readonly property color subtleFill: "#191C21"

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
    readonly property color focusRing: accent
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
