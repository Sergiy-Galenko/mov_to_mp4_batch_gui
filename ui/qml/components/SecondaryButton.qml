import QtQuick 2.15
import QtQuick.Layouts 1.15
import App 1.0

AppButton {
    variant: "secondary"
    Layout.fillWidth: !Theme.isMac
}
