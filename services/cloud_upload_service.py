from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from app.models import ConversionSettings

LogCallback = Callable[[str, str], None]


class CloudUploadError(RuntimeError):
    pass


class CloudUploadService:
    def upload(self, output_path: Path, settings: ConversionSettings, log_cb: LogCallback | None = None) -> None:
        if not settings.cloud_upload_enabled:
            return
        remote = str(settings.cloud_remote_path or "").strip()
        if not remote:
            raise CloudUploadError("Cloud remote path is empty.")
        tool = self._resolve_rclone_path(str(settings.cloud_rclone_path or "rclone").strip() or "rclone")
        provider = str(settings.cloud_provider or "rclone").strip()
        if provider != "rclone" and log_cb:
            log_cb("INFO", f"Cloud provider '{provider}' uses rclone remote path: {remote}")
        cmd = [tool, "copy", str(output_path), remote, "--progress"]
        if log_cb:
            log_cb("INFO", f"Cloud upload: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        except FileNotFoundError as exc:
            raise CloudUploadError("rclone not found. Set the rclone path or install rclone.") from exc
        except subprocess.TimeoutExpired as exc:
            raise CloudUploadError("Cloud upload timed out.") from exc
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "").strip()
            raise CloudUploadError(details or f"Cloud upload failed with code {result.returncode}.")

    def _resolve_rclone_path(self, tool: str) -> str:
        path = Path(tool).expanduser()
        has_path_separator = any(sep in tool for sep in ("/", "\\"))
        if path.is_absolute() or has_path_separator:
            if path.exists() and path.is_file():
                return str(path.resolve())
            raise CloudUploadError("Configured rclone path does not exist.")
        resolved = shutil.which(tool)
        if resolved and os.environ.get("MEDIA_CONVERTER_ALLOW_PATH_BINARIES", "").strip().lower() in {"1", "true", "yes"}:
            return str(Path(resolved).resolve())
        raise CloudUploadError("Set an absolute rclone path, or enable MEDIA_CONVERTER_ALLOW_PATH_BINARIES=1.")
