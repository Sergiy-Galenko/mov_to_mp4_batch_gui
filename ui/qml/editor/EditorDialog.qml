import QtQuick 2.15
import QtQuick.Controls 2.15
Dialog {
    id: root
    modal: true; padding: 20
    palette.windowText: EditorTheme.text; palette.text: EditorTheme.text; palette.buttonText: EditorTheme.text
    palette.button: EditorTheme.raised; palette.base: EditorTheme.background; palette.highlight: EditorTheme.accent
    background: Rectangle { color: EditorTheme.panel; border.color: EditorTheme.border; radius: EditorTheme.radiusPanel }
    header: Label { text: root.title; color: EditorTheme.text; font.pixelSize: EditorTheme.fontSize + 3; font.bold: true; padding: 20; wrapMode: Text.Wrap }
}
