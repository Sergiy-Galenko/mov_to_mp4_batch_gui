from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from app.constants import (
    ANALYTICS_EMIT_INTERVAL_SEC,
    APP_TITLE,
    APP_VERSION,
    EVENT_POLL_INTERVAL_MS,
    RECENT_FOLDERS_LIMIT,
    RESOURCE_SAMPLE_INTERVAL_SEC,
    WATCH_SCAN_INTERVAL_MS,
)
from app.paths import find_ffmpeg, find_ffprobe
from app.localization import normalize_language, translate
from app.models import ConversionSettings, MediaInfo, TaskItem, TaskStatus
from app.performance_profiles import prediction_factor
from app.settings import merge_settings_maps, settings_map_to_model
from services.ffmpeg_service import FfmpegService
from services.ffmpeg_auto_installer import FfmpegAutoInstaller, FfmpegAutoInstallResult
from services.folder_scanner import FolderScanner
from services.history_store import HistoryStore
from services.media_preview_service import MediaPreviewService
from services.preset_manager import PresetManager
from services.queue_manager import QueueManager
from services.settings_manager import SettingsManager
from services.shortcut_manager import ShortcutManager
from services.smart_convert_service import recommend_settings
from services.system_tray_service import SystemTrayService
from services.theme_manager import ThemeManager
from services.watch_service import WatchService
from services.youtube_download_service import (
    DownloadProgress,
    YouTubeDownloadCancelled,
    YouTubeDownloadError,
    YouTubeDownloadService,
)
from ui.models import HistoryModel, LogModel, QueueModel
from utils.formatting import format_bytes, format_time
from utils.state import load_json_file, save_json_file
