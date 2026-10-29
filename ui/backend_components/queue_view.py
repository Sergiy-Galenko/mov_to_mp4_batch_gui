from __future__ import annotations

from .common import Any, ConversionSettings, Dict, List, Path, QtCore, QueueModel, merge_settings_maps, settings_map_to_model
from .core import CoreMixin


class QueueViewMixin:
    @QtCore.Property(QtCore.QObject, constant=True)
    def filteredQueueModel(self) -> QtCore.QObject:
        return self.queue_filter_model

    @QtCore.Property(int, notify=CoreMixin.queueFilterChanged)
    def visibleQueueCount(self) -> int:
        return self.queue_filter_model.rowCount()

    @QtCore.Property("QVariantList", notify=CoreMixin.queueFilterChanged)
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
        info = self.media_info_cache.get(item.path) or item.probe_data
        output = Path(item.last_output.split(";", 1)[0].strip()) if item.last_output else None
        from utils.error_classifier import classify_stderr_block
        from utils.formatting import format_bytes

        errors = classify_stderr_block(item.last_error or "")
        error = next((e for e in errors if e.category != "unknown"), None)

        def file_size(path):
            try:
                return path.stat().st_size if path and path.is_file() else None
            except OSError:
                return None

        source_size = file_size(item.path)
        output_size = file_size(output)
        return {
            "operation": settings.operation,
            "durationSec": info.duration if info else 0,
            "audioTracks": info.audio_streams if info else 0,
            "audioTrackIndex": settings.audio_track_index,
            "outputExists": output_size is not None,
            "sourceSize": format_bytes(source_size or 0),
            "outputSize": format_bytes(output_size or 0),
            "sizeChangePercent": round((1 - output_size / source_size) * 100, 1) if source_size and output_size else 0,
            "errorText": (error.message + ". " + error.suggestion) if error else item.last_error,
            "errorCategory": error.category if error else "unknown",
            "name": item.path.name,
            "mediaType": item.media_type,
            "thumbnail": self.queue_model.data(self.queue_model.index(index, 0), QueueModel.ThumbnailRole),
            "format": self.ffmpeg_service.output_extension_for(item.media_type, settings),
            "trimStart": settings.trim_start or 0,
            "trimEnd": settings.trim_end or 0,
            "fastCopy": settings.fast_copy,
        }
