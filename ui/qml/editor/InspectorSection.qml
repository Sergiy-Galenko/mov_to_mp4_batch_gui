import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
ColumnLayout {
    id: root
    property string title: ""
    property bool expanded: true
    default property alias fields: body.data
    spacing: 8
    Layout.fillWidth: true
    EditorButton { text: root.title; iconName: root.expanded ? "chevron-down" : "chevron"; Layout.fillWidth: true; onClicked: root.expanded = !root.expanded }
    ColumnLayout { id: body; Layout.fillWidth: true; spacing: 8; visible: root.expanded }
    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: EditorTheme.border }
}
