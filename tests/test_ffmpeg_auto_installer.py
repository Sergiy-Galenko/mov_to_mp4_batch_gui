import shutil
import zipfile
from pathlib import Path

from services.ffmpeg_auto_installer import FfmpegAutoInstaller


def _make_ffmpeg_zip(tmp_path: Path) -> Path:
    package_root = tmp_path / "package" / "ffmpeg-master-latest-win64-gpl"
    bin_dir = package_root / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "ffmpeg.exe").write_text("fake ffmpeg", encoding="utf-8")
    (bin_dir / "ffprobe.exe").write_text("fake ffprobe", encoding="utf-8")
    archive = tmp_path / "ffmpeg.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for file_path in package_root.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(tmp_path / "package"))
    return archive


def test_installer_downloads_and_installs_managed_ffmpeg(tmp_path: Path) -> None:
    archive = _make_ffmpeg_zip(tmp_path)
    progress_messages = []

    def fake_download(url, destination, progress_cb=None):
        if progress_cb:
            progress_cb("copying")
        shutil.copyfile(archive, destination)

    installer = FfmpegAutoInstaller(
        install_dir=tmp_path / "install",
        download_func=fake_download,
        now_func=lambda: 1000.0,
        platform_key="win64",
        expected_sha256=FfmpegAutoInstaller._sha256(archive),
    )

    result = installer.ensure("", force=True, progress_cb=progress_messages.append)

    assert result.status == "downloaded"
    assert result.changed is True
    assert Path(result.ffmpeg_path).exists()
    assert Path(result.ffprobe_path).exists()
    assert installer.find_managed_ffmpeg() == result.ffmpeg_path
    assert "copying" in progress_messages
    assert installer.should_run(result.ffmpeg_path) is False


def test_installer_skips_external_ffmpeg(tmp_path: Path) -> None:
    external = tmp_path / "tools" / "ffmpeg.exe"
    external.parent.mkdir()
    external.write_text("external", encoding="utf-8")
    installer = FfmpegAutoInstaller(install_dir=tmp_path / "install", platform_key="win64")

    result = installer.ensure(str(external))

    assert result.status == "external"
    assert result.changed is False
    assert result.ffmpeg_path == str(external)


def test_installer_detects_due_managed_update(tmp_path: Path) -> None:
    archive = _make_ffmpeg_zip(tmp_path)

    def fake_download(url, destination, progress_cb=None):
        shutil.copyfile(archive, destination)

    installer = FfmpegAutoInstaller(
        install_dir=tmp_path / "install",
        download_func=fake_download,
        now_func=lambda: 1000.0,
        platform_key="win64",
        check_interval_sec=3600,
        expected_sha256=FfmpegAutoInstaller._sha256(archive),
    )
    result = installer.ensure("", force=True)

    fresh = FfmpegAutoInstaller(
        install_dir=tmp_path / "install",
        download_func=fake_download,
        now_func=lambda: 2000.0,
        platform_key="win64",
        check_interval_sec=3600,
        expected_sha256=FfmpegAutoInstaller._sha256(archive),
    )
    stale = FfmpegAutoInstaller(
        install_dir=tmp_path / "install",
        download_func=fake_download,
        now_func=lambda: 5000.0,
        platform_key="win64",
        check_interval_sec=3600,
        expected_sha256=FfmpegAutoInstaller._sha256(archive),
    )

    assert fresh.should_run(result.ffmpeg_path) is False
    assert stale.should_run(result.ffmpeg_path) is True


def test_installer_blocks_unpinned_ffmpeg_download(tmp_path: Path) -> None:
    calls = []

    def fake_download(url, destination, progress_cb=None):
        calls.append(url)

    installer = FfmpegAutoInstaller(
        install_dir=tmp_path / "install",
        download_func=fake_download,
        platform_key="win64",
    )

    result = installer.ensure("", force=True)

    assert result.status == "error"
    assert "SHA-256" in result.message
    assert calls == []


def test_installer_rejects_zip_slip_members(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../evil.txt", "owned")
        zf.writestr("ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe", "fake")

    def fake_download(url, destination, progress_cb=None):
        shutil.copyfile(archive, destination)

    installer = FfmpegAutoInstaller(
        install_dir=tmp_path / "install",
        download_func=fake_download,
        platform_key="win64",
        expected_sha256=FfmpegAutoInstaller._sha256(archive),
    )

    result = installer.ensure("", force=True)

    assert result.status == "error"
    assert "unsafe path" in result.message
    assert not (tmp_path / "evil.txt").exists()
