"""Qt / QML Binding for Archive and Compression operations."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from services.archive_service import ArchiveService
from services.background_job import BackgroundJob, JobContext

logger = logging.getLogger(__name__)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_time(seconds: float) -> str:
    secs = int(seconds)
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class ArchiveBackend(BackgroundJob):
    """QObject exposing Archive & Compression capabilities to QML."""

    isBusyChanged = QtCore.Signal()
    progressDetailsChanged = QtCore.Signal()
    toolsChanged = QtCore.Signal()
    archiveFinished = QtCore.Signal(bool, str, dict)
    extractFinished = QtCore.Signal(bool, str, dict)
    archiveContentsReady = QtCore.Signal(str, list, int, int)
    analysisReady = QtCore.Signal(dict)
    operationError = QtCore.Signal(str, str, str)  # title, message, details

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._tool_settings = QtCore.QSettings()
        seven_zip_path = str(self._tool_settings.value("archive/7z_path", "") or "")
        rar_path = str(self._tool_settings.value("archive/rar_path", "") or "")
        self._service = ArchiveService(seven_zip_bin=seven_zip_path or None, rar_bin=rar_path or None)
        self._current_file = ""
        self._files_done = 0
        self._files_total = 0
        self._bytes_done = 0
        self._bytes_total = 0
        self._elapsed_seconds = 0.0
        self._last_analysis: dict[str, Any] = {}
        self._last_result_data: dict[str, Any] = {}
        self._last_error_details = ""
        self._cached_archive_contents: list[dict[str, Any]] = []
        self.changed.connect(self.isBusyChanged.emit)

    # -------------------------------------------------------------------------
    # Properties for QML bindings
    # -------------------------------------------------------------------------

    @QtCore.Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._busy

    @QtCore.Property(str, notify=progressDetailsChanged)
    def currentFile(self) -> str:
        return self._current_file

    @QtCore.Property(int, notify=progressDetailsChanged)
    def filesDone(self) -> int:
        return self._files_done

    @QtCore.Property(int, notify=progressDetailsChanged)
    def filesTotal(self) -> int:
        return self._files_total

    @QtCore.Property(str, notify=progressDetailsChanged)
    def bytesDoneText(self) -> str:
        return _format_size(self._bytes_done)

    @QtCore.Property(str, notify=progressDetailsChanged)
    def bytesTotalText(self) -> str:
        return _format_size(self._bytes_total)

    @QtCore.Property(str, notify=progressDetailsChanged)
    def elapsedText(self) -> str:
        return _format_time(self._elapsed_seconds)

    @QtCore.Property(bool, notify=toolsChanged)
    def has7z(self) -> bool:
        return self._service.has_7z

    @QtCore.Property(bool, notify=toolsChanged)
    def hasRar(self) -> bool:
        return self._service.has_rar

    @QtCore.Property(str, notify=toolsChanged)
    def sevenZipPath(self) -> str:
        return str(self._service._7z_path or "")

    @QtCore.Property(str, notify=toolsChanged)
    def rarPath(self) -> str:
        return str(self._service._rar_path or "")

    @QtCore.Property(list, notify=toolsChanged)
    def supportedCreateFormats(self) -> list[dict[str, Any]]:
        formats = self._service.get_supported_formats()
        return [
            {
                "id": f.id,
                "name": f.name,
                "extension": f.extension,
                "canCreate": f.can_create,
                "supportsEncryption": f.supports_encryption,
                "supportsFilenameEncryption": f.supports_filename_encryption,
                "supportsSplit": f.supports_split,
                "supportsSolid": f.supports_solid,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            for f in formats
            if f.can_create
        ]

    @QtCore.Property(list, notify=toolsChanged)
    def supportedExtractFormats(self) -> list[dict[str, Any]]:
        formats = self._service.get_supported_formats()
        return [
            {
                "id": f.id,
                "name": f.name,
                "extension": f.extension,
                "canExtract": f.can_extract,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            for f in formats
            if f.can_extract
        ]

    @QtCore.Property(dict, notify=progressDetailsChanged)
    def lastResult(self) -> dict[str, Any]:
        return self._last_result_data

    @QtCore.Property(str, notify=progressDetailsChanged)
    def lastErrorDetails(self) -> str:
        return self._last_error_details

    # -------------------------------------------------------------------------
    # Slots callable from QML
    # -------------------------------------------------------------------------

    @QtCore.Slot()
    def pick7Zip(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Вкажіть 7-Zip", "", "7-Zip (7z 7za 7zr);;All Files (*)"
        )
        if path:
            self._service._7z_path = path
            self._tool_settings.setValue("archive/7z_path", path)
            self.toolsChanged.emit()

    @QtCore.Slot()
    def pickRar(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Вкажіть WinRAR CLI", "", "RAR (rar);;All Files (*)"
        )
        if path:
            self._service._rar_path = path
            self._tool_settings.setValue("archive/rar_path", path)
            self.toolsChanged.emit()

    @QtCore.Slot(list, result="QVariantMap")
    def analyzeSources(self, sources: list[str]) -> dict[str, Any]:
        """Analyze source files/folders to determine total size, count, and compression hints."""
        clean_sources = [str(s).replace("file://", "").strip() for s in sources if str(s).strip()]
        res = self._service.analyze_sources(clean_sources)
        formatted_res = {
            "totalSize": res["total_size"],
            "totalSizeFormatted": _format_size(res["total_size"]),
            "fileCount": res["file_count"],
            "sampleName": res["sample_name"],
            "isMostlyCompressed": res["is_mostly_compressed"],
            "suggestedPreset": res["suggested_preset"],
            "notice": res["notice"],
            "suggestedOutputName": (
                res["sample_name"] if res["sample_name"] else "Archive"
            ),
        }
        self._last_analysis = formatted_res
        self.analysisReady.emit(formatted_res)
        return formatted_res

    @QtCore.Slot(list, result=str)
    def getSuggestedArchiveName(self, sources: list[str]) -> str:
        if not sources:
            return "Archive"
        first = str(sources[0]).replace("file://", "").strip()
        p = Path(first)
        return p.stem if p.is_file() else p.name

    @QtCore.Slot(list, result=str)
    def getDefaultOutputFolder(self, sources: list[str]) -> str:
        if not sources:
            return str(Path.home())
        first = str(sources[0]).replace("file://", "").strip()
        p = Path(first)
        return str(p.parent)

    @QtCore.Slot(str, int, result="QVariantMap")
    def checkFreeDiskSpace(self, target_folder: str, required_bytes: int) -> dict[str, Any]:
        folder_clean = str(target_folder).replace("file://", "").strip()
        p = Path(folder_clean).resolve()
        try:
            free = shutil.disk_usage(p if p.exists() else p.parent).free
            has_space = free >= required_bytes
            return {
                "hasSpace": has_space,
                "freeBytes": free,
                "freeFormatted": _format_size(free),
                "requiredBytes": required_bytes,
                "requiredFormatted": _format_size(required_bytes),
            }
        except OSError:
            return {
                "hasSpace": True,
                "freeBytes": 0,
                "freeFormatted": "Unknown",
                "requiredBytes": required_bytes,
                "requiredFormatted": _format_size(required_bytes),
            }

    @QtCore.Slot(list, str, str, str, str, bool, int, bool)
    def createArchive(
        self,
        sources: list[str],
        output_path: str,
        archive_format: str = "zip",
        preset: str = "balanced",
        password: str = "",
        encrypt_filenames: bool = False,
        split_size_mb: int = 0,
        solid: bool = True,
    ) -> None:
        """Asynchronously create archive on a background worker thread."""
        clean_sources = [str(s).replace("file://", "").strip() for s in sources if str(s).strip()]
        clean_output = str(output_path).replace("file://", "").strip()

        # Reset progress
        self._current_file = "Preparing..."
        self._files_done = 0
        self._files_total = 0
        self._bytes_done = 0
        self._bytes_total = 0
        self._elapsed_seconds = 0.0
        self._last_result_data = {}
        self._last_error_details = ""
        self.progressDetailsChanged.emit()

        def work(ctx: JobContext) -> dict[str, Any]:
            def on_progress(pct: float, f_done: int, f_total: int, b_done: int, b_total: int, curr_f: str, elapsed: float) -> None:
                ctx.check()
                self._files_done = f_done
                self._files_total = f_total
                self._bytes_done = b_done
                self._bytes_total = b_total
                self._current_file = curr_f
                self._elapsed_seconds = elapsed
                self._progress.emit(f"Compressing ({int(pct)}%)", int(pct))
                self.progressDetailsChanged.emit()

            res = self._service.create_archive(
                sources=clean_sources,
                output_path=clean_output,
                archive_format=archive_format,
                preset=preset,
                password=password,
                encrypt_filenames=encrypt_filenames,
                split_size_mb=split_size_mb,
                solid=solid,
                cancel_requested=lambda: ctx.cancelled.is_set(),
                progress_callback=on_progress,
            )

            if not res.success:
                raise RuntimeError(res.error_message)

            result_map = {
                "success": True,
                "outputPath": res.output_path,
                "originalSize": res.original_size,
                "originalSizeFormatted": _format_size(res.original_size),
                "archiveSize": res.archive_size,
                "archiveSizeFormatted": _format_size(res.archive_size),
                "savedPercent": res.saved_percent,
                "isLarger": res.is_larger,
                "filesCount": res.files_count,
                "elapsedSeconds": res.elapsed_seconds,
                "elapsedFormatted": _format_time(res.elapsed_seconds),
            }
            self._last_result_data = result_map
            return result_map

        def on_finished(res: dict[str, Any], err: str) -> None:
            if err:
                self._last_error_details = err
                self.archiveFinished.emit(False, err, {})
                self.operationError.emit("Archive Creation Error", err, err)
            else:
                self.archiveFinished.emit(True, "Archive created successfully", res)

        self._finished.connect(on_finished)
        self.start_job(work)

    @QtCore.Slot(str, str, list, str, str)
    def extractArchive(
        self,
        archive_path: str,
        destination_dir: str,
        selected_files: list[str] | None = None,
        password: str = "",
        overwrite_mode: str = "ask",
    ) -> None:
        """Asynchronously extract archive on a background worker thread."""
        clean_archive = str(archive_path).replace("file://", "").strip()
        clean_dest = str(destination_dir).replace("file://", "").strip()

        self._current_file = "Reading archive..."
        self._files_done = 0
        self._files_total = 0
        self._bytes_done = 0
        self._bytes_total = 0
        self._elapsed_seconds = 0.0
        self._last_result_data = {}
        self._last_error_details = ""
        self.progressDetailsChanged.emit()

        def work(ctx: JobContext) -> dict[str, Any]:
            def on_progress(pct: float, f_done: int, f_total: int, b_done: int, b_total: int, curr_f: str, elapsed: float) -> None:
                ctx.check()
                self._files_done = f_done
                self._files_total = f_total
                self._bytes_done = b_done
                self._bytes_total = b_total
                self._current_file = curr_f
                self._elapsed_seconds = elapsed
                self._progress.emit(f"Extracting ({int(pct)}%)", int(pct))
                self.progressDetailsChanged.emit()

            res = self._service.extract_archive(
                archive_path=clean_archive,
                destination_dir=clean_dest,
                selected_files=selected_files or None,
                password=password,
                overwrite_mode=overwrite_mode,
                cancel_requested=lambda: ctx.cancelled.is_set(),
                progress_callback=on_progress,
            )

            if not res.success:
                raise RuntimeError(res.error_message)

            result_map = {
                "success": True,
                "destination": res.destination,
                "filesExtracted": res.files_extracted,
                "bytesExtracted": res.bytes_extracted,
                "bytesExtractedFormatted": _format_size(res.bytes_extracted),
                "elapsedSeconds": res.elapsed_seconds,
                "elapsedFormatted": _format_time(res.elapsed_seconds),
            }
            self._last_result_data = result_map
            return result_map

        def on_finished(res: dict[str, Any], err: str) -> None:
            if err:
                self._last_error_details = err
                self.extractFinished.emit(False, err, {})
                self.operationError.emit("Archive Extraction Error", err, err)
            else:
                self.extractFinished.emit(True, "Extracted successfully", res)

        self._finished.connect(on_finished)
        self.start_job(work)

    @QtCore.Slot(str, str)
    def listArchive(self, archive_path: str, password: str = "") -> None:
        """List files inside archive and emit archiveContentsReady."""
        clean_archive = str(archive_path).replace("file://", "").strip()
        try:
            entries = self._service.list_archive(clean_archive, password=password)
            mapped_entries = [
                {
                    "name": e.name,
                    "path": e.path,
                    "size": e.size,
                    "sizeFormatted": _format_size(e.size),
                    "compressedSize": e.compressed_size,
                    "compressedSizeFormatted": _format_size(e.compressed_size),
                    "isDir": e.is_dir,
                    "modified": e.modified,
                    "iconType": e.icon_type,
                }
                for e in entries
            ]
            total_files = len([e for e in entries if not e.is_dir])
            total_bytes = sum(e.size for e in entries if not e.is_dir)
            self._cached_archive_contents = mapped_entries
            self.archiveContentsReady.emit(clean_archive, mapped_entries, total_files, total_bytes)
        except Exception as e:
            logger.warning("Failed to list archive %s: %s", clean_archive, e)
            self.operationError.emit("Cannot Open Archive", str(e), str(e))

    @QtCore.Slot(str)
    def openInFileManager(self, file_or_folder_path: str) -> None:
        """Reveal file or folder in OS File Manager (Finder / Explorer)."""
        clean_path = str(file_or_folder_path).replace("file://", "").strip()
        p = Path(clean_path).resolve()
        if not p.exists():
            p = p.parent
        if not p.exists():
            return

        if sys.platform == "darwin":
            if p.is_file():
                subprocess.run(["open", "-R", str(p)], check=False)
            else:
                subprocess.run(["open", str(p)], check=False)
        elif sys.platform == "win32":
            if p.is_file():
                subprocess.run(["explorer", f"/select,{p}"], check=False)
            else:
                subprocess.run(["explorer", str(p)], check=False)
        else:
            folder = str(p.parent if p.is_file() else p)
            subprocess.run(["xdg-open", folder], check=False)

    @QtCore.Slot(str)
    def copyToClipboard(self, text: str) -> None:
        """Copy path or text to system clipboard."""
        app = QtWidgets.QApplication.instance()
        if app:
            clipboard = QtGui.QGuiApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
