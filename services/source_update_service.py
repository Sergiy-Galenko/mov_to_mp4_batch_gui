"""Safe self-update support for source checkouts of Media Converter."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REPOSITORY_URL = "https://github.com/Sergiy-Galenko/mov_to_mp4_batch_gui.git"


@dataclass(frozen=True)
class SourceUpdateInfo:
    checked: bool = False
    available: bool = False
    restart_required: bool = False
    local_commit: str = ""
    remote_commit: str = ""
    message: str = ""


class SourceUpdateService:
    """Checks and fast-forwards a clean checkout to the repository's main branch."""

    def __init__(
        self,
        project_root: Path | None = None,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parents[1]).resolve()
        self._run = run

    def check(self) -> SourceUpdateInfo:
        if not (self.project_root / ".git").exists():
            return SourceUpdateInfo(checked=True, message="Оновлення доступні лише для Git-копії проєкту.")
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
