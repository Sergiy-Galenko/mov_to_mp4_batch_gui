import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6 import QtCore

from app.models import MediaInfo, TaskItem, TaskStatus
from utils.formatting import format_bytes, format_time


class QueueModel(QtCore.QAbstractListModel):
    NameRole = QtCore.Qt.UserRole + 1
    TypeRole = QtCore.Qt.UserRole + 2
    PathRole = QtCore.Qt.UserRole + 3
    DisplayRole = QtCore.Qt.UserRole + 4
    StatusRole = QtCore.Qt.UserRole + 5
    ErrorRole = QtCore.Qt.UserRole + 6
    AttemptsRole = QtCore.Qt.UserRole + 7
    HasOverrideRole = QtCore.Qt.UserRole + 8
    OutputRole = QtCore.Qt.UserRole + 9
    PreviewRole = QtCore.Qt.UserRole + 10
    DurationRole = QtCore.Qt.UserRole + 11
    SizeRole = QtCore.Qt.UserRole + 12
    ThumbnailRole = QtCore.Qt.UserRole + 13
    IdRole = QtCore.Qt.UserRole + 14
    ProgressRole = QtCore.Qt.UserRole + 15
    EtaRole = QtCore.Qt.UserRole + 16
    SpeedRole = QtCore.Qt.UserRole + 17
    ElapsedRole = QtCore.Qt.UserRole + 18
    ExitCodeRole = QtCore.Qt.UserRole + 19
    PredictedSizeRole = QtCore.Qt.UserRole + 20
    CompressionRole = QtCore.Qt.UserRole + 21

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._items: List[TaskItem] = []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == QtCore.Qt.DisplayRole or role == self.DisplayRole:
            return f"{item.path.name}  [{item.media_type}]"
        if role == self.NameRole:
            return item.path.name
        if role == self.TypeRole:
            return item.media_type
        if role == self.PathRole:
            return str(item.path)
        if role == self.StatusRole:
            return item.status
        if role == self.ErrorRole:
            return item.last_error
        if role == self.AttemptsRole:
            return item.attempts
        if role == self.HasOverrideRole:
            return bool(item.overrides)
        if role == self.OutputRole:
            return item.last_output
        if role == self.PreviewRole:
            return item.preview_output
        if role == self.DurationRole:
            return item.duration_text
        if role == self.SizeRole:
            return item.size_text
        if role == self.ThumbnailRole:
            thumbnail = item.thumbnail_path
            if not thumbnail and item.media_type == "image" and item.path.exists():
                thumbnail = str(item.path)
            if thumbnail:
                return QtCore.QUrl.fromLocalFile(thumbnail).toString()
            return ""
        if role == self.IdRole:
            return str(item.path)
        if role == self.ProgressRole:
            return float(item.progress)
        if role == self.EtaRole:
            return item.eta_text
        if role == self.SpeedRole:
            return item.speed_text
        if role == self.ElapsedRole:
            return float(item.elapsed_seconds)
        if role == self.ExitCodeRole:
            return item.exit_code if item.exit_code is not None else -1
        if role == self.PredictedSizeRole:
            return format_bytes(item.predicted_output_bytes) if item.predicted_output_bytes else ""
        if role == self.CompressionRole:
            return f"{item.compression_ratio:.2f}x" if item.compression_ratio > 0 else ""
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.NameRole: b"name",
            self.TypeRole: b"mediaType",
            self.PathRole: b"path",
            self.DisplayRole: b"display",
            self.StatusRole: b"status",
            self.ErrorRole: b"errorText",
            self.AttemptsRole: b"attempts",
            self.HasOverrideRole: b"hasOverride",
            self.OutputRole: b"outputPath",
            self.PreviewRole: b"previewOutput",
            self.DurationRole: b"durationText",
            self.SizeRole: b"sizeText",
            self.ThumbnailRole: b"thumbnailSource",
            self.IdRole: b"itemId",
            self.ProgressRole: b"progress",
            self.EtaRole: b"etaText",
            self.SpeedRole: b"speedText",
            self.ElapsedRole: b"elapsedSeconds",
            self.ExitCodeRole: b"exitCode",
            self.PredictedSizeRole: b"predictedSizeText",
            self.CompressionRole: b"compressionText",
        }

    def items(self) -> List[TaskItem]:
        return list(self._items)

    def item_at(self, index: int) -> Optional[TaskItem]:
        if index < 0 or index >= len(self._items):
            return None
        return self._items[index]

    def item_by_path(self, task_path: Path) -> Optional[TaskItem]:
        task_path = task_path.expanduser()
        for item in self._items:
            if item.path == task_path:
                return item
        return None

    def index_for_path(self, task_path: Path) -> int:
        task_path = task_path.expanduser()
        for idx, item in enumerate(self._items):
            if item.path == task_path:
                return idx
        return -1

    def add_items(self, items: List[TaskItem]) -> None:
        if not items:
            return
        start = len(self._items)
        end = start + len(items) - 1
        self.beginInsertRows(QtCore.QModelIndex(), start, end)
        self._items.extend(items)
        self.endInsertRows()

    def set_items(self, items: List[TaskItem]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def update_item(self, index: int, item: TaskItem) -> None:
        if index < 0 or index >= len(self._items):
            return
        self._items[index] = item
        model_index = self.index(index, 0)
        self.dataChanged.emit(model_index, model_index, list(self.roleNames().keys()))

    def update_task_state(self, task_path: Path, status: str, message: str = "", output_path: str = "") -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            if status == TaskStatus.RUNNING:
                item.attempts += 1
                item.progress = 0.0
                item.eta_text = ""
                item.speed_text = ""
                item.exit_code = None
            item.status = status
            if status == TaskStatus.SUCCESS:
                item.last_error = ""
                item.exit_code = None
                item.progress = 1.0
                item.eta_text = "00:00"
            elif status in {TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}:
                item.last_error = message
                match = re.search(r"(?:code|код)\s*(-?\d+)", message, flags=re.IGNORECASE)
                if match:
                    item.exit_code = int(match.group(1))
                if status != TaskStatus.SKIPPED:
                    item.progress = max(0.0, min(item.progress, 1.0))
                item.eta_text = ""
            if output_path:
                item.last_output = output_path
            self.update_item(idx, item)
            return

    def set_task_progress(self, task_path: Path, progress: float, eta_text: str = "", speed_text: str = "") -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            bounded = max(0.0, min(float(progress), 1.0))
            if item.progress == bounded and item.eta_text == eta_text and item.speed_text == speed_text:
                return
            item.progress = bounded
            item.eta_text = eta_text
            item.speed_text = speed_text
            self.update_item(idx, item)
            return

    def set_preview_output(self, task_path: Path, preview_output: str) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            if item.preview_output == preview_output:
                return
            item.preview_output = preview_output
            self.update_item(idx, item)
            return

    def set_media_summary(self, task_path: Path, info: MediaInfo) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            duration_text = format_time(info.duration) if info.duration else "—"
            size_text = format_bytes(info.size_bytes)
            item.probe_data = info
            item.input_bytes = int(info.size_bytes or 0)
            if item.duration_text == duration_text and item.size_text == size_text:
                return
            item.duration_text = duration_text
            item.size_text = size_text
            self.update_item(idx, item)
            return

    def set_prediction(self, task_path: Path, predicted_bytes: int) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            predicted = max(0, int(predicted_bytes or 0))
            if item.predicted_output_bytes == predicted:
                return
            item.predicted_output_bytes = predicted
            self.update_item(idx, item)
            return

    def set_output_stats(self, task_path: Path, output_path_text: str) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            output_text = str(output_path_text or "").split(";", 1)[0].strip()
            if not output_text:
                return
            try:
                output_bytes = Path(output_text).expanduser().stat().st_size
            except Exception:
                return
            input_bytes = item.input_bytes
            if not input_bytes:
                try:
                    input_bytes = item.path.stat().st_size
                except Exception:
                    input_bytes = 0
            item.output_bytes = output_bytes
            item.input_bytes = input_bytes
            item.compression_ratio = (input_bytes / output_bytes) if input_bytes and output_bytes else 0.0
            self.update_item(idx, item)
            return

    def set_file_size(self, task_path: Path) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            try:
                size_text = format_bytes(item.path.stat().st_size)
            except Exception:
                size_text = "—"
            if item.size_text == size_text:
                return
            item.size_text = size_text
            self.update_item(idx, item)
            return

    def set_thumbnail(self, task_path: Path, thumbnail_path: str) -> None:
        for idx, item in enumerate(self._items):
            if item.path != task_path:
                continue
            if item.thumbnail_path == thumbnail_path:
                return
            item.thumbnail_path = thumbnail_path
            self.update_item(idx, item)
            return

    def paths_set(self) -> set[Path]:
        return {item.path for item in self._items}

    def clear_statuses(self, *, paths: Optional[set[Path]] = None) -> None:
        for idx, item in enumerate(self._items):
            if paths is not None and item.path not in paths:
                continue
            item.status = TaskStatus.QUEUED
            item.last_error = ""
            item.last_output = ""
            item.progress = 0.0
            item.eta_text = ""
            item.speed_text = ""
            self.update_item(idx, item)


class LogModel(QtCore.QAbstractListModel):
    TimeRole = QtCore.Qt.UserRole + 1
    LevelRole = QtCore.Qt.UserRole + 2
    MessageRole = QtCore.Qt.UserRole + 3
    LineRole = QtCore.Qt.UserRole + 4

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._items: List[Dict[str, str]] = []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role == self.TimeRole:
            return item.get("time", "")
        if role == self.LevelRole:
            return item.get("level", "")
        if role == self.MessageRole:
            return item.get("message", "")
        if role == self.LineRole or role == QtCore.Qt.DisplayRole:
            return item.get("line", "")
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.TimeRole: b"timeText",
            self.LevelRole: b"level",
            self.MessageRole: b"message",
            self.LineRole: b"line",
        }

    def append(self, level: str, message: str) -> None:
        time_text = time.strftime("%H:%M:%S")
        line = f"[{time_text}] {level}: {message}"
        row = len(self._items)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._items.append({"time": time_text, "level": level, "message": message, "line": line})
        self.endInsertRows()

    def clear(self) -> None:
        self.beginResetModel()
        self._items = []
        self.endResetModel()

    def line_at(self, index: int) -> str:
        if index < 0 or index >= len(self._items):
            return ""
        return self._items[index].get("line", "")


class HistoryModel(QtCore.QAbstractListModel):
    StartedRole = QtCore.Qt.UserRole + 1
    OperationRole = QtCore.Qt.UserRole + 2
    TotalRole = QtCore.Qt.UserRole + 3
    FailedRole = QtCore.Qt.UserRole + 4
    SkippedRole = QtCore.Qt.UserRole + 5
    OutputRole = QtCore.Qt.UserRole + 6
    StatusRole = QtCore.Qt.UserRole + 7

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._entries: List[Dict[str, Any]] = []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        results = entry.get("results", [])
        failed = sum(1 for item in results if item.get("status") == "failed")
        skipped = sum(1 for item in results if item.get("status") == "skipped")
        if role == self.StartedRole:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("started_at", 0) or 0))
        if role == self.OperationRole:
            return entry.get("operation", "—")
        if role == self.TotalRole:
            return int(entry.get("total_files", 0) or 0)
        if role == self.FailedRole:
            return failed
        if role == self.SkippedRole:
            return skipped
        if role == self.OutputRole:
            return entry.get("output_dir", "—")
        if role == self.StatusRole:
            return "stopped" if entry.get("stopped") else ("failed" if failed else "success")
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.StartedRole: b"startedText",
            self.OperationRole: b"operation",
            self.TotalRole: b"totalFiles",
            self.FailedRole: b"failedFiles",
            self.SkippedRole: b"skippedFiles",
            self.OutputRole: b"outputDir",
            self.StatusRole: b"runStatus",
        }

    def set_entries(self, entries: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def entry_at(self, index: int) -> Optional[Dict[str, Any]]:
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]
