from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import shutil
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.paths import APP_DATA_DIR, find_ffprobe

FFMPEG_WIN64_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
DEFAULT_CHECK_INTERVAL_SEC = 24 * 60 * 60

ProgressCallback = Callable[[str], None]
DownloadFunc = Callable[[str, Path, ProgressCallback | None], None]


@dataclass(frozen=True)
class FfmpegAutoInstallResult:
    status: str
    message: str
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    changed: bool = False
    error: str = ""


class FfmpegAutoInstaller:
    def __init__(
        self,
        install_dir: Path | None = None,
        *,
        download_url: str = FFMPEG_WIN64_URL,
        check_interval_sec: int = DEFAULT_CHECK_INTERVAL_SEC,
        download_func: DownloadFunc | None = None,
        now_func: Callable[[], float] = time.time,
        platform_key: str | None = None,
    ) -> None:
        self.install_dir = Path(install_dir or (APP_DATA_DIR / "ffmpeg")).expanduser()
        self.download_url = download_url
        self.check_interval_sec = max(3600, int(check_interval_sec))
        self.download_func = download_func or self._download_file
        self.now_func = now_func
        self.platform_key = platform_key

    @property
    def current_dir(self) -> Path:
        return self.install_dir / "current"

    @property
    def metadata_path(self) -> Path:
        return self.install_dir / "install.json"

    def managed_ffmpeg_path(self) -> Path:
        return self.current_dir / "bin" / self._binary_name("ffmpeg")

    def managed_ffprobe_path(self) -> Path:
        return self.current_dir / "bin" / self._binary_name("ffprobe")

    def find_managed_ffmpeg(self) -> str:
        path = self.managed_ffmpeg_path()
        return str(path) if path.exists() else ""

    def is_managed_path(self, value: str | Path) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        try:
            path = Path(text).expanduser().resolve()
            base = self.install_dir.resolve()
        except OSError:
            return False
        return path == base or base in path.parents

    def should_run(self, current_ffmpeg_path: str = "", *, auto_update: bool = True, force: bool = False) -> bool:
        if force:
            return True
        current = Path(str(current_ffmpeg_path or "")).expanduser() if current_ffmpeg_path else None
        if not current or not current.exists():
            return True
        if not auto_update or not self.is_managed_path(current):
            return False
        checked_at = float(self._read_metadata().get("checked_at") or 0)
        return self.now_func() - checked_at >= self.check_interval_sec

    def ensure(
        self,
        current_ffmpeg_path: str = "",
        *,
        auto_update: bool = True,
        force: bool = False,
        progress_cb: ProgressCallback | None = None,
    ) -> FfmpegAutoInstallResult:
        current = Path(str(current_ffmpeg_path or "")).expanduser() if current_ffmpeg_path else None
        current_exists = bool(current and current.exists())
        if current_exists and not force and not self.is_managed_path(current):
            return FfmpegAutoInstallResult(
                status="external",
                message="External FFmpeg is configured; auto-update is skipped.",
                ffmpeg_path=str(current),
                ffprobe_path=find_ffprobe(str(current)) or "",
            )
        if not self.should_run(str(current or ""), auto_update=auto_update, force=force):
            managed = self.find_managed_ffmpeg()
            ffmpeg_path = str(current) if current_exists else managed
            return FfmpegAutoInstallResult(
                status="current",
                message="Managed FFmpeg is already current.",
                ffmpeg_path=ffmpeg_path,
                ffprobe_path=find_ffprobe(ffmpeg_path) or "",
            )
        if self._platform_key() != "win64":
            return FfmpegAutoInstallResult(
                status="unsupported",
                message="Automatic FFmpeg download is currently supported only on Windows x64.",
                ffmpeg_path=str(current or "") if current_exists else "",
                ffprobe_path=find_ffprobe(str(current or "")) or "",
                error="unsupported_platform",
            )

        self.install_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self.install_dir / "ffmpeg-download.zip"
        try:
            if progress_cb:
                progress_cb("Downloading FFmpeg...")
            self.download_func(self.download_url, archive_path, progress_cb)
            archive_sha256 = self._sha256(archive_path)
            ffmpeg_path = self._install_zip(archive_path)
            ffprobe_path = str(self.managed_ffprobe_path()) if self.managed_ffprobe_path().exists() else (find_ffprobe(ffmpeg_path) or "")
            self._write_metadata(
                {
                    "source_url": self.download_url,
                    "archive_sha256": archive_sha256,
                    "checked_at": self.now_func(),
                    "installed_at": self.now_func(),
                    "ffmpeg_path": ffmpeg_path,
                    "ffprobe_path": ffprobe_path,
                }
            )
        except Exception as exc:
            return FfmpegAutoInstallResult(
                status="error",
                message=f"Failed to install FFmpeg: {exc}",
                ffmpeg_path=str(current or "") if current_exists else "",
                ffprobe_path=find_ffprobe(str(current or "")) or "",
                error=str(exc),
            )
        finally:
            with contextlib.suppress(OSError):
                archive_path.unlink(missing_ok=True)

        return FfmpegAutoInstallResult(
            status="updated" if current_exists else "downloaded",
            message="FFmpeg was installed automatically.",
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            changed=True,
        )

    def _platform_key(self) -> str:
        if self.platform_key:
            return self.platform_key
        machine = platform.machine().lower()
        if os.name == "nt" and machine in {"amd64", "x86_64"}:
            return "win64"
        return "unsupported"

    def _binary_name(self, name: str) -> str:
        return f"{name}.exe" if self._platform_key() == "win64" else name

    def _download_file(self, url: str, destination: Path, progress_cb: ProgressCallback | None = None) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "MediaConverter/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            last_percent = -1
            with destination.open("wb") as fh:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if progress_cb and total > 0:
                        percent = int(done * 100 / total)
                        if percent >= last_percent + 10:
                            last_percent = percent
                            progress_cb(f"Downloading FFmpeg... {percent}%")

    def _install_zip(self, archive_path: Path) -> str:
        staging = self.install_dir / "staging"
        next_dir = self.install_dir / "next"
        self._safe_rmtree(staging)
        self._safe_rmtree(next_dir)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(staging)
            ffmpeg_name = self._binary_name("ffmpeg")
            matches = list(staging.rglob(ffmpeg_name))
            if not matches:
                raise RuntimeError("ffmpeg binary was not found in the archive")
            package_root = matches[0].parent.parent
            shutil.copytree(package_root, next_dir)
            installed_ffmpeg = next_dir / "bin" / ffmpeg_name
            if not installed_ffmpeg.exists():
                raise RuntimeError("installed ffmpeg binary is missing")
            self._safe_rmtree(self.current_dir)
            shutil.move(str(next_dir), str(self.current_dir))
        finally:
            self._safe_rmtree(staging)
            self._safe_rmtree(next_dir)
        return str(self.managed_ffmpeg_path())

    def _safe_rmtree(self, path: Path) -> None:
        if not path.exists():
            return
        base = self.install_dir.resolve()
        target = path.resolve()
        if target != base and base not in target.parents:
            raise RuntimeError(f"refusing to remove path outside FFmpeg install dir: {target}")
        shutil.rmtree(target)

    def _read_metadata(self) -> dict:
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_metadata(self, data: dict) -> None:
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
