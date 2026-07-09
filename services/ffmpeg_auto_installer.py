from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import platform
import shutil
import stat
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.paths import APP_DATA_DIR, find_ffprobe
from services.url_security import env_flag, env_hosts, validate_https_url

FFMPEG_WIN64_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
DEFAULT_CHECK_INTERVAL_SEC = 24 * 60 * 60
DEFAULT_ALLOWED_DOWNLOAD_HOSTS = {"github.com"}
MAX_FFMPEG_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ZIP_ENTRIES = 10_000
MAX_ZIP_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024

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
        expected_sha256: str | None = None,
        allowed_hosts: set[str] | None = None,
        allow_unverified: bool | None = None,
    ) -> None:
        self.install_dir = Path(install_dir or (APP_DATA_DIR / "ffmpeg")).expanduser()
        self.download_url = download_url
        self.check_interval_sec = max(3600, int(check_interval_sec))
        self.download_func = download_func or self._download_file
        self.now_func = now_func
        self.platform_key = platform_key
        self.expected_sha256 = self._normalize_sha256(expected_sha256 or os.environ.get("MEDIA_CONVERTER_FFMPEG_SHA256", ""))
        self.allowed_hosts = allowed_hosts or env_hosts("MEDIA_CONVERTER_FFMPEG_HOSTS") or set(DEFAULT_ALLOWED_DOWNLOAD_HOSTS)
        self.allow_unverified = env_flag("MEDIA_CONVERTER_ALLOW_UNVERIFIED_FFMPEG") if allow_unverified is None else bool(allow_unverified)

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
        try:
            self._validate_download_policy()
        except Exception as exc:
            return FfmpegAutoInstallResult(
                status="error",
                message=f"FFmpeg auto-install is blocked: {exc}",
                ffmpeg_path=str(current or "") if current_exists else "",
                ffprobe_path=find_ffprobe(str(current or "")) or "",
                error=str(exc),
            )

        self.install_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self.install_dir / "ffmpeg-download.zip"
        try:
            if progress_cb:
                progress_cb("Downloading FFmpeg...")
            self.download_func(self.download_url, archive_path, progress_cb)
            archive_sha256 = self._sha256(archive_path)
            self._verify_archive_hash(archive_sha256)
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
        validated_url = validate_https_url(
            url,
            allowed_hosts=self.allowed_hosts,
            allow_local=env_flag("MEDIA_CONVERTER_ALLOW_LOCAL_DOWNLOADS"),
        )
        request = urllib.request.Request(validated_url, headers={"User-Agent": "MediaConverter/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or 0)
            if total > MAX_FFMPEG_ARCHIVE_BYTES:
                raise RuntimeError("FFmpeg archive is larger than the allowed limit")
            done = 0
            last_percent = -1
            with destination.open("wb") as fh:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if done > MAX_FFMPEG_ARCHIVE_BYTES:
                        raise RuntimeError("FFmpeg archive exceeded the allowed download limit")
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
                self._safe_extract_zip(zf, staging)
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

    def _validate_download_policy(self) -> None:
        validate_https_url(
            self.download_url,
            allowed_hosts=self.allowed_hosts,
            allow_local=env_flag("MEDIA_CONVERTER_ALLOW_LOCAL_DOWNLOADS"),
        )
        if not self.expected_sha256 and not self.allow_unverified:
            raise RuntimeError(
                "set MEDIA_CONVERTER_FFMPEG_SHA256 to the expected archive SHA-256 "
                "or explicitly opt in with MEDIA_CONVERTER_ALLOW_UNVERIFIED_FFMPEG=1"
            )

    def _verify_archive_hash(self, archive_sha256: str) -> None:
        if not self.expected_sha256:
            return
        if not hmac.compare_digest(archive_sha256.lower(), self.expected_sha256.lower()):
            raise RuntimeError("FFmpeg archive SHA-256 does not match the pinned value")

    def _safe_extract_zip(self, zf: zipfile.ZipFile, destination: Path) -> None:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise RuntimeError("FFmpeg archive contains too many files")
        total_size = 0
        base = destination.resolve()
        for info in infos:
            total_size += max(0, int(info.file_size))
            if total_size > MAX_ZIP_UNCOMPRESSED_BYTES:
                raise RuntimeError("FFmpeg archive expands beyond the allowed limit")
            target = self._safe_zip_target(base, info.filename)
            file_type = (info.external_attr >> 16) & 0o170000
            if file_type == stat.S_IFLNK:
                raise RuntimeError(f"refusing to extract symlink from FFmpeg archive: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)

    @staticmethod
    def _safe_zip_target(base: Path, name: str) -> Path:
        normalized = str(name or "").replace("\\", "/")
        if not normalized or normalized.startswith("/") or ":" in normalized.split("/", 1)[0]:
            raise RuntimeError(f"unsafe path in FFmpeg archive: {name}")
        target = (base / normalized).resolve()
        try:
            target.relative_to(base)
        except ValueError as exc:
            raise RuntimeError(f"unsafe path in FFmpeg archive: {name}") from exc
        return target

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

    @staticmethod
    def _normalize_sha256(value: str) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
            raise ValueError("FFmpeg SHA-256 must be a 64-character hexadecimal value")
        return text
