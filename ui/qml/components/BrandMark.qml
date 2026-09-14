import QtQuick 2.15
Item {
    objectName: "brandMark"
    implicitWidth: 32
    implicitHeight: 32
    property alias source: logo.source
    readonly property bool ready: logo.status === Image.Ready
    Image {
        id: logo
        anchors.fill: parent
        source: Qt.resolvedUrl("../../../assets/app-logo-v2.png")
        sourceSize.width: 256
        sourceSize.height: 256
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        cache: true
    }
}
