import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"
Rectangle {
    id: root; property var editor
    readonly property var item: editor.selected
    readonly property var cropAspectValues: ["free", "16:9", "9:16", "4:3", "1:1", "21:9"]
    readonly property var transitionValues: ["none", "fade", "dissolve", "wipeleft", "wiperight", "slideup", "slidedown", "circlecrop"]
    color: EditorTheme.panel; clip: true
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { Layout.fillWidth: true; text: I18n.t(editor.inspectorTab === 4 ? "editor.deliver" : "editor.inspector"); color: EditorTheme.text; font.pixelSize: EditorTheme.fontSize+1; font.bold: true }
            EditorButton { iconOnly: true; iconName: "close"; text: I18n.t("close"); onClicked: editor.inspectorVisible = false }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: EditorTheme.controlHeight + EditorTheme.space1 * 2
            visible: editor.inspectorTab < 3
            radius: EditorTheme.radiusControl
            color: EditorTheme.bgElevated
            border.width: 1
            border.color: EditorTheme.borderSubtle
            RowLayout {
                anchors.fill: parent; anchors.margins: EditorTheme.space1; spacing: EditorTheme.space1
                Repeater {
                    model: ["video", "audio", "title"]
                    EditorButton {
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        text: I18n.t("editor." + modelData)
                        variant: "segmented"
                        checked: editor.inspectorTab === index
                        onClicked: editor.inspectorTab = index
                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: item.name || item.text || ""; elide: Text.ElideMiddle; color: EditorTheme.secondary; font.pixelSize: EditorTheme.smallSize; visible: !!item.id && editor.inspectorTab < 3 }
        ScrollView {
            id: scroll; Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: scroll.availableWidth; spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; visible: !item.id && editor.inspectorTab < 3; spacing: 12
                    AppIcon { name: "sliders"; Layout.preferredWidth: 32; Layout.preferredHeight: 32; iconColor: EditorTheme.muted; Layout.alignment: Qt.AlignHCenter }
                    Label { Layout.fillWidth: true; text: I18n.t("editor.no_selection"); color: EditorTheme.text; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                    Label { Layout.fillWidth: true; text: I18n.t("editor.select_hint"); color: EditorTheme.secondary; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                    EditorButton { Layout.fillWidth: true; text: I18n.t("editor.project_settings"); onClicked: editor.editProjectSettings() }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 12; visible: item.kind === "video" && editor.inspectorTab === 0
                    enabled: !editor.doc.tracks.video_locked
                    InspectorSection {
                        title: I18n.t("editor.clip_range")
                        GridLayout {
                            columns: 2; Layout.fillWidth: true; columnSpacing: 12; rowSpacing: 8
                            Label { text: I18n.t("editor.in"); color: EditorTheme.secondary }
                            EditorNumber { objectName: "editorInField"; Layout.fillWidth: true; decimals: 3; maximum: Math.max(0, editor.outPoint-1/editor.fps); value: editor.inPoint; onEdited: function(number) { editor.inPoint = number } }
                            Label { text: I18n.t("editor.out"); color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; decimals: 3; minimum: editor.inPoint+1/editor.fps; maximum: item.media_type === "image" ? 3600 : (item.source_duration || 1); value: editor.outPoint; onEdited: function(number) { editor.outPoint = number } }
                        }
                        Label { Layout.fillWidth: true; text: editor.timecode(editor.outPoint-editor.inPoint); font.family: Theme.monoFont; color: EditorTheme.muted }
                    }
                    InspectorSection {
                        title: I18n.t("editor.crop")
                        RowLayout {
                            Layout.fillWidth: true
                            Label { Layout.fillWidth: true; text: I18n.t("editor.enabled"); color: EditorTheme.secondary }
                            Switch { checked: editor.cropEnabled; onToggled: editor.cropEnabled = checked }
                        }
                        EditorCombo { Layout.fillWidth: true; model: [I18n.t("editor.free"), "16:9", "9:16", "4:3", "1:1", "21:9"]; currentIndex: Math.max(0, root.cropAspectValues.indexOf(editor.cropAspect)); onActivated: { editor.cropAspect = root.cropAspectValues[currentIndex]; editor.cropOverlayVisible = true } }
                        GridLayout {
                            columns: 4; Layout.fillWidth: true; columnSpacing: 8; rowSpacing: 8
                            Label { text: "X"; color: EditorTheme.secondary }
                            EditorNumber { objectName: "editorCropX"; Layout.fillWidth: true; implicitWidth: 70; value: editor.cropX; maximum: Math.max(0, editor.nativeWidth-editor.cropW); onEdited: function(number) { editor.cropX = number; editor.cropEnabled = true } }
                            Label { text: "Y"; color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; implicitWidth: 70; value: editor.cropY; maximum: Math.max(0, editor.nativeHeight-editor.cropH); onEdited: function(number) { editor.cropY = number; editor.cropEnabled = true } }
                            Label { text: "W"; color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; implicitWidth: 70; value: editor.cropW; minimum: 2; maximum: editor.nativeWidth-editor.cropX; onEdited: function(number) { editor.cropW = number; editor.cropEnabled = true } }
                            Label { text: "H"; color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; implicitWidth: 70; value: editor.cropH; minimum: 2; maximum: editor.nativeHeight-editor.cropY; onEdited: function(number) { editor.cropH = number; editor.cropEnabled = true } }
                        }
                        EditorButton { Layout.fillWidth: true; text: I18n.t("editor.reset_crop"); iconName: "refresh"; onClicked: editor.resetCrop() }
                    }
                    InspectorSection {
                        title: I18n.t("editor.transitions"); expanded: false
                        EditorCombo { Layout.fillWidth: true; model: [I18n.t("editor.transition_cut"), I18n.t("editor.transition_fade"), I18n.t("editor.transition_dissolve"), I18n.t("editor.transition_wipe_left"), I18n.t("editor.transition_wipe_right"), I18n.t("editor.transition_slide_up"), I18n.t("editor.transition_slide_down"), I18n.t("editor.transition_circle")]; currentIndex: Math.max(0, root.transitionValues.indexOf(item.transition_to_next)); onActivated: editor.project.editSelected({transition_to_next: root.transitionValues[currentIndex]}) }
                        RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: I18n.t("editor.duration"); color: EditorTheme.secondary } EditorNumber { value: item.transition_duration || .5; decimals: 2; minimum: .05; maximum: Math.min(5, (editor.outPoint-editor.inPoint)/2); onEdited: function(number) { editor.project.editSelected({transition_duration: number}) } } }
                    }
                    InspectorSection {
                        title: I18n.t("editor.transform"); expanded: false
                        Label { Layout.fillWidth: true; text: I18n.t("editor.transform_unavailable"); color: EditorTheme.muted; wrapMode: Text.Wrap }
                        EditorButton { Layout.fillWidth: true; text: I18n.t("editor.scale_rotation"); enabled: false; hint: I18n.t("editor.transform_unavailable") }
                    }
                    InspectorSection {
                        title: I18n.t("editor.tools"); expanded: false
                        EditorButton { Layout.fillWidth: true; text: I18n.t("editor.smart_reframe"); enabled: !(editor.project && editor.project.analysis && editor.project.analysis.busy); onClicked: editor.project.analyze("reframe", editor.filePath, {aspect: "9:16"}) }
                        EditorButton { Layout.fillWidth: true; text: I18n.t("editor.track_blur"); enabled: !(editor.project && editor.project.analysis && editor.project.analysis.busy); onClicked: editor.project.analyze("blur", editor.filePath, {bbox: [editor.cropX,editor.cropY,editor.cropW,editor.cropH], target: "face", style: "box"}) }
                        Label { Layout.fillWidth: true; text: I18n.t("editor.tracking_hint"); wrapMode: Text.Wrap; color: EditorTheme.muted; font.pixelSize: EditorTheme.smallSize }
                        EditorButton { Layout.fillWidth: true; text: I18n.t("studio.title"); onClicked: editor.openTools() }
                        EditorButton { Layout.fillWidth: true; text: I18n.t("editor.apply_queue"); enabled: !!editor.filePath; onClicked: editor.applyAndClose() }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; visible: editor.inspectorTab === 1 && !!item.id; enabled: !editor.doc.tracks.audio_locked
                    InspectorSection {
                        title: I18n.t("editor.audio")
                        RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: I18n.t("editor.enabled"); color: EditorTheme.secondary } Switch { checked: item.kind === "audio" ? !editor.doc.tracks.music_muted : editor.audioEnabled; onToggled: item.kind === "audio" ? editor.project.updateSection("tracks", {music_muted: !checked}) : editor.audioEnabled = checked } }
                        Label { Layout.fillWidth: true; text: item.kind === "audio" ? item.name || I18n.t("editor.audio") : I18n.t("editor.original_audio"); color: EditorTheme.secondary; elide: Text.ElideMiddle }
                        ColumnLayout {
                            Layout.fillWidth: true; visible: item.kind === "audio"
                            RowLayout { Layout.fillWidth: true; Label { text: I18n.t("editor.volume"); color: EditorTheme.secondary } Slider { Layout.fillWidth: true; from: 0; to: 2; value: item.volume === undefined ? 1 : item.volume; onMoved: editor.project.editSelected({volume: value}) } Label { text: Math.round((item.volume || 0)*100)+"%"; color: EditorTheme.text } }
                            RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: I18n.t("editor.loop"); color: EditorTheme.secondary } Switch { checked: !!item.loop; onToggled: editor.project.editSelected({loop: checked}) } }
                            RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: I18n.t("editor.ducking"); color: EditorTheme.secondary } Switch { checked: !!item.ducking; onToggled: editor.project.editSelected({ducking: checked}) } }
                            RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: I18n.t("editor.offset"); color: EditorTheme.secondary } EditorNumber { decimals: 2; value: item.offset || 0; onEdited: function(number) { editor.project.editSelected({offset: number}) } } }
                        }
                        EditorButton { Layout.fillWidth: true; text: I18n.t("editor.import_audio"); onClicked: editor.project.chooseMedia() }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; visible: editor.inspectorTab === 2 && item.kind === "title"; enabled: !editor.doc.tracks.titles_locked
                    InspectorSection {
                        title: I18n.t("editor.title")
                        TextArea { objectName: "editorTitleText"; Layout.fillWidth: true; Layout.preferredHeight: 100; text: item.text || ""; color: EditorTheme.text; wrapMode: TextEdit.Wrap; selectByMouse: true; background: Rectangle { color: EditorTheme.background; border.color: EditorTheme.border; radius: 4 } onTextChanged: if (activeFocus && text !== item.text) editor.project.editSelected({text: text}) }
                        EditorField { Layout.fillWidth: true; text: item.font || "Arial"; onEditingFinished: editor.project.editSelected({font: text}) }
                        GridLayout {
                            Layout.fillWidth: true; columns: 2; columnSpacing: 8; rowSpacing: 8
                            Label { text: I18n.t("editor.size"); color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; value: item.size || 48; minimum: 8; maximum: 400; onEdited: function(number) { editor.project.editSelected({size: number}) } }
                            Label { text: I18n.t("editor.bold"); color: EditorTheme.secondary }
                            Switch { checked: !!item.bold; onToggled: editor.project.editSelected({bold: checked}) }
                            Label { text: I18n.t("editor.color"); color: EditorTheme.secondary }
                            EditorField { Layout.fillWidth: true; text: item.color || "#ffffff"; validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ } onEditingFinished: if (acceptableInput) editor.project.editSelected({color: text}) }
                            Label { text: "X %"; color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; value: (item.x || 0)*100; maximum: 100; onEdited: function(number) { editor.project.editSelected({x: number/100}) } }
                            Label { text: "Y %"; color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; value: (item.y || 0)*100; maximum: 100; onEdited: function(number) { editor.project.editSelected({y: number/100}) } }
                            Label { text: I18n.t("editor.opacity"); color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; value: (item.opacity === undefined ? 1 : item.opacity)*100; maximum: 100; onEdited: function(number) { editor.project.editSelected({opacity: number/100}) } }
                            Label { text: I18n.t("editor.background"); color: EditorTheme.secondary }
                            Switch { checked: !!item.background; onToggled: editor.project.editSelected({background: checked}) }
                            Label { text: I18n.t("editor.in"); color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; decimals: 2; maximum: Math.max(0, (item.end || 1)-.01); value: item.start || 0; onEdited: function(number) { editor.project.editSelected({start: number}) } }
                            Label { text: I18n.t("editor.out"); color: EditorTheme.secondary }
                            EditorNumber { Layout.fillWidth: true; decimals: 2; minimum: (item.start || 0)+.01; value: item.end || 3; onEdited: function(number) { editor.project.editSelected({end: number}) } }
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; visible: editor.inspectorTab === 3
                    InspectorSection {
                        title: I18n.t("editor.color")
                        Label { Layout.fillWidth: true; text: I18n.t("editor.color_unavailable"); color: EditorTheme.secondary; wrapMode: Text.Wrap }
                        Repeater { model: ["exposure","contrast","saturation"]; RowLayout { required property string modelData; Layout.fillWidth: true; Label { Layout.fillWidth: true; text: I18n.t("editor." + modelData); color: EditorTheme.muted } EditorNumber { enabled: false; value: 0 } } }
                    }
                }
                EditorExportPanel { editor: root.editor; Layout.fillWidth: true; visible: editor.inspectorTab === 4 }
                ColumnLayout {
                    Layout.fillWidth: true; visible: editor.project && editor.project.offline.length > 0
                    Label { text: I18n.t("editor.media_offline"); color: EditorTheme.danger; font.bold: true }
                    Repeater { model: editor.project ? editor.project.offline : []; EditorButton { required property var modelData; Layout.fillWidth: true; text: I18n.t("editor.locate") + ": " + modelData.name; onClicked: editor.project.locate(modelData.path) } }
                }
                Label { Layout.fillWidth: true; visible: !!(editor.project && editor.project.analysis && editor.project.analysis.busy); text: I18n.t("editor.analyzing"); color: EditorTheme.secondary }
                Label { Layout.fillWidth: true; visible: !!text; text: editor.project && editor.project.analysis ? editor.project.analysis.error : ""; wrapMode: Text.Wrap; color: EditorTheme.danger }
            }
        }
    }
}
