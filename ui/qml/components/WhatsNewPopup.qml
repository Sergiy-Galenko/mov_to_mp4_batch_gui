import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.settings 1.0
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

    property string currentVersion: "1.1.0" // Update this when releasing new features

    Settings {
        id: settings
        category: "App"
        property string lastSeenVersion: ""
    }

    Component.onCompleted: {
        if (settings.lastSeenVersion !== currentVersion) {
            root.open()
        }
    }

    onClosed: {
        settings.lastSeenVersion = currentVersion
    }

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
            text: "🎉 Що нового у версії " + root.currentVersion
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
                        text: "✨ Нові фічі та UI/UX Редизайн"
                        color: Theme.accentPrimary
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "• <b>Дизайн Arc/Linear</b>: Повністю оновлено вигляд програми. Глибокі темні кольори, скляні ефекти та м'які тіні.\n" +
                              "• <b>Прогресивне розкриття</b>: Інтерфейс став набагато простішим. Розширені налаштування (Sidebar) тепер з'являються лише коли вони дійсно потрібні.\n" +
                              "• <b>Емодзі замість тексту</b>: Легка навігація по статусах (✅ готово, ⏳ обробка) та типах файлів (🎬 відео, 🎵 аудіо).\n" +
                              "• <b>Нова Drop Zone</b>: Зручна та приваблива зона для перетягування файлів (Drag & Drop) прямо на головному екрані."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSizeMd
                        lineHeight: 1.4
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space2

                    Label {
                        text: "🐛 Виправлення багів (Bug Fixes)"
                        color: Theme.statusWarning
                        font.pixelSize: Theme.fontSizeLg
                        font.bold: true
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "• <b>Оптимізовано Header та Footer</b>: Виправлено відображення компонентів на різних роздільних здатностях.\n" +
                              "• <b>Синтаксис QML</b>: Виправлено помилки парсингу та відсутні властивості (напр. radius у ShimmerBar).\n" +
                              "• <b>Продуктивність</b>: Покращено швидкість анімацій та рендерингу списку файлів (QueueItem) за рахунок відмови від важких тіней."
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
            text: "Чудово! Почати роботу"
            font.pixelSize: Theme.fontSizeMd
            font.bold: true
            onClicked: root.close()
        }
    }
}
