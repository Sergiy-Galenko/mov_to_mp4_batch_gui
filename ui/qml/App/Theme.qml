pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property color bgBase: "#0D0F11"
    readonly property color bgSurface: "#151820"
    readonly property color bgElevated: "#1E2330"
    readonly property color bgBorder: "#2A3040"
    readonly property color accentPrimary: "#3D8EFF"
    readonly property color accentSuccess: "#22C55E"
    readonly property color accentWarn: "#F59E0B"
    readonly property color accentError: "#EF4444"
    readonly property color accentPurple: "#8B5CF6"
    readonly property color textPrimary: "#F0F4FF"
    readonly property color textSecondary: "#8B95A8"
    readonly property color textMuted: "#4A5568"

    readonly property string displayFont: "IBM Plex Mono"
    readonly property string monoFont: "JetBrains Mono"
    readonly property string bodyFont: "Inter"
    readonly property int fontMeta: 11
    readonly property int fontSmall: 13
    readonly property int fontBody: 15
    readonly property int fontTitle: 18
    readonly property int fontHeading: 24
    readonly property int fontDisplay: 32

    readonly property int space0: 4
    readonly property int space1: 8
    readonly property int space2: 12
    readonly property int space3: 16
    readonly property int space4: 24
    readonly property int space5: 32
    readonly property int maxWidth: 1480
    readonly property int compactBreakpoint: 1120
    readonly property int titlebarHeight: 40
    readonly property int sidebarWidth: 220
    readonly property int radiusButton: 6
    readonly property int radiusPanel: 10
    readonly property int radiusInput: 6
    readonly property int radiusCard: 10
    readonly property int radiusSection: 10
    readonly property int radiusPill: 999
    readonly property int buttonHeight: 34
    readonly property int inputHeight: 34
    readonly property int checkboxSize: 18
    readonly property int cardPadding: 12
    readonly property int sectionPadding: 12
    readonly property real shadowOpacity: 0.22

    readonly property color bg: bgBase
    readonly property color bgDeep: "#090B0D"
    readonly property color bgLift: bgSurface
    readonly property color bgGrid: "#11151C"
    readonly property color panel: bgSurface
    readonly property color panelAlt: bgElevated
    readonly property color panelHover: "#242B3A"
    readonly property color section: bgSurface
    readonly property color sectionAlt: bgElevated
    readonly property color input: "#101319"
    readonly property color inputHover: "#171B24"
    readonly property color hover: bgElevated
    readonly property color border: bgBorder
    readonly property color borderStrong: "#3A4358"
    readonly property color focusRing: accentPrimary
    readonly property color text: textPrimary
    readonly property color muted: textSecondary
    readonly property color subtleText: textMuted
    readonly property color accent: accentPrimary
    readonly property color accent2: accentSuccess
    readonly property color accentHover: "#66A6FF"
    readonly property color accentSoft: "#142641"
    readonly property color success: accentSuccess
    readonly property color successSoft: "#12331F"
    readonly property color warning: accentWarn
    readonly property color warningSoft: "#33230A"
    readonly property color danger: accentError
    readonly property color dangerSoft: "#351719"
    readonly property color running: accentWarn
    readonly property color runningSoft: "#33230A"
    readonly property color purple: accentPurple
    readonly property color disabledBg: "#1B202B"
    readonly property color disabledText: textMuted

    function statusColor(status) {
        if (status === "success" || status === "done")
            return accentSuccess
        if (status === "failed")
            return accentError
        if (status === "skipped" || status === "running" || status === "processing" || status === "analyzing")
            return accentWarn
        if (status === "paused")
            return accentPurple
        return textSecondary
    }
}
