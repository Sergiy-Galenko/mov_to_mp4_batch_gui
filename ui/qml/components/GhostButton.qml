import QtQuick 2.15
import QtQuick.Layouts 1.15
import App 1.0

AppButton {
    variant: "ghost"
    Layout.fillWidth: !Theme.isMac
}
