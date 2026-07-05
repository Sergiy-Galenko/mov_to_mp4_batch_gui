pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property string activeMode: (typeof backend !== "undefined" && backend) ? backend.effectiveThemeMode : "dark"
    readonly property bool lightMode: activeMode === "light"
    readonly property bool highContrastMode: activeMode === "high_contrast"

    readonly property color bgPrimary: highContrastMode ? "#000000" : lightMode ? "#F9FAFB" : "#0E0F11"
    readonly property color bgSecondary: highContrastMode ? "#080808" : lightMode ? "#FFFFFF" : "#141517"
    readonly property color bgElevated: highContrastMode ? "#111111" : lightMode ? "#FFFFFF" : "#1C1D21"
    readonly property color borderSubtle: highContrastMode ? "#FFFFFF" : lightMode ? "#E5E7EB" : "#27282D"
    readonly property color borderStrong: highContrastMode ? "#FFFFFF" : lightMode ? "#D1D5DB" : "#36383D"

    readonly property color textPrimary: highContrastMode ? "#FFFFFF" : lightMode ? "#111827" : "#F3F4F6"
    readonly property color textSecondary: highContrastMode ? "#F5F5F5" : lightMode ? "#6B7280" : "#9CA3AF"
    readonly property color textDisabled: highContrastMode ? "#CFCFCF" : lightMode ? "#9CA3AF" : "#4B5563"
    readonly property color textOnAccent: "#FFFFFF"

    readonly property color accent: highContrastMode ? "#FFFF00" : (typeof backend !== "undefined" && backend ? backend.accentColor : "#5E6AD2")
    readonly property color accentHover: highContrastMode ? "#FFFF66" : lightMode ? "#4F46E5" : "#6E7BF2"
    readonly property color accentPressed: highContrastMode ? "#D6D600" : lightMode ? "#4338CA" : "#4E58B2"

    readonly property color statusSuccess: "#10B981"
    readonly property color statusWarning: "#F59E0B"
    readonly property color statusError: "#EF4444"
    readonly property color statusRunning: "#3B82F6"

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

    readonly property int radiusSm: 6
    readonly property int radiusMd: 12
    readonly property int radiusLg: 16

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
    readonly property color input: highContrastMode ? "#000000" : lightMode ? "#FFFFFF" : "#18191B"
    readonly property color inputHover: highContrastMode ? "#101010" : lightMode ? "#F3F4F6" : "#232427"
    readonly property color panelHover: highContrastMode ? "#151515" : lightMode ? "#F9FAFB" : "#232427"
    readonly property color accentSoft: highContrastMode ? "#333300" : lightMode ? "#EEF2FF" : "#1E2238"
    readonly property color successSoft: highContrastMode ? "#003300" : lightMode ? "#ECFDF5" : "#064E3B"
    readonly property color warningSoft: highContrastMode ? "#3A3200" : lightMode ? "#FFFBEB" : "#78350F"
    readonly property color dangerSoft: highContrastMode ? "#3A0000" : lightMode ? "#FEF2F2" : "#7F1D1D"
    readonly property color disabledBg: highContrastMode ? "#080808" : lightMode ? "#F3F4F6" : "#1F2937"
    readonly property color selection: highContrastMode ? "#202000" : lightMode ? "#E0E7FF" : "#3730A3"
    readonly property color progressTrack: highContrastMode ? "#000000" : lightMode ? "#E5E7EB" : "#374151"
    readonly property color progressHighlight: accent
    readonly property color overlayHover: highContrastMode ? "#171717" : lightMode ? "#F3F4F6" : "#27272A"
    readonly property color overlayPressed: highContrastMode ? "#222222" : lightMode ? "#E5E7EB" : "#3F3F46"
    readonly property color subtleFill: highContrastMode ? "#050505" : lightMode ? "#F9FAFB" : "#1F2937"

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
