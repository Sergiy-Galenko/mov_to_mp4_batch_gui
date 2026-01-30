pragma Singleton
import QtQuick 2.15

QtObject {
    property color bg: "#0B1220"
    property color panel: "#0F172A"
    property color section: "#0B1324"
    property color border: "#1E293B"
    property color text: "#E2E8F0"
    property color muted: "#94A3B8"
    property color accent: "#3B82F6"
    property color accentHover: "#2563EB"
    property color input: "#0B1324"
    property color hover: "#1E293B"
    property color disabledBg: "#1F2937"
    property color disabledText: "#64748B"

    property int space1: 8
    property int space2: 16
    property int space3: 24
    property int space4: 32
    property int maxWidth: 1160
    property int compactBreakpoint: 980
    property int radiusCard: 16
    property int radiusSection: 12
}
