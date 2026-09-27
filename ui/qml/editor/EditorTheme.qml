pragma Singleton
import QtQuick 2.15
import App 1.0
QtObject {
    readonly property color background: "#111318"
    readonly property color panel: "#1a1d23"
    readonly property color raised: "#232730"
    readonly property color hover: "#303641"
    readonly property color border: "#343a46"
    readonly property color text: "#f1f3f7"
    readonly property color secondary: "#adb5c4"
    readonly property color muted: "#8691a3"
    readonly property color accent: "#268cff"
    readonly property color danger: "#ff6978"
    readonly property color success: "#55c99a"
    readonly property color video: "#244e7b"
    readonly property color audio: "#20564c"
    readonly property color title: "#694389"
    readonly property int fontSize: Math.round(12 * Theme.fontScale)
    readonly property int smallSize: Math.round(11 * Theme.fontScale)
    readonly property int controlHeight: Math.max(30, fontSize + 12)
}
