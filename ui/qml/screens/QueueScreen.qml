import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0
import "../components"
import "../layout" as AppLayout
import "../queue" as Queue

Item {
    id: root
    property var appRoot
    readonly property bool narrow: width < 1180
    readonly property bool hasSelection: appRoot && appRoot.selectedPaths.length > 0
    readonly property bool batchSelection: appRoot && appRoot.selectedPaths.length > 1

    function focusSearch() { queueSearchField.forceActiveFocus() }

    function clearSelection() {
        if (appRoot)
            appRoot.clearQueueSelection()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                color: Theme.windowBackground

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space4
                    anchors.rightMargin: Theme.space4
                    spacing: Theme.space2

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        spacing: 1
                        Label { Layout.fillWidth: true; text: appRoot ? appRoot.workspaceTitle() : I18n.t("nav_queue"); color: Theme.textPrimary; font.pixelSize: Theme.fontHeading; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        Label { text: backend ? backend.visibleQueueCount + " " + I18n.t("files") : "0 " + I18n.t("files"); color: Theme.textSecondary; font.pixelSize: Theme.fontMeta }
                    }

                    AppButton {
                        objectName: "addFilesButton"
                        iconName: "plus"
                        Layout.fillWidth: false
                        hoverEnabled: true
                        text: I18n.t("add_files")
                        onClicked: appRoot && appRoot.addFilesForWorkspace()
                    }

                    AppButton {
                        iconName: "folder"
                        visible: root.width > 800
                        Layout.fillWidth: false
                        hoverEnabled: true
                        text: I18n.t("add_folder")
                        onClicked: appRoot && appRoot.addFolderForWorkspace()
                    }

                    AppIconButton {
                        visible: root.narrow && root.hasSelection
                        iconName: "info"
                        accessibleLabel: I18n.t("selected_file")
                        onClicked: inspectorDrawer.open()
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderMuted }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.batchSelection ? 42 : 0
                visible: root.batchSelection
                color: Theme.selectionBackground
                border.width: 0

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space4
                    anchors.rightMargin: Theme.space3
                    spacing: Theme.space2
                    Label { text: I18n.t("selected") + ": " + (appRoot ? appRoot.selectedPaths.length : 0); color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; font.weight: Font.DemiBold }
                    AppButton { text: I18n.t("move_up"); implicitHeight: 28; onClicked: backend && backend.moveSelectedPathsUp(appRoot.selectedPaths) }
                    AppButton { text: I18n.t("move_down"); implicitHeight: 28; onClicked: backend && backend.moveSelectedPathsDown(appRoot.selectedPaths) }
                    AppButton { text: I18n.t("batch_override"); implicitHeight: 28; onClicked: appRoot && appRoot.openSidebarSection(5, "selected_override", appRoot.navIndexFor(5, "selected_override")) }
                    Item { Layout.fillWidth: true }
                    AppButton { text: I18n.t("batch_remove"); implicitHeight: 28; onClicked: appRoot && appRoot.removeSelectedPaths() }
                    AppIconButton { iconName: "close"; accessibleLabel: I18n.t("cancel"); onClicked: root.clearSelection() }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: backend && !backend.outputDirConfigured ? 42 : 0
                visible: backend && !backend.outputDirConfigured
                color: Theme.warningSoft
                border.width: 0
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space4
                    anchors.rightMargin: Theme.space4
                    spacing: Theme.space3
                    AppIcon { Layout.preferredWidth: 16; Layout.preferredHeight: 16; name: "info"; iconColor: Theme.warning }
                    Label { Layout.fillWidth: true; text: I18n.t("output_folder_required_detail"); color: Theme.textPrimary; font.pixelSize: Theme.fontSizeSm; elide: Text.ElideRight }
                    AppButton { text: I18n.t("choose"); implicitHeight: 28; onClicked: backend && backend.ensureOutputDirSelected() }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                color: Theme.panelBackground
                border.width: 0

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space4
                    anchors.rightMargin: Theme.space4
                    spacing: Theme.space2

                    AppTextField {
                        id: queueSearchField
                        search: true
                        objectName: "queueSearchField"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 320
                        Layout.minimumWidth: 120
                        placeholderText: I18n.t("queue_search")
                        Accessible.name: I18n.t("queue_search")
                        Keys.onEscapePressed: clear()
                        text: appRoot ? appRoot.queueSearchText : ""
                        onTextChanged: if (appRoot) appRoot.queueSearchText = text
                    }

                    AppIconButton {
                        visible: queueSearchField.text.length > 0
                        iconName: "close"
                        accessibleLabel: I18n.t("clear_search")
                        onClicked: { queueSearchField.clear(); queueSearchField.forceActiveFocus() }
                    }

                    AppComboBox {
                        Layout.fillWidth: false
                        Layout.preferredWidth: root.width > 840 ? 134 : 104
                        Layout.maximumWidth: root.width > 840 ? 134 : 104
                        model: ["all", "pending", "processing", "done", "failed", "skipped", "cancelled"]
                        translationPrefix: "queue_filter_"
                        currentIndex: appRoot ? Math.max(0, find(appRoot.queueStatusFilter)) : 0
                        onActivated: if (appRoot) appRoot.queueStatusFilter = currentText
                    }

                    AppIconButton {
                        iconName: (backend && backend.queueViewMode === "grid") ? "queue" : "grid"
                        accessibleLabel: (backend && backend.queueViewMode === "grid") ? I18n.t("list_view") : I18n.t("grid_view")
                        onClicked: if (backend) backend.queueViewMode = (backend.queueViewMode === "grid" ? "list" : "grid")
                    }

                    AppIconButton {
                        iconName: "sort"
                        accessibleLabel: I18n.t("priority")
                        onClicked: sortMenu.open()
                        Menu {
                            id: sortMenu
                            MenuItem { text: I18n.t("priority"); onTriggered: backend && backend.sortQueueByPriority() }
                            MenuItem { text: I18n.t("retry_failed"); enabled: backend && backend.failedCount > 0; onTriggered: backend && backend.retryFailed() }
                            MenuSeparator {}
                            MenuItem { text: I18n.t("cleanup_done"); onTriggered: backend && backend.cleanupQueue("done") }
                            MenuItem { text: I18n.t("cleanup_failed"); onTriggered: backend && backend.cleanupQueue("failed") }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.borderMuted }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.windowBackground

                DropArea {
                    id: queueAppendDropArea
                    objectName: "queueAppendDropArea"
                    anchors.fill: parent
                    keys: ["text/uri-list"]
                    onDropped: function(drop) {
                        if (drop.hasUrls) {
                            backend && backend.addDroppedUrls(drop.urls)
                            drop.acceptProposedAction()
                        }
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: Theme.space3
                    visible: queueAppendDropArea.containsDrag && backend && backend.queueCount > 0
                    z: 3
                    color: Theme.accentSoft
                    border.width: 1
                    border.color: Theme.accentPrimary
                    radius: Theme.radiusMd
                    Label { anchors.centerIn: parent; text: I18n.t("drop_append_title"); color: Theme.textPrimary; font.pixelSize: Theme.fontSizeMd; font.weight: Font.DemiBold }
                }

                Queue.QueueEmptyState {
                    anchors.fill: parent
                    visible: !backend || backend.queueCount === 0
                    onHeightChanged: if (appRoot) appRoot.queueDropZoneHeight = height
                    Component.onCompleted: if (appRoot) appRoot.queueDropZoneHeight = height
                    onFilesDropped: function(urls) { backend && backend.addDroppedUrls(urls) }
                    onAddFilesRequested: appRoot && appRoot.addFilesForWorkspace()
                    onAddFolderRequested: appRoot && appRoot.addFolderForWorkspace()
                }

                ColumnLayout {
                    anchors.fill: parent
                    visible: backend && backend.queueCount > 0
                    spacing: 0

                    Rectangle {
                        visible: !(backend && backend.queueViewMode === "grid")
                        Layout.fillWidth: true
                        Layout.preferredHeight: 31
                        color: Theme.panelSecondary
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space3
                            anchors.rightMargin: Theme.space3
                            spacing: Theme.space2
                            Item { Layout.preferredWidth: 22 }
                            Item { Layout.preferredWidth: 32 }
                            Label { Layout.fillWidth: true; text: I18n.t("file_name").toUpperCase(); color: Theme.textMuted; font.pixelSize: 10; font.weight: Font.DemiBold }
                            Label { visible: !root.narrow; Layout.preferredWidth: 64; text: I18n.t("format").toUpperCase(); color: Theme.textMuted; font.pixelSize: 10; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignRight }
                            Label { visible: !root.narrow; Layout.preferredWidth: 140; text: I18n.t("size_duration").toUpperCase(); color: Theme.textMuted; font.pixelSize: 10; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignRight }
                            Item { Layout.preferredWidth: 112; visible: !root.narrow }
                            Label { Layout.preferredWidth: 112; text: I18n.t("status").toUpperCase(); color: Theme.textMuted; font.pixelSize: 10; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter }
                            Item { Layout.preferredWidth: 32 }
                        }
                    }

                    SecondaryButton {
                        visible: backend && backend.visibleQueueCount === 0
                        Layout.alignment: Qt.AlignHCenter
                        Layout.fillWidth: false
                        Layout.topMargin: Theme.space3
                        text: I18n.t("reset_filters")
                        onClicked: if (appRoot) { appRoot.queueSearchText = ""; appRoot.queueStatusFilter = "all" }
                    }

                    Label {
                        visible: backend && backend.visibleQueueCount === 0
                        Layout.fillWidth: true
                        Layout.margins: Theme.space4
                        text: I18n.t("no_matching_files")
                        color: Theme.textSecondary
                        horizontalAlignment: Text.AlignHCenter
                    }

                    ListView {
                        id: queueList
                        objectName: "queueList"
                        visible: !(backend && backend.queueViewMode === "grid")
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: visible && backend ? backend.filteredQueueModel : null
                        clip: true
                        spacing: 1
                        cacheBuffer: 160
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        reuseItems: true
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Queue.QueueRow {
                            width: ListView.view.width
                            fileName: model.name
                            filePath: model.path
                            mediaType: model.mediaType
                            status: model.status
                            errorText: model.errorText
                            outputPath: model.outputPath || model.previewOutput
                            durationText: model.durationText
                            sizeText: model.sizeText
                            thumbnailSource: model.thumbnailSource
                            progress: model.progress
                            etaText: model.etaText
                            speedText: model.speedText
                            selected: appRoot ? appRoot.isPathSelected(model.path) : false
                            compact: root.narrow
                            itemIndex: model.sourceIndex
                            onSelectedRequested: function(path, modifiers) { appRoot && appRoot.selectQueuePath(path, index, modifiers, model.name, model.mediaType, model.thumbnailSource) }
                            onRetryRequested: function(path) { backend && backend.retryTaskPath(path) }
                            onSkipRequested: function(path) { backend && backend.skipTaskPath(path) }
                            onRemoveRequested: function(path) { appRoot && appRoot.removeQueuePath(path) }
                            onQuickConvertRequested: function(path, name, mediaKind, rowIndex) { appRoot && appRoot.openQuickConvert(path, name, mediaKind, rowIndex) }
                            onMoveRequested: function(path, targetIndex) { backend && backend.movePathToIndex(path, targetIndex) }
                            onOpenOutputRequested: function(path) { backend && backend.openOutputForPath(path) }
                        }
                    }

                    GridView {
                        id: queueGrid
                        objectName: "queueGrid"
                        visible: backend && backend.queueViewMode === "grid"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 10
                        cellWidth: width / Math.max(1, Math.floor(width / 224))
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        cellHeight: 244
                        model: visible && backend ? backend.filteredQueueModel : null
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Item {
                            width: GridView.view.cellWidth - 8
                            height: 236

                            QueueItemCard {
                                anchors.fill: parent
                                fileName: model.name
                                filePath: model.path
                                mediaType: model.mediaType
                                status: model.status
                                errorText: model.errorText
                                outputPath: model.outputPath || model.previewOutput
                                durationText: model.durationText
                                sizeText: model.sizeText
                                thumbnailSource: model.thumbnailSource
                                progress: model.progress
                                etaText: model.etaText
                                speedText: model.speedText
                                selected: appRoot ? appRoot.isPathSelected(model.path) : false
                                itemIndex: model.sourceIndex
                                onSelectedRequested: function(path, modifiers) { appRoot && appRoot.selectQueuePath(path, index, modifiers, model.name, model.mediaType, model.thumbnailSource) }
                                onRetryRequested: function(path) { backend && backend.retryTaskPath(path) }
                                onSkipRequested: function(path) { backend && backend.skipTaskPath(path) }
                                onRemoveRequested: function(path) { appRoot && appRoot.removeQueuePath(path) }
                                onQuickConvertRequested: function(path, name, mediaKind, rowIndex) { appRoot && appRoot.openQuickConvert(path, name, mediaKind, rowIndex) }
                                onMoveRequested: function(path, targetIndex) { backend && backend.movePathToIndex(path, targetIndex) }
                                onOpenOutputRequested: function(path) { backend && backend.openOutputForPath(path) }
                            }
                        }
                    }
                }
            }
        }

        AppLayout.InspectorPanel {
            visible: root.hasSelection && !root.narrow
            Layout.fillHeight: true
            Layout.preferredWidth: visible ? 328 : 0
            Layout.minimumWidth: visible ? 328 : 0
            Layout.maximumWidth: visible ? 328 : 0
            appRoot: root.appRoot
        }
    }

    Drawer {
        id: inspectorDrawer
        edge: Qt.RightEdge
        width: Math.min(340, root.width - 36)
        height: root.height
        modal: true
        Overlay.modal: Rectangle { color: Theme.modalScrim }
        interactive: true
        background: Rectangle { color: Theme.panelBackground; border.width: 1; border.color: Theme.borderDefault }
        AppLayout.InspectorPanel { anchors.fill: parent; appRoot: root.appRoot }
    }

    onNarrowChanged: if (!narrow) inspectorDrawer.close()

    Connections {
        target: appRoot
        function onSelectedPathChanged() {
            if (!appRoot || appRoot.selectedPath.length === 0) inspectorDrawer.close()
            else if (root.narrow)
                inspectorDrawer.open()
        }
    }
}
