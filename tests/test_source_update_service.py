from __future__ import annotations

import subprocess
from pathlib import Path

from services.source_update_service import SourceUpdateService


class FakeGit:
    def __init__(self, *, branch: str = "main", dirty: bool = False, merge_ok: bool = True) -> None:
        self.branch = branch
        self.dirty = dirty
        self.merge_ok = merge_ok
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, command, **_kwargs):
        args = tuple(command[1:])
        self.calls.append(args)
        stdout = ""
        returncode = 0
        if args == ("rev-parse", "HEAD"):
            stdout = "1111111local\n"
        elif args == ("rev-parse", "FETCH_HEAD"):
            stdout = "2222222remote\n"
        elif args == ("branch", "--show-current"):
            stdout = self.branch + "\n"
        elif args == ("status", "--porcelain"):
            stdout = " M ui/qml/Main.qml\n" if self.dirty else ""
        elif args == ("merge-base", "--is-ancestor", "HEAD", "FETCH_HEAD"):
            returncode = 0 if self.merge_ok else 1
        return subprocess.CompletedProcess(command, returncode, stdout, "")


def service_for(tmp_path: Path, fake_git: FakeGit) -> SourceUpdateService:
    (tmp_path / ".git").mkdir()
    return SourceUpdateService(tmp_path, run=fake_git)


def test_check_offers_fast_forward_update_on_clean_main(tmp_path):
    fake_git = FakeGit()
    info = service_for(tmp_path, fake_git).check()

    assert info.available is True
    assert info.local_commit == "1111111local"
    assert info.remote_commit == "2222222remote"
    assert ("fetch", "--quiet", "https://github.com/Sergiy-Galenko/mov_to_mp4_batch_gui.git", "main") in fake_git.calls


def test_check_refuses_update_when_worktree_is_dirty(tmp_path):
    info = service_for(tmp_path, FakeGit(dirty=True)).check()

    assert info.available is False
    assert "локальні зміни" in info.message.lower()


def test_check_refuses_update_outside_main(tmp_path):
    info = service_for(tmp_path, FakeGit(branch="feature/new-ui")).check()

    assert info.available is False
    assert "активна гілка" in info.message.lower()


def test_apply_fast_forwards_and_requires_restart(tmp_path):
    fake_git = FakeGit()
    info = service_for(tmp_path, fake_git).apply()

    assert info.restart_required is True
    assert ("merge", "--ff-only", "FETCH_HEAD") in fake_git.calls


def test_packaged_app_downloads_the_platform_release(tmp_path, monkeypatch):
    monkeypatch.setattr("services.source_update_service.Path.home", lambda: tmp_path)
    release = {
        "tag_name": "v2.1.0",
        "assets": [{"name": "MediaConverter-mac.dmg", "browser_download_url": "https://example.test/MediaConverter-mac.dmg"}],
    }
    downloaded: list[tuple[str, Path]] = []

    def download(url: str, target: Path) -> None:
        downloaded.append((url, target))
        target.write_bytes(b"installer")

    service = SourceUpdateService(tmp_path, frozen=True, version="2.0.0", fetch_release=lambda: release, download=download)
    available = service.check()
    result = service.apply()

    assert available.available is True
    assert available.package_url.endswith(".dmg")
    assert downloaded[0][0] == available.package_url
    assert Path(result.downloaded_path).read_bytes() == b"installer"
