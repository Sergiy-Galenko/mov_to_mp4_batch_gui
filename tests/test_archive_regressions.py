from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from services.archive_service import ArchiveService
from services.queue_manager import QueueManager


def test_cancel_preserves_existing_archive_and_backups(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("input")
    output = tmp_path / "archive.zip"
    backup = tmp_path / "archive.zip.backup"
    output.write_bytes(b"old archive")
    backup.write_bytes(b"old backup")
    result = ArchiveService().create_archive([str(source)], str(output), cancel_requested=lambda: True)
    assert not result.success
    assert output.read_bytes() == b"old archive"
    assert backup.read_bytes() == b"old backup"
    assert not list(tmp_path.glob(".archive-*"))


def test_success_replaces_archive_without_modifying_backup(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("input")
    output = tmp_path / "archive.zip"
    output.write_bytes(b"old")
    backup = tmp_path / "archive.zip.backup"
    backup.write_bytes(b"backup")
    result = ArchiveService().create_archive([str(source)], str(output))
    assert result.success
    assert result.output_paths == [str(output)]
    assert output.read_bytes().startswith(b"PK")
    assert backup.read_bytes() == b"backup"


@pytest.mark.parametrize(
    "archive_format,names",
    [
        ("7z", ["archive.7z.001", "archive.7z.002"]),
        ("rar", ["archive.part1.rar", "archive.part2.rar"]),
    ],
)
def test_split_archive_reports_all_volumes_and_total_size(tmp_path, archive_format, names):
    source = tmp_path / "input.txt"
    source.write_text("input")
    output = tmp_path / f"archive.{archive_format}"

    def encode(**kwargs):
        for name in names:
            (kwargs["output_path"].parent / name).write_bytes(b"volume")

    with (
        patch.object(ArchiveService, f"has_{archive_format}", new_callable=PropertyMock, return_value=True),
        patch.object(ArchiveService, f"_create_{archive_format}", side_effect=encode),
    ):
        result = ArchiveService().create_archive([str(source)], str(output), archive_format=archive_format, split_size_mb=1)
    assert result.success, result.error_message
    assert result.output_paths == [str(tmp_path / name) for name in names]
    assert result.output_path == result.output_paths[0]
    assert result.archive_size == 12
    assert all(Path(p).read_bytes() == b"volume" for p in result.output_paths)


def test_split_publication_failure_rolls_back_only_new_parts(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("input")
    existing = tmp_path / "archive.7z.002"
    existing.write_bytes(b"old volume")

    def encode(**kwargs):
        for suffix in ("001", "002"):
            (kwargs["output_path"].parent / f"archive.7z.{suffix}").write_bytes(b"new")

    with (
        patch.object(ArchiveService, "has_7z", new_callable=PropertyMock, return_value=True),
        patch.object(ArchiveService, "_create_7z", side_effect=encode),
    ):
        result = ArchiveService().create_archive([str(source)], str(tmp_path / "archive.7z"), archive_format="7z", split_size_mb=1)
    assert not result.success
    assert existing.read_bytes() == b"old volume"
    assert not (tmp_path / "archive.7z.001").exists()


@pytest.mark.parametrize(
    "bad_fields",
    [
        {"attempts": "invalid"},
        {"attempts": -1},
        {"progress": "nan"},
        {"progress": 101},
        {"elapsed_seconds": float("inf")},
        {"overrides": ["invalid"]},
        {"input_bytes": {}},
        {"exit_code": []},
    ],
)
def test_queue_skips_bad_record_and_keeps_valid_records(bad_fields):
    valid = {"path": "input.mp4", "media_type": "video"}
    result = QueueManager().deserialize_tasks([{**valid, **bad_fields}, valid])
    assert len(result) == 1
    assert result[0].path == Path("input.mp4")
