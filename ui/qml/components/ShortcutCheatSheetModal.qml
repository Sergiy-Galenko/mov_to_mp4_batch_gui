import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Dialog {
    id: root
    title: ""
    modal: true
    dim: true
    x: (parent ? (parent.width - width) / 2 : 100)
    y: (parent ? (parent.height - height) / 2 : 100)
    width: Math.min(680, parent ? parent.width - 32 : 600)
    height: Math.min(520, parent ? parent.height - 32 : 480)
    padding: 0
    clip: true

    property string searchText: ""

    background: Rectangle {
        radius: Theme.radiusLg
        color: Theme.panelBackground
        border.width: 1
        border.color: Theme.borderStrong
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: Theme.panelSecondary

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12


                Label {
                    Layout.fillWidth: true
                    text: I18n.t("keyboard_shortcuts")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSizeMd
                    font.weight: Font.DemiBold
                }

                AppTextField {
                    Layout.preferredWidth: 200
                    placeholderText: I18n.t("shortcut_search")
                    onTextChanged: root.searchText = text.toLowerCase()
                }

                AppIconButton {
                    iconName: "close"
                    accessibleLabel: I18n.t("cancel")
                    onClicked: root.close()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.borderMuted
        }

        // Body List
        ScrollView {
            id: shortcutsScroll
            contentWidth: availableWidth
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            anchors.margins: 12


            ColumnLayout {
                width: shortcutsScroll.availableWidth
                spacing: 12


                Repeater {
                    model: [
                        { category: "conversion", title: "Conversion Controls" },
                        { category: "queue", title: "Queue Management" },
                        { category: "navigation", title: "Navigation & Screens" },
                        { category: "general", title: "General & Presets" }
                    ]

                    delegate: ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Label {
                            text: modelData.title
                            color: Theme.accentPrimary
                            font.pixelSize: Theme.fontSizeSm
                            font.weight: Font.DemiBold
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 16
                            rowSpacing: 6

                            Repeater {
                                model: backend ? backend.allShortcuts.filter(
                                    function(s) {
                                        return s.category === modelData.category &&
                                            (root.searchText === "" ||
                                             s.label.toLowerCase().includes(root.searchText) ||
                                             s.key.toLowerCase().includes(root.searchText))
                                    }
                                ) : []

                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: kbdLbl.implicitWidth + 16
                                        Layout.preferredHeight: 24
                                        radius: Theme.radiusSm
                                        color: Theme.panelSecondary
                                        border.width: 1
                                        border.color: Theme.borderStrong
                                        Label {
                                            id: kbdLbl
                                            anchors.centerIn: parent
                                            text: modelData.key
                                            color: Theme.textPrimary
                                            font.family: Theme.monoFont
                                            font.pixelSize: 11
                                            font.weight: Font.DemiBold
                                        }
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.label
                                        color: Theme.textSecondary
                                        font.pixelSize: Theme.fontSizeSm
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderMuted }
                    }
                }
            }
        }
    }
}
