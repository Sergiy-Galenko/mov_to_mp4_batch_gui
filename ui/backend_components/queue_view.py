from __future__ import annotations

BODY = r'''    @QtCore.Property(QtCore.QObject, constant=True)
    def filteredQueueModel(self) -> QtCore.QObject:
        return self.queue_filter_model

    @QtCore.Property(int, notify=queueFilterChanged)
    def visibleQueueCount(self) -> int:
        return self.queue_filter_model.rowCount()

    @QtCore.Property("QVariantList", notify=queueFilterChanged)
    def visibleQueuePaths(self) -> List[str]:
        model = self.queue_filter_model
        return [str(model.data(model.index(row, 0), QueueModel.PathRole)) for row in range(model.rowCount())]

    @QtCore.Slot(str, str, str)
    def setQueueFilter(self, search: str, status: str, media_kind: str) -> None:
        self.queue_filter_model.set_filters(search, status, media_kind)
        self.queueFilterChanged.emit()

    @QtCore.Slot(str, result=int)
    def queueIndexForPath(self, path_text: str) -> int:
        return self.queue_model.index_for_path(Path(path_text).expanduser())

    @QtCore.Slot(str, result="QVariantMap")
    def queueItemDetails(self, path_text: str) -> Dict[str, Any]:
        index = self.queueIndexForPath(path_text)
        item = self.queue_model.item_at(index)
        if item is None:
            return {}
        settings = settings_map_to_model(merge_settings_maps(self._last_settings_map, item.overrides), defaults=ConversionSettings())
        return {
            "name": item.path.name,
            "mediaType": item.media_type,
            "thumbnail": self.queue_model.data(self.queue_model.index(index, 0), QueueModel.ThumbnailRole),
            "format": self.ffmpeg_service.output_extension_for(item.media_type, settings),
            "trimStart": settings.trim_start or 0,
            "trimEnd": settings.trim_end or 0,
            "fastCopy": settings.fast_copy,
        }
'''
