"""Universal Archive and Compression Service.

Provides robust, cross-platform archiving and extraction supporting:
- Creation: ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2, TAR.XZ, GZ, BZ2, XZ
- Extraction: ZIP, 7Z, RAR, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ, TXZ, GZ, BZ2, XZ
- Security: Zip Slip / Path Traversal prevention, symlink safety, archive bomb detection, disk space pre-check
- Performance: Streaming chunked processing for multi-gigabyte files (4GB-100GB+)
- Cancellation with automatic cleanup of incomplete output files
- Password protection & AES-256 encryption
"""

from __future__ import annotations

import bz2
import contextlib
import gzip
import logging
import lzma
import os
import shutil
import subprocess
import tarfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.paths import find_7z, find_rar

try:
    import pyzipper
except ImportError:  # The non-encrypted archive features remain available.
    pyzipper = None

logger = logging.getLogger(__name__)

# Known media/compressed extensions where compression yields minimal gains
ALREADY_COMPRESSED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
    ".wmv",
    ".flv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".gif",
    ".mp3",
    ".aac",
    ".ogg",
    ".flac",
    ".m4a",
    ".opus",
    ".zip",
    ".7z",
    ".rar",
    ".gz",
    ".bz2",
    ".xz",
    ".tar.gz",
    ".tar.xz",
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
}

TEXT_OR_CODE_EXTENSIONS = {
    ".txt",
    ".json",
    ".xml",
    ".csv",
    ".tsv",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".py",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".md",
    ".log",
    ".sql",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
}


@dataclass
class ArchiveEntry:
    name: str
    path: str
    size: int
    compressed_size: int
    is_dir: bool
    modified: float
    icon_type: str = "generic"


@dataclass
class ArchiveFormatInfo:
    id: str
    name: str
    extension: str
    can_create: bool
    can_extract: bool
    supports_encryption: bool
    supports_filename_encryption: bool
    supports_split: bool
    supports_solid: bool
    description: str
    recommendation: str


@dataclass
class ArchiveResult:
    success: bool
    output_path: str = ""
    original_size: int = 0
    archive_size: int = 0
    saved_percent: float = 0.0
    is_larger: bool = False
    files_count: int = 0
    elapsed_seconds: float = 0.0
    error_message: str = ""


@dataclass
class ExtractResult:
    success: bool
    destination: str = ""
    files_extracted: int = 0
    bytes_extracted: int = 0
    elapsed_seconds: float = 0.0
    error_message: str = ""


def get_file_icon_type(name: str, is_dir: bool = False) -> str:
    if is_dir:
        return "folder"
    ext = Path(name).suffix.lower()
    if ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv"}:
        return "video"
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp", ".svg", ".tiff"}:
        return "image"
    if ext in {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".opus"}:
        return "audio"
    if ext in {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"}:
        return "document"
    if ext in {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".tbz2", ".txz"}:
        return "archive"
    if ext in TEXT_OR_CODE_EXTENSIONS or ext in {".sh", ".bat", ".cmd", ".ps1"}:
        return "code"
    return "generic"


class ArchiveSecurityError(Exception):
    """Raised when an archive operation violates security constraints."""

    pass


class NotEnoughDiskSpaceError(ArchiveSecurityError):
    """Raised when destination drive lacks sufficient space."""

    pass


class ArchiveService:
    """Service providing core archiving, compression and extraction operations."""

    def __init__(self, seven_zip_bin: str | None = None, rar_bin: str | None = None) -> None:
        self._7z_path = seven_zip_bin or find_7z()
        self._rar_path = rar_bin or find_rar()
        self._cancelled = False

    @property
    def has_7z(self) -> bool:
        return bool(self._7z_path and Path(self._7z_path).is_file())

    @property
    def has_rar(self) -> bool:
        return bool(self._rar_path and Path(self._rar_path).is_file())

    def get_supported_formats(self) -> list[ArchiveFormatInfo]:
        has_7z = self.has_7z
        has_rar = self.has_rar
        return [
            ArchiveFormatInfo(
                id="zip",
                name="ZIP",
                extension=".zip",
                can_create=True,
                can_extract=True,
                supports_encryption=True,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=False,
                description="Best compatibility across Windows, Mac, and Linux",
                recommendation="Recommended for sharing and general use",
            ),
            ArchiveFormatInfo(
                id="7z",
                name="7Z",
                extension=".7z",
                can_create=has_7z,
                can_extract=has_7z,
                supports_encryption=has_7z,
                supports_filename_encryption=has_7z,
                supports_split=has_7z,
                supports_solid=has_7z,
                description="High compression ratio with AES-256 encryption",
                recommendation="Recommended for maximum compression & security" if has_7z else "Requires 7-Zip installed",
            ),
            ArchiveFormatInfo(
                id="tar.gz",
                name="TAR.GZ",
                extension=".tar.gz",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=True,
                description="Standard Unix archive format with Gzip compression",
                recommendation="Recommended for Linux/server deployments",
            ),
            ArchiveFormatInfo(
                id="tar.bz2",
                name="TAR.BZ2",
                extension=".tar.bz2",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=True,
                description="Bzip2 compressed Unix tar archive with higher ratio",
                recommendation="Better compression than Gzip for text/data",
            ),
            ArchiveFormatInfo(
                id="tar.xz",
                name="TAR.XZ",
                extension=".tar.xz",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=True,
                description="High-ratio LZMA2 compression for tar archives",
                recommendation="Maximum compression for Unix distributions",
            ),
            ArchiveFormatInfo(
                id="tar",
                name="TAR",
                extension=".tar",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=False,
                description="Uncompressed tarball preserving exact permissions",
                recommendation="Fast bundling without compression overhead",
            ),
            ArchiveFormatInfo(
                id="gz",
                name="GZ",
                extension=".gz",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=False,
                description="Single file Gzip compression",
                recommendation="Best for individual logs or text files",
            ),
            ArchiveFormatInfo(
                id="bz2",
                name="BZ2",
                extension=".bz2",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=False,
                description="Single file Bzip2 compression",
                recommendation="Good compression for individual files",
            ),
            ArchiveFormatInfo(
                id="xz",
                name="XZ",
                extension=".xz",
                can_create=True,
                can_extract=True,
                supports_encryption=False,
                supports_filename_encryption=False,
                supports_split=False,
                supports_solid=False,
                description="Single file XZ / LZMA compression",
                recommendation="High compression for individual files",
            ),
            ArchiveFormatInfo(
                id="rar",
                name="RAR",
                extension=".rar",
                can_create=has_rar,
                can_extract=has_7z,
                supports_encryption=has_rar,
                supports_filename_encryption=has_rar,
                supports_split=has_rar,
                supports_solid=has_rar,
                description="Proprietary WinRAR archive format",
                recommendation="WinRAR command-line tool required for creation" if not has_rar else "High compatibility RAR archive",
            ),
        ]

    def analyze_sources(self, sources: list[str]) -> dict:
        """Scan input paths and gather total size, item count, and smart compression hints."""
        total_size = 0
        file_count = 0
        already_compressed_count = 0
        text_count = 0
        sample_name = ""

        resolved_files: list[tuple[str, str, int]] = []  # (disk_path, archive_rel_path, size)

        for src_str in sources:
            src = Path(src_str).resolve()
            if not src.exists():
                continue
            if not sample_name:
                sample_name = src.stem or src.name

            if src.is_file():
                sz = src.stat().st_size
                total_size += sz
                file_count += 1
                resolved_files.append((str(src), src.name, sz))
                ext = src.suffix.lower()
                if ext in ALREADY_COMPRESSED_EXTENSIONS:
                    already_compressed_count += 1
                elif ext in TEXT_OR_CODE_EXTENSIONS:
                    text_count += 1
            elif src.is_dir():
                parent_dir = src.parent
                stack = [src]
                while stack:
                    curr_dir = stack.pop()
                    try:
                        with os.scandir(curr_dir) as entries:
                            for entry in entries:
                                try:
                                    if entry.is_dir(follow_symlinks=False):
                                        stack.append(Path(entry.path))
                                    elif entry.is_file(follow_symlinks=False):
                                        p = Path(entry.path)
                                        sz = entry.stat(follow_symlinks=False).st_size
                                        total_size += sz
                                        file_count += 1
                                        rel = str(p.relative_to(parent_dir))
                                        resolved_files.append((str(p), rel, sz))
                                        ext = p.suffix.lower()
                                        if ext in ALREADY_COMPRESSED_EXTENSIONS:
                                            already_compressed_count += 1
                                        elif ext in TEXT_OR_CODE_EXTENSIONS:
                                            text_count += 1
                                except OSError:
                                    continue
                    except OSError:
                        continue

        is_mostly_compressed = file_count > 0 and (already_compressed_count / file_count) >= 0.5
        suggested_preset = "fast" if is_mostly_compressed else ("maximum" if (text_count / max(1, file_count)) > 0.5 else "balanced")

        notice = ""
        if is_mostly_compressed:
            notice = "Selected files are already compressed media. Archive size may not decrease significantly."

        return {
            "total_size": total_size,
            "file_count": file_count,
            "sample_name": sample_name or "Archive",
            "is_mostly_compressed": is_mostly_compressed,
            "suggested_preset": suggested_preset,
            "notice": notice,
            "resolved_files": resolved_files,
        }

    # =========================================================================
    # CREATE ARCHIVE
    # =========================================================================

    def create_archive(
        self,
        sources: list[str],
        output_path: str,
        archive_format: str = "zip",
        preset: str = "balanced",
        password: str = "",
        encrypt_filenames: bool = False,
        split_size_mb: int = 0,
        solid: bool = True,
        cancel_requested: Callable[[], bool] | None = None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None = None,
    ) -> ArchiveResult:
        """Create an archive with progress updates, cancel support, and streaming."""
        start_time = time.time()
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        analysis = self.analyze_sources(sources)
        resolved_files = analysis["resolved_files"]
        total_size = analysis["total_size"]
        total_files = analysis["file_count"]

        if total_files == 0:
            return ArchiveResult(success=False, error_message="No valid files selected for archiving.")

        # Check destination free space
        try:
            free_bytes = shutil.disk_usage(out_file.parent).free
            # Archive creation might need at least enough space for the output
            if free_bytes < 10 * 1024 * 1024:  # At least 10MB
                return ArchiveResult(success=False, error_message="Insufficient free disk space at destination.")
        except OSError:
            pass

        format_clean = archive_format.lower().strip()
        if format_clean.startswith("."):
            format_clean = format_clean[1:]

        # Dispatch
        try:
            if format_clean == "zip":
                if password and pyzipper is None:
                    return ArchiveResult(
                        success=False,
                        error_message="Password-protected ZIP archives require the pyzipper package.",
                    )
                self._create_zip(
                    resolved_files=resolved_files,
                    output_path=out_file,
                    preset=preset,
                    password=password,
                    total_size=total_size,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            elif format_clean.startswith("tar"):
                self._create_tar(
                    resolved_files=resolved_files,
                    output_path=out_file,
                    tar_format=format_clean,
                    preset=preset,
                    total_size=total_size,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            elif format_clean in {"gz", "bz2", "xz"}:
                self._create_single_compressed(
                    resolved_files=resolved_files,
                    output_path=out_file,
                    comp_type=format_clean,
                    preset=preset,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            elif format_clean == "7z":
                if not self.has_7z:
                    return ArchiveResult(success=False, error_message="7-Zip executable not found on system.")
                self._create_7z(
                    resolved_files=resolved_files,
                    output_path=out_file,
                    preset=preset,
                    password=password,
                    encrypt_filenames=encrypt_filenames,
                    split_size_mb=split_size_mb,
                    solid=solid,
                    total_size=total_size,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            elif format_clean == "rar":
                if not self.has_rar:
                    return ArchiveResult(success=False, error_message="WinRAR command-line executable not found on system.")
                self._create_rar(
                    resolved_files=resolved_files,
                    output_path=out_file,
                    preset=preset,
                    password=password,
                    encrypt_filenames=encrypt_filenames,
                    split_size_mb=split_size_mb,
                    solid=solid,
                    total_size=total_size,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            else:
                return ArchiveResult(success=False, error_message=f"Unsupported format: {archive_format}")

            # Verify output file
            if not out_file.exists():
                return ArchiveResult(success=False, error_message="Archive output file was not created.")

            archive_size = out_file.stat().st_size
            elapsed = time.time() - start_time
            saved_bytes = total_size - archive_size
            saved_percent = round((saved_bytes / total_size * 100), 1) if total_size > 0 else 0.0
            is_larger = archive_size > total_size

            return ArchiveResult(
                success=True,
                output_path=str(out_file),
                original_size=total_size,
                archive_size=archive_size,
                saved_percent=saved_percent,
                is_larger=is_larger,
                files_count=total_files,
                elapsed_seconds=elapsed,
            )

        except Exception as exc:
            # Cleanup on failure or cancellation
            if out_file.exists():
                with contextlib.suppress(OSError):
                    out_file.unlink()
            # Also clean up any split files if generated
            for part in out_file.parent.glob(f"{out_file.name}.*"):
                with contextlib.suppress(OSError):
                    part.unlink()
            msg = str(exc)
            if "cancelled" in msg.lower():
                return ArchiveResult(success=False, error_message="Operation cancelled by user.")
            logger.exception("Archive creation failed: %s", exc)
            return ArchiveResult(success=False, error_message=f"Compression failed: {exc}")

    def _create_zip(
        self,
        resolved_files: list[tuple[str, str, int]],
        output_path: Path,
        preset: str,
        password: str,
        total_size: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> None:
        """Create standard ZIP archive with streaming writes and Zip64 support."""
        # Compression level mapping
        comp_type = zipfile.ZIP_DEFLATED
        comp_level = 6  # Balanced
        if preset == "fast":
            comp_level = 1
        elif preset == "maximum":
            comp_level = 9
        elif preset == "store":
            comp_type = zipfile.ZIP_STORED
            comp_level = None

        bytes_processed = 0
        files_processed = 0

        # If password requested and pyzipper is missing, fall back to 7-Zip CLI for AES-256 ZIP
        if password and pyzipper is None:
            if self.has_7z:
                return self._create_7z(
                    resolved_files=resolved_files,
                    output_path=output_path,
                    preset=preset,
                    password=password,
                    encrypt_filenames=False,
                    split_size_mb=0,
                    solid=False,
                    total_size=total_size,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                    archive_type="zip",
                )
            raise RuntimeError("Для шифрування ZIP потрібен модуль pyzipper або встановлений 7-Zip.")

        # Enable Zip64 by default for archives > 4GB or with > 65535 files
        zip_class = pyzipper.AESZipFile if password else zipfile.ZipFile
        with zip_class(
            output_path,
            mode="w",
            compression=comp_type,
            compresslevel=comp_level if comp_type == zipfile.ZIP_DEFLATED else None,
            allowZip64=True,
        ) as zf:
            if password:
                zf.setpassword(password.encode("utf-8"))
                zf.setencryption(pyzipper.WZ_AES, nbits=256)

            for disk_path, arc_name, _fsize in resolved_files:
                if cancel_requested and cancel_requested():
                    raise RuntimeError("Compression cancelled by user.")

                # Stream file into zip using buffer
                zinfo = zf.zipinfo_cls(arc_name) if password else zipfile.ZipInfo.from_file(disk_path, arc_name)
                if password:
                    zinfo.date_time = time.localtime(os.stat(disk_path).st_mtime)[:6]
                zinfo.compress_type = comp_type
                # Preserve permissions
                with contextlib.suppress(OSError):
                    zinfo.external_attr = (os.stat(disk_path).st_mode & 0xFFFF) << 16

                chunk_size = 1024 * 1024  # 1MB
                with open(disk_path, "rb") as src_f, zf.open(zinfo, mode="w") as dest_f:
                    while True:
                        if cancel_requested and cancel_requested():
                            raise RuntimeError("Compression cancelled by user.")
                        chunk = src_f.read(chunk_size)
                        if not chunk:
                            break
                        dest_f.write(chunk)
                        bytes_processed += len(chunk)
                        if progress_callback:
                            pct = min(100.0, (bytes_processed / max(1, total_size)) * 100)
                            elapsed = time.time() - start_time
                            progress_callback(pct, files_processed, total_files, bytes_processed, total_size, arc_name, elapsed)

                files_processed += 1
                if progress_callback:
                    pct = min(100.0, (bytes_processed / max(1, total_size)) * 100)
                    elapsed = time.time() - start_time
                    progress_callback(pct, files_processed, total_files, bytes_processed, total_size, arc_name, elapsed)

    def _create_tar(
        self,
        resolved_files: list[tuple[str, str, int]],
        output_path: Path,
        tar_format: str,
        preset: str,
        total_size: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> None:
        """Create TAR, TAR.GZ, TAR.BZ2, or TAR.XZ archive with chunked streaming."""
        mode = "w"
        if tar_format in {"tar.gz", "tgz"}:
            mode = "w:gz"
        elif tar_format in {"tar.bz2", "tbz2"}:
            mode = "w:bz2"
        elif tar_format in {"tar.xz", "txz"}:
            mode = "w:xz"

        bytes_processed = 0
        files_processed = 0

        with tarfile.open(output_path, mode=mode) as tf:
            for disk_path, arc_name, fsize in resolved_files:
                if cancel_requested and cancel_requested():
                    raise RuntimeError("Compression cancelled by user.")

                ti = tf.gettarinfo(disk_path, arcname=arc_name)
                if ti.isreg():
                    with open(disk_path, "rb") as src_f:
                        tf.addfile(ti, fileobj=src_f)
                else:
                    tf.addfile(ti)

                bytes_processed += fsize
                files_processed += 1
                if progress_callback:
                    pct = min(100.0, (bytes_processed / max(1, total_size)) * 100)
                    elapsed = time.time() - start_time
                    progress_callback(pct, files_processed, total_files, bytes_processed, total_size, arc_name, elapsed)

    def _create_single_compressed(
        self,
        resolved_files: list[tuple[str, str, int]],
        output_path: Path,
        comp_type: str,
        preset: str,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> None:
        """Compress a single file into .gz, .bz2, or .xz."""
        disk_path, arc_name, fsize = resolved_files[0]
        chunk_size = 1024 * 1024  # 1MB
        bytes_processed = 0

        # Choose writer
        if comp_type == "gz":
            writer_cls = gzip.open
        elif comp_type == "bz2":
            writer_cls = bz2.open
        elif comp_type == "xz":
            writer_cls = lzma.open
        else:
            raise ValueError(f"Unknown single-file compression: {comp_type}")

        with open(disk_path, "rb") as src_f, writer_cls(output_path, "wb") as dest_f:
            while True:
                if cancel_requested and cancel_requested():
                    raise RuntimeError("Compression cancelled by user.")
                chunk = src_f.read(chunk_size)
                if not chunk:
                    break
                dest_f.write(chunk)
                bytes_processed += len(chunk)
                if progress_callback:
                    pct = min(100.0, (bytes_processed / max(1, fsize)) * 100)
                    elapsed = time.time() - start_time
                    progress_callback(pct, 1, 1, bytes_processed, fsize, arc_name, elapsed)

    def _create_7z(
        self,
        resolved_files: list[tuple[str, str, int]],
        output_path: Path,
        preset: str,
        password: str,
        encrypt_filenames: bool,
        split_size_mb: int,
        solid: bool,
        total_size: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
        archive_type: str = "7z",
    ) -> None:
        """Create 7Z or ZIP archive using 7-Zip CLI."""
        assert self._7z_path is not None
        level_flag = "-mx=5"
        if preset == "fast":
            level_flag = "-mx=1"
        elif preset == "maximum":
            level_flag = "-mx=9"

        cmd = [self._7z_path, "a", f"-t{archive_type}", str(output_path), level_flag, "-bsp1"]
        if archive_type == "7z" and not solid:
            cmd.append("-ms=off")
        if password:
            cmd.append(f"-p{password}")
            if archive_type == "7z" and encrypt_filenames:
                cmd.append("-mhe=on")
            elif archive_type == "zip":
                cmd.append("-mem=AES256")
        if split_size_mb > 0:
            cmd.append(f"-v{split_size_mb}m")

        # Create temporary file list to avoid command line length limits
        temp_list_file = output_path.parent / f"_7z_list_{int(time.time() * 1000)}.txt"
        try:
            with open(temp_list_file, "w", encoding="utf-8") as f:
                # Group by parent source or write disk paths
                for disk_p, _, _ in resolved_files:
                    f.write(f"{disk_p}\n")

            cmd.append(f"@{temp_list_file}")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Monitor progress
            while proc.poll() is None:
                if cancel_requested and cancel_requested():
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise RuntimeError("Compression cancelled by user.")

                line = proc.stdout.readline() if proc.stdout else ""
                if line and "%" in line:
                    # Parse 7z percentage output like " 45% 12/40"
                    parts = line.strip().split()
                    for p in parts:
                        if p.endswith("%"):
                            try:
                                val = float(p[:-1])
                                if progress_callback:
                                    elapsed = time.time() - start_time
                                    bytes_done = int(total_size * (val / 100.0))
                                    progress_callback(val, 0, total_files, bytes_done, total_size, "Compressing...", elapsed)
                            except ValueError:
                                pass
                time.sleep(0.05)

            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"7-Zip exited with code {proc.returncode}: {stderr or stdout}")

        finally:
            if temp_list_file.exists():
                with contextlib.suppress(OSError):
                    temp_list_file.unlink()

    def _create_rar(
        self,
        resolved_files: list[tuple[str, str, int]],
        output_path: Path,
        preset: str,
        password: str,
        encrypt_filenames: bool,
        split_size_mb: int,
        solid: bool,
        total_size: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> None:
        """Create a RAR archive through the official WinRAR command-line tool."""
        assert self._rar_path is not None
        compression_level = {"store": "0", "fast": "1", "balanced": "3", "maximum": "5"}.get(preset, "3")
        cmd = [self._rar_path, "a", f"-m{compression_level}", "-ep1"]
        cmd.append("-s" if solid else "-s-")
        if password:
            cmd.append(f"-hp{password}" if encrypt_filenames else f"-p{password}")
        if split_size_mb > 0:
            cmd.append(f"-v{split_size_mb}m")

        file_list = output_path.parent / f"_rar_list_{int(time.time() * 1000)}.txt"
        try:
            with file_list.open("w", encoding="utf-8") as stream:
                for disk_path, _, _ in resolved_files:
                    stream.write(f"{disk_path}\n")

            cmd.extend([str(output_path), f"@{file_list}"])
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            while process.poll() is None:
                if cancel_requested and cancel_requested():
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise RuntimeError("Compression cancelled by user.")
                time.sleep(0.05)

            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"WinRAR exited with code {process.returncode}: {stderr or stdout}")
            if progress_callback:
                progress_callback(100.0, total_files, total_files, total_size, total_size, output_path.name, time.time() - start_time)
        finally:
            if file_list.exists():
                with contextlib.suppress(OSError):
                    file_list.unlink()

    # =========================================================================
    # EXTRACT ARCHIVE & SECURITY
    # =========================================================================

    def list_archive(self, archive_path: str, password: str = "") -> list[ArchiveEntry]:
        """List files and folders inside an archive with sizes, dates, and types."""
        arc = Path(archive_path).resolve()
        if not arc.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        entries: list[ArchiveEntry] = []
        name_lower = arc.name.lower()

        # Check if ZIP
        if zipfile.is_zipfile(arc):
            try:
                zip_class = pyzipper.AESZipFile if pyzipper is not None else zipfile.ZipFile
                with zip_class(arc, "r") as zf:
                    if password:
                        zf.setpassword(password.encode("utf-8"))
                    for zi in zf.infolist():
                        is_dir = zi.is_dir()
                        # Date tuple: (year, month, day, hour, min, sec)
                        try:
                            mod_time = time.mktime((*zi.date_time, 0, 0, -1))
                        except Exception:
                            mod_time = 0.0
                        entries.append(
                            ArchiveEntry(
                                name=Path(zi.filename).name or zi.filename,
                                path=zi.filename,
                                size=zi.file_size,
                                compressed_size=zi.compress_size,
                                is_dir=is_dir,
                                modified=mod_time,
                                icon_type=get_file_icon_type(zi.filename, is_dir),
                            )
                        )
                return entries
            except zipfile.BadZipFile as e:
                raise ValueError(f"Corrupted or invalid ZIP archive: {e}") from e

        # Check if TAR
        if tarfile.is_tarfile(arc):
            try:
                with tarfile.open(arc, "r:*") as tf:
                    for ti in tf.getmembers():
                        is_dir = ti.isdir()
                        entries.append(
                            ArchiveEntry(
                                name=Path(ti.name).name or ti.name,
                                path=ti.name,
                                size=ti.size,
                                compressed_size=ti.size,
                                is_dir=is_dir,
                                modified=float(ti.mtime),
                                icon_type=get_file_icon_type(ti.name, is_dir),
                            )
                        )
                return entries
            except tarfile.TarError as e:
                raise ValueError(f"Corrupted or invalid TAR archive: {e}") from e

        # Check single file compressed (.gz, .bz2, .xz)
        if name_lower.endswith(".gz") and not name_lower.endswith(".tar.gz"):
            stem = arc.stem
            entries.append(
                ArchiveEntry(
                    name=stem,
                    path=stem,
                    size=arc.stat().st_size,
                    compressed_size=arc.stat().st_size,
                    is_dir=False,
                    modified=arc.stat().st_mtime,
                    icon_type=get_file_icon_type(stem),
                )
            )
            return entries
        if name_lower.endswith(".bz2") and not name_lower.endswith(".tar.bz2"):
            stem = arc.stem
            entries.append(
                ArchiveEntry(
                    name=stem,
                    path=stem,
                    size=arc.stat().st_size,
                    compressed_size=arc.stat().st_size,
                    is_dir=False,
                    modified=arc.stat().st_mtime,
                    icon_type=get_file_icon_type(stem),
                )
            )
            return entries
        if name_lower.endswith(".xz") and not name_lower.endswith(".tar.xz"):
            stem = arc.stem
            entries.append(
                ArchiveEntry(
                    name=stem,
                    path=stem,
                    size=arc.stat().st_size,
                    compressed_size=arc.stat().st_size,
                    is_dir=False,
                    modified=arc.stat().st_mtime,
                    icon_type=get_file_icon_type(stem),
                )
            )
            return entries

        # Try 7z if available
        if self.has_7z:
            assert self._7z_path is not None
            cmd = [self._7z_path, "l", "-slt", str(arc)]
            if password:
                cmd.append(f"-p{password}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                current_entry: dict[str, str] = {}
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        if "Path" in current_entry and current_entry["Path"] != str(arc):
                            path_val = current_entry.get("Path", "")
                            size_val = int(current_entry.get("Size", 0)) if current_entry.get("Size", "").isdigit() else 0
                            csize_val = (
                                int(current_entry.get("Packed Size", 0)) if current_entry.get("Packed Size", "").isdigit() else size_val
                            )
                            is_dir = current_entry.get("Folder", "") == "+"
                            entries.append(
                                ArchiveEntry(
                                    name=Path(path_val).name or path_val,
                                    path=path_val,
                                    size=size_val,
                                    compressed_size=csize_val,
                                    is_dir=is_dir,
                                    modified=0.0,
                                    icon_type=get_file_icon_type(path_val, is_dir),
                                )
                            )
                        current_entry = {}
                    elif "=" in line:
                        k, v = line.split("=", 1)
                        current_entry[k.strip()] = v.strip()
                return entries

        raise ValueError(f"Unsupported or unreadable archive format: {arc.suffix}")

    def validate_safe_path(self, dest_dir: Path, target_path: str) -> Path:
        """Prevent Zip Slip / Path Traversal vulnerabilities."""
        # Clean path, strip leading slashes or Windows drive letters
        cleaned = os.path.normpath(target_path).lstrip("/\\")
        if cleaned.startswith(".." + os.sep) or cleaned == "..":
            raise ArchiveSecurityError(f"Path traversal attempt detected: {target_path}")

        resolved_dest = dest_dir.resolve()
        resolved_target = (resolved_dest / cleaned).resolve()

        # Target must be strictly inside or equal to dest_dir
        try:
            resolved_target.relative_to(resolved_dest)
        except ValueError:
            raise ArchiveSecurityError(f"Zip Slip detected: target '{target_path}' escapes extraction directory.") from None

        return resolved_target

    def extract_archive(
        self,
        archive_path: str,
        destination_dir: str,
        selected_files: list[str] | None = None,
        password: str = "",
        overwrite_mode: str = "ask",  # "replace", "skip", "keep_both"
        cancel_requested: Callable[[], bool] | None = None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None = None,
    ) -> ExtractResult:
        """Extract archive safely with Path Traversal protection and disk space checks."""
        start_time = time.time()
        arc = Path(archive_path).resolve()
        dest = Path(destination_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)

        if not arc.exists():
            return ExtractResult(success=False, error_message="Source archive not found.")

        # Inspect content & sizes
        try:
            entries = self.list_archive(str(arc), password=password)
        except Exception as e:
            msg = str(e)
            if "password" in msg.lower():
                return ExtractResult(success=False, error_message="Incorrect password or encrypted archive.")
            return ExtractResult(success=False, error_message=f"Cannot read archive: {msg}")

        # Filter by selected files if requested
        if selected_files:
            selected_set = set(selected_files)
            entries_to_extract = [
                e for e in entries if e.path in selected_set or any(e.path.startswith(s.rstrip("/") + "/") for s in selected_set)
            ]
        else:
            entries_to_extract = entries

        total_uncompressed_bytes = sum(e.size for e in entries_to_extract if not e.is_dir)
        total_files = len([e for e in entries_to_extract if not e.is_dir])

        # Archive bomb detection: ratio check
        arc_size = max(1, arc.stat().st_size)
        ratio = total_uncompressed_bytes / arc_size
        if ratio > 100.0 and total_uncompressed_bytes > 1024 * 1024 * 1024:  # > 100:1 ratio and > 1GB
            raise ArchiveSecurityError(
                f"Potential archive bomb detected: compression ratio {ratio:.1f}:1 ({total_uncompressed_bytes / 1e9:.2f} GB)."
            )

        # Free space check
        try:
            free_bytes = shutil.disk_usage(dest).free
            if free_bytes < total_uncompressed_bytes:
                req_gb = total_uncompressed_bytes / (1024**3)
                avail_gb = free_bytes / (1024**3)
                return ExtractResult(
                    success=False,
                    error_message=f"Not enough free disk space. Required: {req_gb:.2f} GB, Available: {avail_gb:.2f} GB",
                )
        except OSError:
            pass

        # Perform extraction
        name_lower = arc.name.lower()
        try:
            if zipfile.is_zipfile(arc):
                try:
                    return self._extract_zip(
                        arc=arc,
                        dest=dest,
                        entries=entries_to_extract,
                        password=password,
                        overwrite_mode=overwrite_mode,
                        total_bytes=total_uncompressed_bytes,
                        total_files=total_files,
                        start_time=start_time,
                        cancel_requested=cancel_requested,
                        progress_callback=progress_callback,
                    )
                except Exception as zip_err:
                    if self.has_7z and password:
                        logger.warning("Standard ZIP extraction failed (%s), falling back to 7-Zip CLI...", zip_err)
                        return self._extract_7z(
                            arc=arc,
                            dest=dest,
                            selected_files=selected_files,
                            password=password,
                            overwrite_mode=overwrite_mode,
                            total_bytes=total_uncompressed_bytes,
                            total_files=total_files,
                            start_time=start_time,
                            cancel_requested=cancel_requested,
                            progress_callback=progress_callback,
                        )
                    raise
            elif tarfile.is_tarfile(arc):
                return self._extract_tar(
                    arc=arc,
                    dest=dest,
                    entries=entries_to_extract,
                    overwrite_mode=overwrite_mode,
                    total_bytes=total_uncompressed_bytes,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            elif name_lower.endswith(".gz") and not name_lower.endswith(".tar.gz"):
                return self._extract_single(arc, dest, "gz", start_time, cancel_requested, progress_callback)
            elif name_lower.endswith(".bz2") and not name_lower.endswith(".tar.bz2"):
                return self._extract_single(arc, dest, "bz2", start_time, cancel_requested, progress_callback)
            elif name_lower.endswith(".xz") and not name_lower.endswith(".tar.xz"):
                return self._extract_single(arc, dest, "xz", start_time, cancel_requested, progress_callback)
            elif self.has_7z:
                return self._extract_7z(
                    arc=arc,
                    dest=dest,
                    selected_files=selected_files,
                    password=password,
                    overwrite_mode=overwrite_mode,
                    total_bytes=total_uncompressed_bytes,
                    total_files=total_files,
                    start_time=start_time,
                    cancel_requested=cancel_requested,
                    progress_callback=progress_callback,
                )
            else:
                return ExtractResult(success=False, error_message=f"Unsupported archive format: {arc.suffix}")

        except Exception as exc:
            msg = str(exc)
            if "cancelled" in msg.lower():
                return ExtractResult(success=False, error_message="Extraction cancelled by user.")
            logger.exception("Archive extraction failed: %s", exc)
            return ExtractResult(success=False, error_message=f"Extraction failed: {exc}")

    def _resolve_collision_path(self, target_path: Path, overwrite_mode: str) -> Path | None:
        """Handle target path collision according to mode ('replace', 'skip', 'keep_both')."""
        if not target_path.exists():
            return target_path
        if overwrite_mode == "replace":
            return target_path
        if overwrite_mode == "skip":
            return None
        # keep_both: add " (1)", " (2)", etc.
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        counter = 1
        while True:
            new_target = parent / f"{stem} ({counter}){suffix}"
            if not new_target.exists():
                return new_target
            counter += 1

    def _extract_zip(
        self,
        arc: Path,
        dest: Path,
        entries: list[ArchiveEntry],
        password: str,
        overwrite_mode: str,
        total_bytes: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> ExtractResult:
        bytes_extracted = 0
        files_extracted = 0

        zip_class = pyzipper.AESZipFile if pyzipper is not None else zipfile.ZipFile
        with zip_class(arc, "r") as zf:
            if password:
                zf.setpassword(password.encode("utf-8"))

            for entry in entries:
                if cancel_requested and cancel_requested():
                    raise RuntimeError("Extraction cancelled by user.")

                target_file = self.validate_safe_path(dest, entry.path)

                if entry.is_dir:
                    target_file.mkdir(parents=True, exist_ok=True)
                    continue

                target_file = self._resolve_collision_path(target_file, overwrite_mode)
                if target_file is None:  # Skipped
                    continue

                target_file.parent.mkdir(parents=True, exist_ok=True)

                chunk_size = 1024 * 1024  # 1MB buffer
                with zf.open(entry.path, "r") as src_f, open(target_file, "wb") as dest_f:
                    while True:
                        if cancel_requested and cancel_requested():
                            raise RuntimeError("Extraction cancelled by user.")
                        chunk = src_f.read(chunk_size)
                        if not chunk:
                            break
                        dest_f.write(chunk)
                        bytes_extracted += len(chunk)
                        if progress_callback:
                            pct = min(100.0, (bytes_extracted / max(1, total_bytes)) * 100)
                            elapsed = time.time() - start_time
                            progress_callback(pct, files_extracted, total_files, bytes_extracted, total_bytes, entry.name, elapsed)

                # Restore timestamp
                if entry.modified > 0:
                    with contextlib.suppress(OSError):
                        os.utime(target_file, (entry.modified, entry.modified))

                files_extracted += 1

        return ExtractResult(
            success=True,
            destination=str(dest),
            files_extracted=files_extracted,
            bytes_extracted=bytes_extracted,
            elapsed_seconds=time.time() - start_time,
        )

    def _extract_tar(
        self,
        arc: Path,
        dest: Path,
        entries: list[ArchiveEntry],
        overwrite_mode: str,
        total_bytes: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> ExtractResult:
        bytes_extracted = 0
        files_extracted = 0

        with tarfile.open(arc, "r:*") as tf:
            for entry in entries:
                if cancel_requested and cancel_requested():
                    raise RuntimeError("Extraction cancelled by user.")

                ti = tf.getmember(entry.path)
                # Security: Symlink protection
                if ti.issym() or ti.islnk():
                    # Validate that link target does not point outside destination
                    link_target = ti.linkname
                    if os.path.isabs(link_target) or ".." in link_target:
                        continue  # Skip dangerous symlink

                target_file = self.validate_safe_path(dest, entry.path)

                if ti.isdir():
                    target_file.mkdir(parents=True, exist_ok=True)
                    continue

                target_file = self._resolve_collision_path(target_file, overwrite_mode)
                if target_file is None:  # Skipped
                    continue

                target_file.parent.mkdir(parents=True, exist_ok=True)

                if ti.isreg():
                    fileobj = tf.extractfile(ti)
                    if fileobj:
                        chunk_size = 1024 * 1024
                        with open(target_file, "wb") as dest_f:
                            while True:
                                if cancel_requested and cancel_requested():
                                    raise RuntimeError("Extraction cancelled by user.")
                                chunk = fileobj.read(chunk_size)
                                if not chunk:
                                    break
                                dest_f.write(chunk)
                                bytes_extracted += len(chunk)
                                if progress_callback:
                                    pct = min(100.0, (bytes_extracted / max(1, total_bytes)) * 100)
                                    elapsed = time.time() - start_time
                                    progress_callback(pct, files_extracted, total_files, bytes_extracted, total_bytes, entry.name, elapsed)

                # Restore timestamp & permissions
                try:
                    os.chmod(target_file, ti.mode)
                    os.utime(target_file, (ti.mtime, ti.mtime))
                except OSError:
                    pass

                files_extracted += 1

        return ExtractResult(
            success=True,
            destination=str(dest),
            files_extracted=files_extracted,
            bytes_extracted=bytes_extracted,
            elapsed_seconds=time.time() - start_time,
        )

    def _extract_single(
        self,
        arc: Path,
        dest: Path,
        comp_type: str,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> ExtractResult:
        """Extract a single-file compressed archive (.gz, .bz2, .xz)."""
        target_name = arc.stem
        target_path = self.validate_safe_path(dest, target_name)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if comp_type == "gz":
            reader_cls = gzip.open
        elif comp_type == "bz2":
            reader_cls = bz2.open
        elif comp_type == "xz":
            reader_cls = lzma.open
        else:
            raise ValueError(f"Unknown single-file compression: {comp_type}")

        chunk_size = 1024 * 1024
        bytes_extracted = 0

        with reader_cls(arc, "rb") as src_f, open(target_path, "wb") as dest_f:
            while True:
                if cancel_requested and cancel_requested():
                    raise RuntimeError("Extraction cancelled by user.")
                chunk = src_f.read(chunk_size)
                if not chunk:
                    break
                dest_f.write(chunk)
                bytes_extracted += len(chunk)
                if progress_callback:
                    elapsed = time.time() - start_time
                    progress_callback(50.0, 1, 1, bytes_extracted, bytes_extracted, target_name, elapsed)

        return ExtractResult(
            success=True,
            destination=str(dest),
            files_extracted=1,
            bytes_extracted=bytes_extracted,
            elapsed_seconds=time.time() - start_time,
        )

    def _extract_7z(
        self,
        arc: Path,
        dest: Path,
        selected_files: list[str] | None,
        password: str,
        overwrite_mode: str,
        total_bytes: int,
        total_files: int,
        start_time: float,
        cancel_requested: Callable[[], bool] | None,
        progress_callback: Callable[[float, int, int, int, int, str, float], None] | None,
    ) -> ExtractResult:
        """Extract using 7-Zip CLI with security and progress handling."""
        assert self._7z_path is not None
        cmd = [self._7z_path, "x", str(arc), f"-o{dest}", "-bsp1"]

        # Overwrite mode flag for 7z
        if overwrite_mode == "replace":
            cmd.append("-aoa")
        elif overwrite_mode == "skip":
            cmd.append("-aos")
        elif overwrite_mode == "keep_both":
            cmd.append("-aou")

        if password:
            cmd.append(f"-p{password}")
        else:
            cmd.append("-p-")  # Do not prompt on console

        if selected_files:
            cmd.extend(selected_files)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        while proc.poll() is None:
            if cancel_requested and cancel_requested():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise RuntimeError("Extraction cancelled by user.")

            line = proc.stdout.readline() if proc.stdout else ""
            if line and "%" in line:
                for p in line.strip().split():
                    if p.endswith("%"):
                        try:
                            val = float(p[:-1])
                            if progress_callback:
                                elapsed = time.time() - start_time
                                bytes_done = int(total_bytes * (val / 100.0))
                                progress_callback(val, 0, total_files, bytes_done, total_bytes, "Extracting...", elapsed)
                        except ValueError:
                            pass
            time.sleep(0.05)

        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            if "wrong password" in (stdout + stderr).lower() or "cannot open encrypted" in (stdout + stderr).lower():
                return ExtractResult(success=False, error_message="Incorrect password.")
            return ExtractResult(success=False, error_message=f"7-Zip extraction error ({proc.returncode}): {stderr or stdout}")

        return ExtractResult(
            success=True,
            destination=str(dest),
            files_extracted=total_files,
            bytes_extracted=total_bytes,
            elapsed_seconds=time.time() - start_time,
        )
