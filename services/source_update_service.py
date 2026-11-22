"""Safe self-update support for source checkouts of Media Converter."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.constants import APP_VERSION

REPOSITORY_URL = "https://github.com/Sergiy-Galenko/mov_to_mp4_batch_gui.git"
RELEASE_API_URL = "https://api.github.com/repos/Sergiy-Galenko/mov_to_mp4_batch_gui/releases/latest"


@dataclass(frozen=True)
class SourceUpdateInfo:
    checked: bool = False
    available: bool = False
    restart_required: bool = False
    local_commit: str = ""
    remote_commit: str = ""
    message: str = ""
    package_url: str = ""
    downloaded_path: str = ""


class SourceUpdateService:
    """Checks and fast-forwards a clean checkout to the repository's main branch."""

    def __init__(
        self,
        project_root: Path | None = None,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        *,
        frozen: bool | None = None,
        version: str = APP_VERSION,
        fetch_release: Callable[[], dict] | None = None,
        download: Callable[[str, Path], None] | None = None,
    ) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parents[1]).resolve()
        self._run = run
        self._frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        self._version = version
        self._fetch_release = fetch_release or self._fetch_latest_release
        self._download = download or self._download_package

    def check(self) -> SourceUpdateInfo:
        if self._frozen:
            return self._check_packaged_release()
        if not (self.project_root / ".git").exists():
            return SourceUpdateInfo(checked=True, message="Для цієї копії немає автоматичного оновлення. Встановіть офіційний пакет застосунку або використайте Git-копію.")
        if not self._git_available():
            return SourceUpdateInfo(checked=True, message="Git не знайдено. Встановіть Git для перевірки оновлень.")

        fetch = self._git("fetch", "--quiet", REPOSITORY_URL, "main")
        if fetch.returncode != 0:
            return SourceUpdateInfo(checked=True, message=self._failure_message("Не вдалося отримати main", fetch))

        local = self._git_output("rev-parse", "HEAD")
        remote = self._git_output("rev-parse", "FETCH_HEAD")
        if not local or not remote:
            return SourceUpdateInfo(checked=True, message="Не вдалося визначити версію поточного коду.")
        if local == remote:
            return SourceUpdateInfo(checked=True, local_commit=local, remote_commit=remote, message="Установлено найновішу версію.")

        branch = self._git_output("branch", "--show-current")
        dirty = bool(self._git_output("status", "--porcelain"))
        if branch != "main":
            return SourceUpdateInfo(
                checked=True,
                local_commit=local,
                remote_commit=remote,
                message=f"Є нові зміни у main, але зараз активна гілка «{branch or 'detached'}». Перейдіть на main для оновлення.",
            )
        if dirty:
            return SourceUpdateInfo(
                checked=True,
                local_commit=local,
                remote_commit=remote,
                message="Є нові зміни у main. Спочатку закомітьте або сховайте локальні зміни.",
            )
        ancestor = self._git("merge-base", "--is-ancestor", "HEAD", "FETCH_HEAD")
        if ancestor.returncode != 0:
            return SourceUpdateInfo(
                checked=True,
                local_commit=local,
                remote_commit=remote,
                message="Локальна main має власні зміни. Автоматичне оновлення вимкнено, щоб не втратити код.",
            )
        return SourceUpdateInfo(
            checked=True,
            available=True,
            local_commit=local,
            remote_commit=remote,
            message=f"Доступне оновлення main: {local[:7]} → {remote[:7]}.",
        )

    def apply(self) -> SourceUpdateInfo:
        info = self.check()
        if not info.available:
            return info
        if self._frozen:
            if not info.package_url:
                return SourceUpdateInfo(checked=True, message="Не знайдено пакет для оновлення цієї платформи.")
            target = Path.home() / "Downloads" / Path(info.package_url.split("?", 1)[0]).name
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                self._download(info.package_url, target)
            except OSError as exc:
                return SourceUpdateInfo(checked=True, message=f"Не вдалося завантажити оновлення: {exc}")
            return SourceUpdateInfo(
                checked=True,
                local_commit=self._version,
                remote_commit=info.remote_commit,
                downloaded_path=str(target),
                message=f"Оновлення завантажено: {target.name}. Відкрийте файл і завершіть встановлення.",
            )
        merge = self._git("merge", "--ff-only", "FETCH_HEAD")
        if merge.returncode != 0:
            return SourceUpdateInfo(
                checked=True,
                local_commit=info.local_commit,
                remote_commit=info.remote_commit,
                message=self._failure_message("Не вдалося застосувати оновлення", merge),
            )
        return SourceUpdateInfo(
            checked=True,
            restart_required=True,
            local_commit=info.remote_commit,
            remote_commit=info.remote_commit,
            message="Оновлення завантажено. Перезапустіть застосунок, щоб застосувати нову версію.",
        )

    def _git_available(self) -> bool:
        return self._git("--version").returncode == 0

    def _git_output(self, *args: str) -> str:
        result = self._git(*args)
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self._run(
            ["git", *args],
            cwd=self.project_root,
            text=True,
            capture_output=True,
            timeout=25,
            check=False,
        )

    @staticmethod
    def _failure_message(prefix: str, result: subprocess.CompletedProcess[str]) -> str:
        detail = (result.stderr or result.stdout or "невідома помилка").strip().splitlines()[-1]
        return f"{prefix}: {detail}"

    def _check_packaged_release(self) -> SourceUpdateInfo:
        try:
            release = self._fetch_release()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return SourceUpdateInfo(checked=True, local_commit=self._version, message=f"Не вдалося перевірити реліз: {exc}")
        tag = str(release.get("tag_name") or "").strip()
        version = tag.lstrip("vV")
        if not version:
            return SourceUpdateInfo(checked=True, local_commit=self._version, message="GitHub не повернув номер останнього релізу.")
        if not self._is_newer(version, self._version):
            return SourceUpdateInfo(checked=True, local_commit=self._version, remote_commit=version, message="Установлено найновішу версію.")
        package_url = self._package_url(release.get("assets") or [])
        if not package_url:
            return SourceUpdateInfo(checked=True, local_commit=self._version, remote_commit=version, message=f"Доступний реліз {tag}, але пакет для цієї платформи ще не опубліковано.")
        return SourceUpdateInfo(
            checked=True,
            available=True,
            local_commit=self._version,
            remote_commit=version,
            package_url=package_url,
            message=f"Доступний реліз {tag}. Натисніть «Оновити», щоб завантажити інсталятор.",
        )

    def _package_url(self, assets: list[dict]) -> str:
        platform = "mac" if sys.platform == "darwin" else "win" if sys.platform == "win32" else "linux"
        extensions = (".dmg", ".pkg", ".zip") if platform == "mac" else (".exe", ".msi", ".zip") if platform == "win" else (".appimage", ".deb", ".tar.gz", ".zip")
        candidates = [asset for asset in assets if str(asset.get("name") or "").lower().endswith(extensions)]
        named = [asset for asset in candidates if platform in str(asset.get("name") or "").lower()]
        selected = (named or candidates or [{}])[0]
        return str(selected.get("browser_download_url") or "")

    @staticmethod
    def _is_newer(candidate: str, current: str) -> bool:
        def parts(value: str) -> tuple[int, ...]:
            return tuple(int(part) for part in value.split(".") if part.isdigit())
        return parts(candidate) > parts(current)

    @staticmethod
    def _fetch_latest_release() -> dict:
        request = urllib.request.Request(RELEASE_API_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "MediaConverter"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _download_package(url: str, target: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "MediaConverter"})
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
