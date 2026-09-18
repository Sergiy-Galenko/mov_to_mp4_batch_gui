import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Dialog {
    id: root
    title: "Користувацькі JS-скрипти та плагіни (Scripting Engine)"
    modal: true
    Overlay.modal: Rectangle { color: Theme.modalScrim }
    width: 780
    height: 660
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)

    background: Rectangle {
        color: Theme.panelBackground
        radius: Theme.radiusLg
        border.width: 1
        border.color: Theme.borderMuted
    }

    property bool masterEnabled: false
    property int activeTab: 0 // 0: rename, 1: route, 2: filter

    property bool renameEnabled: true
    property string renameCode: ""

    property bool routeEnabled: false
    property string routeCode: ""

    property bool filterEnabled: false
    property string filterCode: ""

    property string testResultText: ""
    property string testErrorText: ""
    property bool testSuccess: false

    function activeType() {
        if (activeTab === 0) return "rename"
        if (activeTab === 1) return "route"
        return "filter"
    }

    function loadConfig() {
        if (!backend) return
        var cfg = backend.getScriptingConfig()
        root.masterEnabled = !!cfg.enabled
        root.renameEnabled = cfg.rename_enabled !== undefined ? !!cfg.rename_enabled : true
        root.renameCode = cfg.rename_script || ""
        root.routeEnabled = !!cfg.route_enabled
        root.routeCode = cfg.route_script || ""
        root.filterEnabled = !!cfg.filter_enabled
        root.filterCode = cfg.filter_script || ""
        updateSnippetModel()
        clearTestResult()
    }

    function saveConfig() {
        if (!backend) return
        syncCurrentCode()
        var cfg = {
            "enabled": root.masterEnabled,
            "rename_enabled": root.renameEnabled,
            "rename_script": root.renameCode,
            "route_enabled": root.routeEnabled,
            "route_script": root.routeCode,
            "filter_enabled": root.filterEnabled,
            "filter_script": root.filterCode
        }
        backend.saveScriptingConfig(cfg)
        root.close()
    }

    function syncCurrentCode() {
        if (root.activeTab === 0) root.renameCode = codeArea.text
        else if (root.activeTab === 1) root.routeCode = codeArea.text
        else if (root.activeTab === 2) root.filterCode = codeArea.text
    }

    function switchTab(newTab) {
        syncCurrentCode()
        root.activeTab = newTab
        if (newTab === 0) codeArea.text = root.renameCode
        else if (newTab === 1) codeArea.text = root.routeCode
        else if (newTab === 2) codeArea.text = root.filterCode
        updateSnippetModel()
        clearTestResult()
    }

    function updateSnippetModel() {
        if (!backend) return
        var snips = backend.getScriptSnippets(activeType()) || []
        var items = ["-- Вибрати готовий шаблон --"]
        for (var i = 0; i < snips.length; ++i) {
            items.push(snips[i].title)
        }
        snippetCombo.model = items
        snippetCombo.currentIndex = 0
    }

    function applySnippet(index) {
        if (index <= 0 || !backend) return
        var snips = backend.getScriptSnippets(activeType()) || []
        if (index - 1 < snips.length) {
            codeArea.text = snips[index - 1].code
            clearTestResult()
        }
    }

    function resetCurrentToDefault() {
        if (!backend) return
        var def = backend.resetScriptToDefault(activeType())
        codeArea.text = def
        clearTestResult()
    }

    function runTest() {
        if (!backend) return
        syncCurrentCode()
        var type = activeType()
        var code = codeArea.text
        var rep = backend.testUserScript(type, code)
        root.testSuccess = !!rep.success
        if (rep.success) {
            root.testResultText = rep.result || ""
            root.testErrorText = ""
        } else {
            root.testResultText = ""
            root.testErrorText = rep.error || "Помилка виконання"
        }
    }

    function clearTestResult() {
        root.testResultText = ""
        root.testErrorText = ""
        root.testSuccess = false
    }

    onOpened: loadConfig()

    contentItem: ColumnLayout {
        spacing: 10

        // Header: Master Switch & Description
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            AppCheckBox {
                id: masterCheck
                text: "Увімкнути виконання JS-скриптів"
                checked: root.masterEnabled
                onToggled: root.masterEnabled = checked
            }

            Item { Layout.fillWidth: true }

            Label {
                text: "ECMAScript Sandbox (QJSEngine)"
                font.pixelSize: Theme.fontSizeXs
                font.family: Theme.monoFont
                color: Theme.textMuted
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderDefault }

        // Tabs: Rename, Routing, Filter
        RowLayout {
            Layout.fillWidth: true
            spacing: 4

            AppButton {
                Layout.fillWidth: true
                text: "🏷️ Перейменування (formatOutputName)"
                variant: root.activeTab === 0 ? "primary" : "ghost"
                onClicked: root.switchTab(0)
            }

            AppButton {
                Layout.fillWidth: true
                text: "📁 Сортування по папках (routeOutputFolder)"
                variant: root.activeTab === 1 ? "primary" : "ghost"
                onClicked: root.switchTab(1)
            }

            AppButton {
                Layout.fillWidth: true
                text: "⚙️ FFmpeg фільтри (buildVideoFilter)"
                variant: root.activeTab === 2 ? "primary" : "ghost"
                onClicked: root.switchTab(2)
            }
        }

        // Subheader: Tab-specific toggle and Snippets
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            AppCheckBox {
                text: root.activeTab === 0 ? "Активувати правило перейменування" :
                      root.activeTab === 1 ? "Активувати правило сортування" :
                      "Активувати правило фільтрів FFmpeg"
                checked: root.activeTab === 0 ? root.renameEnabled :
                         root.activeTab === 1 ? root.routeEnabled :
                         root.filterEnabled
                onToggled: {
                    if (root.activeTab === 0) root.renameEnabled = checked
                    else if (root.activeTab === 1) root.routeEnabled = checked
                    else if (root.activeTab === 2) root.filterEnabled = checked
                }
            }

            Item { Layout.fillWidth: true }

            Label {
                text: "Шаблони:"
                font.pixelSize: Theme.fontSizeSm
                color: Theme.textSecondary
            }

            AppComboBox {
                id: snippetCombo
                Layout.preferredWidth: 260
                onActivated: function(index) { root.applySnippet(index) }
            }

            AppButton {
                text: "Скинути"
                variant: "ghost"
                onClicked: root.resetCurrentToDefault()
            }
        }

        // Code Editor Canvas / Scroll Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 220
            color: Theme.bgElevated
            radius: Theme.radiusMd
            border.width: 1
            border.color: Theme.borderDefault
            clip: true

            ScrollView {
                anchors.fill: parent
                anchors.margins: 4
                clip: true

                TextArea {
                    id: codeArea
                    font.family: Theme.monoFont
                    font.pixelSize: 12
                    color: Theme.textPrimary
                    selectionColor: Theme.accentPrimary
                    selectedTextColor: Theme.textPrimary
                    selectByMouse: true
                    wrapMode: TextEdit.NoWrap
                    text: root.renameCode
                    tabStopDistance: 28
                    background: null
                }
            }
        }

        // Test Runner Bar & Result Preview Card
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 74
            color: Theme.panelBackground
            radius: Theme.radiusMd
            border.width: 1
            border.color: Theme.borderDefault

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 12

                AppButton {
                    text: "▶ Перевірити скрипт"
                    variant: "secondary"
                    implicitHeight: 34
                    onClicked: root.runTest()
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    RowLayout {
                        spacing: 6
                        Label {
                            text: "Зразок файлу: DJI_0042.mov (4K 3840×2160, 60fps, HEVC, 74s)"
                            font.pixelSize: Theme.fontSizeXs
                            font.family: Theme.monoFont
                            color: Theme.textMuted
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 26
                        radius: 4
                        color: root.testErrorText ? Qt.rgba(1, 0, 0, 0.15) :
                               root.testSuccess ? Qt.rgba(0, 0.8, 0.2, 0.15) :
                               Theme.bgElevated
                        border.width: 1
                        border.color: root.testErrorText ? Theme.accentWarn :
                                     root.testSuccess ? Theme.accentSuccess :
                                     Theme.borderSubtle

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8

                            Label {
                                Layout.fillWidth: true
                                text: root.testErrorText ? ("❌ Помилка: " + root.testErrorText) :
                                      root.testResultText ? ("✓ Результат: " + root.testResultText) :
                                      "Натисніть «Перевірити скрипт», щоб побачити вихідне значення"
                                font.pixelSize: Theme.fontSizeSm
                                font.family: Theme.monoFont
                                color: root.testErrorText ? Theme.accentWarn :
                                       root.testSuccess ? Theme.accentSuccess :
                                       Theme.textSecondary
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }
            }
        }

        // Footer Actions
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Item { Layout.fillWidth: true }

            AppButton {
                text: "Скасувати"
                variant: "ghost"
                onClicked: root.close()
            }

            AppButton {
                text: "Зберегти скрипти"
                variant: "primary"
                onClicked: root.saveConfig()
            }
        }
    }
}

