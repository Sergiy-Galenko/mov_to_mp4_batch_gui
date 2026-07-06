"""Advanced folder scanner with filtering and exclude patterns.

Provides recursive folder scanning with media type filtering,
glob-based exclude patterns, and file size constraints.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from utils.files import media_type


# Default patterns to always exclude
_DEFAULT_EXCLUDES = {
    "*.tmp",
    "*.temp",
    "*.part",
    "*.crdownload",
    "*_thumb.*",
    "._*",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}


class FolderScanner:
    """Scans folders recursively with advanced filtering options."""

    def __init__(
        self,
        *,
        type_filter: Optional[str] = None,
        exclude_patterns: Optional[Iterable[str]] = None,
        min_size_bytes: int = 0,
        max_size_bytes: int = 0,
        include_hidden: bool = False,
    ) -> None:
        """
        Args:
            type_filter: Limit to 'video', 'audio', 'image', 'subtitle', 'text', or None for all.
            exclude_patterns: Glob patterns for filenames to skip (e.g. '*.tmp').
            min_size_bytes: Skip files smaller than this (0 = no limit).
            max_size_bytes: Skip files larger than this (0 = no limit).
            include_hidden: Include hidden files/folders (starting with dot).
        """
        self.type_filter = type_filter
        self.exclude_patterns: Set[str] = set(exclude_patterns or set()) | _DEFAULT_EXCLUDES
        self.min_size_bytes = max(0, min_size_bytes)
        self.max_size_bytes = max(0, max_size_bytes)
        self.include_hidden = include_hidden

    def scan(self, folder: Path) -> List[Path]:
        """Recursively scan folder and return filtered file list."""
        if not folder.exists() or not folder.is_dir():
            return []

        results: List[Path] = []
        try:
            for item in sorted(folder.rglob("*")):
                if not item.is_file():
                    continue
                if self._should_skip(item):
                    continue
                results.append(item)
        except PermissionError:
            pass
        return results

    def scan_with_stats(self, folder: Path) -> Dict[str, object]:
        """Scan folder and return results with statistics."""
        all_files: List[Path] = []
        excluded_count = 0
        type_filtered_count = 0
        size_filtered_count = 0

        if not folder.exists() or not folder.is_dir():
            return {
                "files": [],
                "total_scanned": 0,
                "excluded": 0,
                "type_filtered": 0,
                "size_filtered": 0,
            }

        try:
            for item in sorted(folder.rglob("*")):
                if not item.is_file():
                    continue

                # Hidden check
                if not self.include_hidden and _is_hidden(item):
                    excluded_count += 1
                    continue

                # Exclude patterns
                if self._matches_exclude(item.name):
                    excluded_count += 1
                    continue

                # Size check
                try:
                    size = item.stat().st_size
                except OSError:
                    continue
                if self.min_size_bytes and size < self.min_size_bytes:
                    size_filtered_count += 1
                    continue
                if self.max_size_bytes and size > self.max_size_bytes:
                    size_filtered_count += 1
                    continue

                # Type filter
                kind = media_type(item)
                if not kind:
                    excluded_count += 1
                    continue
                if self.type_filter and kind != self.type_filter:
                    type_filtered_count += 1
                    continue

                all_files.append(item)
        except PermissionError:
            pass

        return {
            "files": all_files,
            "total_scanned": len(all_files) + excluded_count + type_filtered_count + size_filtered_count,
            "excluded": excluded_count,
            "type_filtered": type_filtered_count,
            "size_filtered": size_filtered_count,
        }

    def _should_skip(self, path: Path) -> bool:
        """Check if a file should be skipped."""
        if not self.include_hidden and _is_hidden(path):
            return True
        if self._matches_exclude(path.name):
            return True
        kind = media_type(path)
        if not kind:
            return True
        if self.type_filter and kind != self.type_filter:
            return True
        if self.min_size_bytes or self.max_size_bytes:
            try:
                size = path.stat().st_size
            except OSError:
                return True
            if self.min_size_bytes and size < self.min_size_bytes:
                return True
            if self.max_size_bytes and size > self.max_size_bytes:
                return True
        return False

    def _matches_exclude(self, filename: str) -> bool:
        """Check if filename matches any exclude pattern."""
        lower = filename.lower()
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(lower, pattern.lower()):
                return True
        return False


def _is_hidden(path: Path) -> bool:
    """Check if file or any parent starts with dot."""
    for part in path.parts:
        if part.startswith(".") and part not in {".", ".."}:
            return True
    return False
