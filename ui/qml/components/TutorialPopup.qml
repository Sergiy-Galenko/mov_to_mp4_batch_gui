import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Popup {
    id: root
    width: 600
    height: 520
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Theme.bgElevated
        radius: Theme.radiusLg
        border.width: 1
        border.color: Theme.borderStrong
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space6
        spacing: Theme.space4

        Label {
            Layout.fillWidth: true
            text: "📖 Як почати користуватися"
            color: Theme.textPrimary
            font.family: Theme.displayFont
            font.pixelSize: Theme.fontSizeXl
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: parent.width - 20
                spacing: Theme.space4

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Label {
                        text: "1️⃣ Додайте файли"
                        color: Theme.accentPrimary
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Просто перетягніть ваші відео, аудіо, зображення або субтитри у велику область 📥 на головному екрані. Або скористайтеся кнопкою «Обрати файли...»."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Label {
                        text: "2️⃣ Оберіть папку збереження"
                        color: Theme.statusWarning
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Внизу екрана натисніть на іконку папки (📁), щоб вказати, куди будуть зберігатися готові файли. Без цього кнопка старту не активується."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Label {
                        text: "3️⃣ Налаштуйте формат (Опціонально)"
                        color: Theme.accent
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Програма автоматично підбирає найкращий формат (Smart Convert). Але якщо ви хочете обрати інший пресет (наприклад, для iPhone), натисніть ⚙️ у верхньому правому куті, щоб відкрити розширені налаштування."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Label {
                        text: "4️⃣ Запустіть конвертацію"
                        color: Theme.statusSuccess
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Натисніть велику кнопку 🚀 Старт. Програма все зробить автоматично: задіє GPU для швидкості, оптимізує якість та збереже файли у вказану папку."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }
            }
        }

        PrimaryButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 200
            Layout.preferredHeight: 44
            text: "Зрозуміло!"
            font.pixelSize: Theme.fontSizeMd
            font.bold: true
            onClicked: root.close()
        }
    }
}
