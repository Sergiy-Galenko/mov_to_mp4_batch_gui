import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../archive"

Item {
    id: root
    property var appRoot: null

    Rectangle {
        anchors.fill: parent
        color: Theme.windowBackground
    }

    ArchivePanel {
        id: archivePanel
        anchors.fill: parent
        anchors.margins: Theme.space4
        appRoot: root.appRoot
    }
}
