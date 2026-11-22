"""Smoke checks that exercise shipped workflows on a real macOS runtime."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.paths import find_ffmpeg
from services.archive_service import ArchiveService
from services.source_update_service import SourceUpdateService

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS integration checks")


def test_macos_archive_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "Файл для перевірки.txt"
    source.write_text("Медіа Конвертер", encoding="utf-8")
    archive = tmp_path / "backup.zip"
    destination = tmp_path / "unpacked"
    service = ArchiveService()

    created = service.create_archive([str(source)], str(archive), archive_format="zip")
    extracted = service.extract_archive(str(archive), str(destination))

    assert created.success, created.error_message
    assert extracted.success, extracted.error_message
    assert (destination / source.name).read_text(encoding="utf-8") == "Медіа Конвертер"


def test_macos_ffmpeg_can_convert_a_short_audio_file(tmp_path: Path) -> None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        pytest.skip("FFmpeg is not installed; the application setup flow must install it first")
    source = tmp_path / "source.wav"
    result = tmp_path / "result.mp3"
    generated = subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono", "-t", "0.1", str(source)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    converted = subprocess.run(
        [ffmpeg, "-y", "-i", str(source), "-c:a", "mp3", str(result)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert generated.returncode == 0, generated.stderr[-1000:]
    assert converted.returncode == 0, converted.stderr[-1000:]
    assert result.exists() and result.stat().st_size > 0


def test_macos_packaged_update_downloads_a_release_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("services.source_update_service.Path.home", lambda: tmp_path)
    asset = "https://example.test/MediaConverter-mac.dmg"
    service = SourceUpdateService(
        tmp_path,
        frozen=True,
        version="2.0.0",
        fetch_release=lambda: {"tag_name": "v2.0.1", "assets": [{"name": "MediaConverter-mac.dmg", "browser_download_url": asset}]},
        download=lambda _url, target: target.write_bytes(b"installer"),
    )

    result = service.apply()

    assert Path(result.downloaded_path).exists()
