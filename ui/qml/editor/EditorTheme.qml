pragma Singleton
import QtQuick 2.15
import App 1.0

// The single visual source of truth for the montage workspace.
QtObject {
    readonly property color bgApp: "#101214"
    readonly property color bgPanel: "#181b1f"
    readonly property color bgElevated: "#22262b"
    readonly property color bgHover: "#2b3036"
    readonly property color bgPreview: "#090b0e"
    readonly property color borderSubtle: "#30353b"
    readonly property color borderStrong: "#4a515a"
    readonly property color textPrimary: "#f2f4f7"
    readonly property color textSecondary: "#b5bdc8"
    readonly property color textDisabled: "#747d89"
    readonly property color textOnMedia: "#ffffff"
    readonly property color textOutline: "#000000"
    readonly property color overlayTitleBg: "#b0000000"
    readonly property color guide: "#7099aacc"
    readonly property color safeArea: "#8099aacc"
    readonly property color accent: "#2f80ed"
    readonly property color accentHover: "#4b93f1"
    readonly property color accentPressed: "#2468bf"
    readonly property color success: "#4bb586"
    readonly property color warning: "#d9a441"
    readonly property color danger: "#df6271"

    readonly property color trackVideo: "#285f91"
    readonly property color trackAudio: "#276b56"
    readonly property color trackTitle: "#68458c"
    readonly property color trackMusic: "#23767a"
    readonly property color timelineLaneA: "#15191d"
    readonly property color timelineLaneB: "#191d22"

    // Backwards-compatible aliases used by existing editor controls.
    readonly property color background: bgApp
    readonly property color panel: bgPanel
    readonly property color raised: bgElevated
    readonly property color hover: bgHover
    readonly property color border: borderSubtle
    readonly property color text: textPrimary
    readonly property color secondary: textSecondary
    readonly property color muted: textDisabled
    readonly property color video: trackVideo
    readonly property color audio: trackAudio
    readonly property color title: trackTitle

    readonly property int space1: 4
    readonly property int space2: 8
    readonly property int space3: 12
    readonly property int space4: 16
    readonly property int radiusControl: 6
    readonly property int radiusPanel: 10
    readonly property int fontSize: Math.max(12, Math.round(13 * Theme.fontScale))
    readonly property int smallSize: Math.max(12, Math.round(12 * Theme.fontScale))
    readonly property int headingSize: Math.round(16 * Theme.fontScale)
    readonly property int controlHeight: 32
    readonly property int primaryHeight: 44
}
