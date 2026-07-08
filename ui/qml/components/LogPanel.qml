import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import App 1.0

Panel {
    title: I18n.t("log")
    RowLayout {
        Layout.fillWidth: true
        Label {
            Layout.fillWidth: true
            text: backend ? backend.statusText : "Ready"
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSmall
            elide: Text.ElideRight
        }
        SecondaryButton { Layout.fillWidth: false; text: I18n.t("export"); onClicked: backend && backend.exportLog() }
        SecondaryButton { Layout.fillWidth: false; text: I18n.t("clear"); onClicked: backend && backend.clearLog() }
    }
    ListView {
        Layout.fillWidth: true
        Layout.preferredHeight: 104
        model: backend ? backend.logModel : null
        clip: true
        spacing: 4
        cacheBuffer: 200
        reuseItems: true
        delegate: Label {
            width: ListView.view.width
            text: model.line
            color: model.level === "ERROR" ? Theme.accentError : model.level === "WARN" ? Theme.accentWarn : Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: Theme.fontMeta
            elide: Text.ElideRight
        }
    }
}
