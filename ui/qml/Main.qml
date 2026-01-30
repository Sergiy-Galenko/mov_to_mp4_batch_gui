import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "components"

ApplicationWindow {
    id: root
    visible: true
    visibility: Window.Maximized
    title: backend.appTitle
    color: Theme.bg

    palette.window: Theme.bg
    palette.base: Theme.input
    palette.text: Theme.text
    palette.button: Theme.panel
    palette.buttonText: Theme.text
    palette.highlight: Theme.accent
    palette.highlightedText: "#FFFFFF"

    property bool compact: contentWrap.width < Theme.compactBreakpoint
    property var selectedQueue: []
    property var portraitOptions: [
        "Вимкнено",
        "9:16 (1080x1920) - crop",
        "9:16 (1080x1920) - blur",
        "9:16 (720x1280) - crop",
        "9:16 (720x1280) - blur"
    ]
    property int currentTab: 0
    property var operationTabs: [
        "Основні",
        "Редагування",
        "Пресети",
        "Покращення",
        "Метадані"
    ]
    property var positionOptions: [
        "Верх-ліворуч",
        "Верх-праворуч",
        "Низ-ліворуч",
        "Низ-праворуч",
        "Центр"
    ]

    function toggleQueueIndex(idx, checked) {
        var pos = selectedQueue.indexOf(idx)
        if (checked && pos === -1) {
            selectedQueue.push(idx)
        } else if (!checked && pos !== -1) {
            selectedQueue.splice(pos, 1)
        }
    }

    function collectSettings() {
        return {
            out_video_fmt: outVideoFmt.currentText,
            out_image_fmt: outImageFmt.currentText,
            crf: crfSpin.value,
            preset: presetCombo.currentText,
            portrait: portraitCombo.currentText,
            img_quality: imgQualitySpin.value,
            overwrite: overwriteCheck.checked,
            fast_copy: fastCopyCheck.checked,
            trim_start: trimStartField.text,
            trim_end: trimEndField.text,
            merge: mergeCheck.checked,
            merge_name: mergeNameField.text,
            resize_w: resizeWField.text,
            resize_h: resizeHField.text,
            crop_w: cropWField.text,
            crop_h: cropHField.text,
            crop_x: cropXField.text,
            crop_y: cropYField.text,
            rotate: rotateCombo.currentText,
            speed: speedField.text,
            wm_path: wmPathField.text,
            wm_pos: wmPosCombo.currentText,
            wm_opacity: wmOpacitySpin.value,
            wm_scale: wmScaleSpin.value,
            text_wm: textWatermarkField.text,
            text_pos: textPosCombo.currentText,
            text_size: textSizeSpin.value,
            text_color: textColorField.text,
            text_box: textBoxCheck.checked,
            text_box_color: textBoxColorField.text,
            text_box_opacity: textBoxOpacitySpin.value,
            text_font: textFontField.text,
            codec: codecCombo.currentText,
            hw: hwCombo.currentText,
            strip_metadata: stripMetadataCheck.checked,
            copy_metadata: copyMetadataCheck.checked,
            meta_title: metaTitleField.text,
            meta_comment: metaCommentField.text,
            meta_author: metaAuthorField.text,
            meta_copyright: metaCopyrightField.text
        }
    }

    function applyPreset(preset) {
        if (!preset)
            return
        if (preset.out_video_fmt) outVideoFmt.currentText = preset.out_video_fmt
        if (preset.out_image_fmt) outImageFmt.currentText = preset.out_image_fmt
        if (preset.crf !== undefined) crfSpin.value = preset.crf
        if (preset.preset) presetCombo.currentText = preset.preset
        if (preset.portrait) portraitCombo.currentText = preset.portrait
        if (preset.img_quality !== undefined) imgQualitySpin.value = preset.img_quality
        overwriteCheck.checked = !!preset.overwrite
        fastCopyCheck.checked = !!preset.fast_copy
        trimStartField.text = preset.trim_start || ""
        trimEndField.text = preset.trim_end || ""
        mergeCheck.checked = !!preset.merge
        mergeNameField.text = preset.merge_name || "merged"
        resizeWField.text = preset.resize_w || ""
        resizeHField.text = preset.resize_h || ""
        cropWField.text = preset.crop_w || ""
        cropHField.text = preset.crop_h || ""
        cropXField.text = preset.crop_x || ""
        cropYField.text = preset.crop_y || ""
        rotateCombo.currentText = preset.rotate || rotateCombo.currentText
        speedField.text = preset.speed || "1.0"
        wmPathField.text = preset.wm_path || ""
        wmPosCombo.currentText = preset.wm_pos || wmPosCombo.currentText
        if (preset.wm_opacity !== undefined) wmOpacitySpin.value = preset.wm_opacity
        if (preset.wm_scale !== undefined) wmScaleSpin.value = preset.wm_scale
        textWatermarkField.text = preset.text_wm || ""
        textPosCombo.currentText = preset.text_pos || textPosCombo.currentText
        if (preset.text_size !== undefined) textSizeSpin.value = preset.text_size
        textColorField.text = preset.text_color || "white"
        textBoxCheck.checked = !!preset.text_box
        textBoxColorField.text = preset.text_box_color || "black"
        if (preset.text_box_opacity !== undefined) textBoxOpacitySpin.value = preset.text_box_opacity
        textFontField.text = preset.text_font || ""
        codecCombo.currentText = preset.codec || codecCombo.currentText
        hwCombo.currentText = preset.hw || hwCombo.currentText
        stripMetadataCheck.checked = !!preset.strip_metadata
        copyMetadataCheck.checked = !!preset.copy_metadata
        metaTitleField.text = preset.meta_title || ""
        metaCommentField.text = preset.meta_comment || ""
        metaAuthorField.text = preset.meta_author || ""
        metaCopyrightField.text = preset.meta_copyright || ""
    }

    Connections {
        target: backend
        function onLogAdded(level, msg) {
            logArea.text += "[" + new Date().toLocaleTimeString() + "] " + level + ": " + msg + "\n"
            logArea.cursorPosition = logArea.text.length
        }
        function onPresetLoaded(preset) {
            applyPreset(preset)
        }
        function onWatermarkPicked(path) {
            wmPathField.text = path
        }
        function onFontPicked(path) {
            textFontField.text = path
        }
    }

    Component.onCompleted: backend.refreshEncoders()

    ScrollView {
        id: contentWrap
        anchors.fill: parent
        anchors.margins: Theme.space3
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        background: Rectangle { color: "transparent" }

        contentItem: Flickable {
            id: contentFlick
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: contentHost.width
            contentHeight: contentHost.implicitHeight

            Item {
                id: contentHost
                width: contentFlick.width
                implicitHeight: contentColumn.implicitHeight

                ColumnLayout {
                    id: contentColumn
                    width: Math.min(contentHost.width, Theme.maxWidth)
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Theme.space3

                    Card {
                        id: headerCard
                        ColumnLayout {
                            spacing: Theme.space2
                            Label {
                                text: backend.appTitle
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                color: Theme.text
                            }
                            Label {
                                text: "Пакетна конвертація відео та фото через FFmpeg."
                                color: Theme.muted
                            }
                            GridLayout {
                                columns: root.compact ? 1 : 4
                                columnSpacing: Theme.space2
                                rowSpacing: Theme.space1
                                Label { text: "FFmpeg:"; color: Theme.text }
                                AppTextField {
                                    id: ffmpegField
                                    text: backend.ffmpegPath
                                    Layout.fillWidth: true
                                    onEditingFinished: backend.ffmpegPath = text
                                }
                                SecondaryButton { text: "Вказати"; onClicked: backend.pickFfmpeg() }
                                GhostButton { text: "Перевірити"; onClicked: backend.refreshEncoders() }
                            }
                            Flow {
                                Layout.fillWidth: true
                                spacing: Theme.space1
                                Repeater {
                                    model: root.operationTabs
                                    delegate: Rectangle {
                                        radius: 10
                                        color: index === root.currentTab ? Theme.accent : Theme.panel
                                        border.color: Theme.border
                                        height: 32
                                        implicitWidth: tabLabel.implicitWidth + Theme.space2 * 2
                                        Label {
                                            id: tabLabel
                                            anchors.centerIn: parent
                                            text: modelData
                                            color: index === root.currentTab ? "#FFFFFF" : Theme.text
                                            font.pixelSize: 12
                                            font.weight: Font.Medium
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: root.currentTab = index
                                        }
                                    }
                                }
                            }
                        }
                    }

            GridLayout {
                id: mainGrid
                columns: root.compact ? 1 : 2
                columnSpacing: Theme.space2
                rowSpacing: Theme.space2
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: Theme.space2

                    Card {
                        title: "Черга"
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: Theme.space1
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 220
                                background: Rectangle { color: "transparent" }
                                ListView {
                                    id: queueList
                                    model: backend.queueModel
                                    clip: true
                                    spacing: 6
                                    delegate: Rectangle {
                                        width: ListView.view.width
                                        height: 36
                                        radius: 8
                                        color: ListView.isCurrentItem ? Theme.hover : "transparent"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            spacing: 8
                                            AppCheckBox {
                                                checked: selectedQueue.indexOf(index) !== -1
                                                onToggled: toggleQueueIndex(index, checked)
                                            }
                                            Label {
                                                text: model.display
                                                color: Theme.text
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                        }
                                        TapHandler {
                                            onTapped: {
                                                queueList.currentIndex = index
                                                backend.selectQueueIndex(index)
                                            }
                                        }
                                    }
                                }
                            }
                            GridLayout {
                                columns: root.compact ? 1 : 2
                                columnSpacing: Theme.space1
                                rowSpacing: Theme.space1
                                SecondaryButton { text: "Додати файли"; onClicked: backend.addFiles() }
                                SecondaryButton { text: "Додати папку"; onClicked: backend.addFolder() }
                                GhostButton { text: "Видалити вибрані"; onClicked: { backend.removeSelected(selectedQueue); selectedQueue = [] } }
                                GhostButton { text: "Очистити"; onClicked: { backend.clearQueue(); selectedQueue = [] } }
                            }
                        }
                    }

                    Card {
                        title: "Вивід"
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: Theme.space1
                            AppTextField {
                                id: outputDirField
                                text: backend.outputDir
                                onEditingFinished: backend.outputDir = text
                            }
                            RowLayout {
                                spacing: Theme.space1
                                Layout.fillWidth: true
                                SecondaryButton { text: "Вибрати"; onClicked: backend.pickOutputDir() }
                                GhostButton { text: "Відкрити папку"; onClicked: backend.openOutputDir() }
                                Item { Layout.fillWidth: true }
                            }
                        }
                    }

                    Card {
                        title: "Інформація"
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: Theme.space1
                            RowLayout { Label { text: "Файл:"; color: Theme.muted } Label { text: backend.infoName; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Тривалість:"; color: Theme.muted } Label { text: backend.infoDuration; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Кодеки:"; color: Theme.muted } Label { text: backend.infoCodec; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Роздільність:"; color: Theme.muted } Label { text: backend.infoRes; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Розмір:"; color: Theme.muted } Label { text: backend.infoSize; color: Theme.text; Layout.fillWidth: true } }
                            RowLayout { Label { text: "Контейнер:"; color: Theme.muted } Label { text: backend.infoContainer; color: Theme.text; Layout.fillWidth: true } }
                        }
                    }

                    Card {
                        title: "Дії"
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: Theme.space1
                            PrimaryButton { text: "Старт"; enabled: !backend.isRunning; onClicked: backend.startConversion(collectSettings()) }
                            SecondaryButton { text: "Стоп"; enabled: backend.isRunning; onClicked: backend.stopConversion() }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: Theme.space2

                    Card {
                        title: "Налаштування"
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: Theme.space2
                            Layout.fillWidth: true
                            StackLayout {
                                id: settingsStack
                                Layout.fillWidth: true
                                currentIndex: root.currentTab

                                Item {
                                    implicitWidth: basicLayout.implicitWidth
                                    implicitHeight: basicLayout.implicitHeight
                                    ColumnLayout {
                                        id: basicLayout
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                            Section {
                                                title: "Відео"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Формат:"; color: Theme.muted }
                                                    AppComboBox { id: outVideoFmt; model: ["mp4", "mkv", "webm", "mov", "avi", "gif"] }
                                                    Label { text: "CRF:"; color: Theme.muted }
                                                    AppSpinBox { id: crfSpin; from: 14; to: 35; value: 23 }
                                                    Label { text: "Preset:"; color: Theme.muted }
                                                    AppComboBox { id: presetCombo; model: ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"] }
                                                    Label { text: "Портрет:"; color: Theme.muted }
                                                    AppComboBox {
                                                        id: portraitCombo
                                                        model: root.portraitOptions
                                                    }
                                                }
                                            }

                                            Section {
                                                title: "Кодеки та GPU"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Кодек відео:"; color: Theme.muted }
                                                    AppComboBox { id: codecCombo; model: ["Авто", "H.264 (AVC)", "H.265 (HEVC)", "AV1", "VP9 (WebM)"] }
                                                    Label { text: "GPU/CPU:"; color: Theme.muted }
                                                    AppComboBox { id: hwCombo; model: ["Авто", "Тільки CPU", "NVIDIA (NVENC)", "Intel (QSV)", "AMD (AMF)"] }
                                                    Label { text: backend.encoderInfo; color: Theme.muted; Layout.columnSpan: root.compact ? 1 : 2 }
                                                }
                                            }

                                            Section {
                                                title: "Фото"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Формат:"; color: Theme.muted }
                                                    AppComboBox { id: outImageFmt; model: ["jpg", "png", "webp", "bmp", "tiff"] }
                                                    Label { text: "Якість (1–100):"; color: Theme.muted }
                                                    AppSpinBox { id: imgQualitySpin; from: 1; to: 100; value: 90 }
                                                }
                                            }

                                            Section {
                                                title: "Поведінка"
                                                ColumnLayout {
                                                    spacing: Theme.space1
                                                    AppCheckBox { id: overwriteCheck; text: "Перезаписувати існуючі файли" }
                                                    AppCheckBox { id: fastCopyCheck; text: "Fast copy (без перекодування, якщо можливо)" }
                                                }
                                            }
                                        }
                                    }

                                Item {
                                    implicitWidth: editLayout.implicitWidth
                                    implicitHeight: editLayout.implicitHeight
                                    ColumnLayout {
                                        id: editLayout
                                        anchors.fill: parent
                                        spacing: Theme.space2

                                            Section {
                                                title: "Час / Merge"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Початок (hh:mm:ss або сек):"; color: Theme.muted; wrapMode: Text.WordWrap }
                                                    AppTextField { id: trimStartField }
                                                    Label { text: "Кінець (hh:mm:ss або сек):"; color: Theme.muted; wrapMode: Text.WordWrap }
                                                    AppTextField { id: trimEndField }
                                                    AppCheckBox { id: mergeCheck; text: "Об'єднати всі відео в один файл"; Layout.columnSpan: root.compact ? 1 : 2 }
                                                    Label { text: "Назва файлу:"; color: Theme.muted }
                                                    AppTextField {
                                                        id: mergeNameField
                                                        text: "merged"
                                                    }
                                                }
                                            }

                                            Section {
                                                title: "Трансформації"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Resize W:"; color: Theme.muted }
                                                    AppTextField { id: resizeWField }
                                                    Label { text: "H:"; color: Theme.muted }
                                                    AppTextField { id: resizeHField }
                                                    Label { text: "Crop W:"; color: Theme.muted }
                                                    AppTextField { id: cropWField }
                                                    Label { text: "H:"; color: Theme.muted }
                                                    AppTextField { id: cropHField }
                                                    Label { text: "X:"; color: Theme.muted }
                                                    AppTextField { id: cropXField }
                                                    Label { text: "Y:"; color: Theme.muted }
                                                    AppTextField { id: cropYField }
                                                    Label { text: "Поворот:"; color: Theme.muted }
                                                    AppComboBox { id: rotateCombo; model: ["0", "90° вправо", "90° вліво", "180°"] }
                                                    Label { text: "Speed:"; color: Theme.muted }
                                                    AppTextField { id: speedField; text: "1.0" }
                                                }
                                            }

                                            Section {
                                                title: "Водяний знак"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Файл:"; color: Theme.muted }
                                                    RowLayout {
                                                        spacing: Theme.space1
                                                        Layout.fillWidth: true
                                                        AppTextField { id: wmPathField; Layout.fillWidth: true }
                                                        SecondaryButton { text: "Вибрати"; onClicked: backend.pickWatermark() }
                                                    }
                                                    Label { text: "Scale %:"; color: Theme.muted }
                                                    AppSpinBox { id: wmScaleSpin; from: 1; to: 200; value: 30 }
                                                    Label { text: "Opacity %:"; color: Theme.muted }
                                                    AppSpinBox { id: wmOpacitySpin; from: 0; to: 100; value: 80 }
                                                    Label { text: "Позиція:"; color: Theme.muted }
                                                    AppComboBox { id: wmPosCombo; model: root.positionOptions }
                                                }
                                            }

                                            Section {
                                                title: "Текст"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Текст:"; color: Theme.muted }
                                                    AppTextField { id: textWatermarkField }
                                                    Label { text: "Розмір:"; color: Theme.muted }
                                                    AppSpinBox { id: textSizeSpin; from: 8; to: 120; value: 24 }
                                                    Label { text: "Колір:"; color: Theme.muted }
                                                    RowLayout {
                                                        spacing: Theme.space1
                                                        Layout.fillWidth: true
                                                        AppTextField { id: textColorField; text: "white"; Layout.fillWidth: true }
                                                        GhostButton { text: "..."; onClicked: textColorField.text = textColorField.text }
                                                    }
                                                    Label { text: "Позиція:"; color: Theme.muted }
                                                    AppComboBox { id: textPosCombo; model: root.positionOptions }
                                                    Label { text: "Шрифт (.ttf):"; color: Theme.muted }
                                                    RowLayout {
                                                        spacing: Theme.space1
                                                        Layout.fillWidth: true
                                                        AppTextField { id: textFontField; Layout.fillWidth: true }
                                                        SecondaryButton { text: "Вибрати"; onClicked: backend.pickFont() }
                                                    }
                                                    AppCheckBox {
                                                        id: textBoxCheck
                                                        text: "Фон тексту"
                                                        Layout.columnSpan: root.compact ? 1 : 2
                                                    }
                                                    Label { text: "Колір:"; color: Theme.muted }
                                                    RowLayout {
                                                        spacing: Theme.space1
                                                        Layout.fillWidth: true
                                                        AppTextField { id: textBoxColorField; text: "black"; Layout.fillWidth: true }
                                                        GhostButton { text: "..."; onClicked: textBoxColorField.text = textBoxColorField.text }
                                                    }
                                                    Label { text: "Opacity %:"; color: Theme.muted }
                                                    AppSpinBox { id: textBoxOpacitySpin; from: 0; to: 100; value: 50 }
                                                }
                                            }
                                        }
                                    }

                                Item {
                                    implicitWidth: presetLayout.implicitWidth
                                    implicitHeight: presetLayout.implicitHeight
                                    ColumnLayout {
                                        id: presetLayout
                                        anchors.fill: parent
                                        spacing: Theme.space2
                                            Section {
                                                title: "Пресети"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 2
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label { text: "Збережені:"; color: Theme.muted }
                                                    AppComboBox { id: presetsCombo; model: backend.presetsModel }
                                                    RowLayout {
                                                        Layout.columnSpan: root.compact ? 1 : 2
                                                        spacing: Theme.space1
                                                        Layout.fillWidth: true
                                                        SecondaryButton { text: "Завантажити"; onClicked: backend.loadPreset(presetsCombo.currentText) }
                                                        GhostButton { text: "Видалити"; onClicked: backend.deletePreset(presetsCombo.currentText) }
                                                    }
                                                    Label { text: "Назва нового:"; color: Theme.muted }
                                                    AppTextField { id: newPresetField }
                                                    PrimaryButton {
                                                        text: "Зберегти"
                                                        Layout.columnSpan: root.compact ? 1 : 2
                                                        onClicked: backend.savePreset(newPresetField.text, collectSettings())
                                                    }
                                                }
                                            }
                                        }
                                    }

                                Item {
                                    implicitWidth: enhanceLayout.implicitWidth
                                    implicitHeight: enhanceLayout.implicitHeight
                                    ColumnLayout {
                                        id: enhanceLayout
                                        anchors.fill: parent
                                        spacing: Theme.space2
                                            Section {
                                                title: "Покращення"
                                                GridLayout {
                                                    columns: root.compact ? 1 : 3
                                                    columnSpacing: Theme.space2
                                                    rowSpacing: Theme.space1
                                                    Label {
                                                        text: "Обери цільову роздільність для upscale:"
                                                        color: Theme.muted
                                                        Layout.columnSpan: root.compact ? 1 : 3
                                                        wrapMode: Text.WordWrap
                                                        Layout.fillWidth: true
                                                    }
                                                    Repeater {
                                                        model: [
                                                            ["360p (640x360)", 640, 360],
                                                            ["480p (854x480)", 854, 480],
                                                            ["540p (960x540)", 960, 540],
                                                            ["720p (1280x720)", 1280, 720],
                                                            ["900p (1600x900)", 1600, 900],
                                                            ["1080p (1920x1080)", 1920, 1080],
                                                            ["1440p (2560x1440)", 2560, 1440],
                                                            ["4K (3840x2160)", 3840, 2160],
                                                            ["8K (7680x4320)", 7680, 4320],
                                                            ["16K (15360x8640)", 15360, 8640]
                                                        ]
                                                        delegate: SecondaryButton {
                                                            text: "До " + modelData[0]
                                                            onClicked: {
                                                                resizeWField.text = modelData[1]
                                                                resizeHField.text = modelData[2]
                                                            }
                                                        }
                                                    }
                                                }
                                                Label {
                                                    text: "Порада: апскейл збільшує розмір/час. Використовуй адекватні параметри CRF і кодеки (H.265/AV1)."
                                                    color: Theme.muted
                                                    wrapMode: Text.WordWrap
                                                }
                                            }
                                        }
                                    }

                                Item {
                                    implicitWidth: metaLayout.implicitWidth
                                    implicitHeight: metaLayout.implicitHeight
                                    ColumnLayout {
                                        id: metaLayout
                                        anchors.fill: parent
                                        spacing: Theme.space2
                                            Section {
                                                title: "Метадані"
                                                ColumnLayout {
                                                    spacing: Theme.space1
                                                    AppCheckBox { id: copyMetadataCheck; text: "Копіювати метадані з джерела"; checked: true }
                                                    AppCheckBox { id: stripMetadataCheck; text: "Очистити метадані" }
                                                    GridLayout {
                                                        columns: root.compact ? 1 : 2
                                                        columnSpacing: Theme.space2
                                                        rowSpacing: Theme.space1
                                                        Label { text: "Title:"; color: Theme.muted }
                                                        AppTextField { id: metaTitleField }
                                                        Label { text: "Author:"; color: Theme.muted }
                                                        AppTextField { id: metaAuthorField }
                                                        Label { text: "Comment:"; color: Theme.muted }
                                                        AppTextField { id: metaCommentField }
                                                        Label { text: "Copyright:"; color: Theme.muted }
                                                        AppTextField { id: metaCopyrightField }
                                                    }
                                                }
                                            }
                                        }
                                }
                            }
                        }
                    }

                    Card {
                        title: "Лог"
                        Layout.fillWidth: true
                        AppTextArea {
                            id: logArea
                            readOnly: true
                            textFormat: Text.PlainText
                            wrapMode: TextEdit.NoWrap
                            Layout.preferredHeight: 180
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                GridLayout {
                    columns: root.compact ? 1 : 5
                    columnSpacing: Theme.space2
                    rowSpacing: Theme.space1
                    Label { text: backend.statusText; color: Theme.text }
                    ProgressBar { from: 0; to: 1; value: backend.fileProgress; Layout.fillWidth: true }
                    Label { text: backend.fileProgressText; color: Theme.muted }
                    ProgressBar { from: 0; to: 1; value: backend.totalProgress; Layout.fillWidth: true }
                    Label { text: backend.totalProgressText; color: Theme.muted }
                }
            }
        }
    }
}
}
}
