import hashlib
import json
import os
import shutil
import subprocess
from queue import Queue
from unittest.mock import Mock

import pytest

from app.models import ConversionSettings, TaskItem
from app.preset_schema import validate_settings
from app.settings import settings_map_to_model
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from services.preview_builder import PreviewBuilder
from services.validation_service import ValidationService
from utils.files import format_output_paths, parse_output_paths


def test_output_paths_with_semicolons_and_legacy_chapter_lists(tmp_path):
    files = [tmp_path / "one; first.mp3", tmp_path / "two;last.mp3"]
    for path in files:
        path.touch()
    assert parse_output_paths(str(files[0])) == files[:1]
    assert parse_output_paths(format_output_paths(list(map(str, files)))) == files
    assert parse_output_paths("; ".join(map(str, files))) == files


def test_merge_stop_and_skip_agree_with_preflight_and_report(tmp_path):
    inputs = [TaskItem(tmp_path / name, "video") for name in ["a.mp4", "b.mp4"]]
    for item in inputs:
        item.path.touch()
    out = tmp_path / "merged.mp3"
    out.write_bytes(b"existing")
    raw = {"operation": "audio_only", "merge": True, "output_collision_policy": "stop"}
    ffmpeg = FfmpegService("ffmpeg", None)
    preview = PreviewBuilder(ffmpeg).build(raw, tasks=inputs, output_dir=str(tmp_path))
    assert all(row.output_path == out for row in preview.items)
    result = ValidationService(ffmpeg).validate(raw, tasks=inputs, output_dir=str(tmp_path), ffmpeg_path="ffmpeg")
    assert "merge_name" in result["errors"]
    for policy, expected in [("stop", "failed"), ("skip", "skipped")]:
        raw["output_collision_policy"] = policy
        converter = ConverterService(ffmpeg, Queue())
        converter._run(inputs, settings_map_to_model(raw), tmp_path)
        summary = next(event[1] for event in converter.queue.queue if event[0] == "run_summary")
        assert [r["status"] for r in summary["results"]] == [expected, expected]
    assert out.read_bytes() == b"existing"
    assert list(tmp_path.glob("*.mp3")) == [out]


def test_real_merges_apply_postprocessing_once_and_use_requested_streams(tmp_path):
    ffmpeg = os.environ.get("MEDIA_CONVERTER_TEST_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("MEDIA_CONVERTER_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg and FFprobe are required for the merge integration test")
    inputs = [TaskItem(tmp_path / name, "video") for name in ["a.mp4", "b.mp4"]]
    subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=s=64x64:r=10:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(inputs[0].path),
        ],
        check=True,
        timeout=30,
    )
    shutil.copyfile(inputs[0].path, inputs[1].path)
    service = FfmpegService(ffmpeg, ffprobe)
    extra = validate_settings({"checksum_algorithm": "sha512", "smart_quality_metric": "psnr"})
    for operation, extension in [("convert", "mp4"), ("audio_only", "mp3")]:
        out = tmp_path / f"joined; final.{extension}"
        converter = ConverterService(service, Queue())
        converter.cloud_uploader.upload = Mock()
        settings = settings_map_to_model(
            {
                **extra,
                "operation": operation,
                "merge": True,
                "merge_name": "joined; final",
                "smart_integrity_check": True,
                "cloud_upload_enabled": True,
                "out_audio_fmt": "mp3",
                "fast_copy": True,
                "secure_delete_original": operation == "audio_only",
            },
            defaults=ConversionSettings(),
        )
        converter._run(inputs, settings, tmp_path)
        logs = [e[2] for e in converter.queue.queue if e[0] == "log"]
        summary = next(e[1] for e in converter.queue.queue if e[0] == "run_summary")
        assert [row["status"] for row in summary["results"]] == ["success", "success"], logs
        converter.cloud_uploader.upload.assert_called_once()
        assert converter.cloud_uploader.upload.call_args.args[0] == out
        assert any("Integrity check OK" in message for message in logs)
        assert out.with_suffix(out.suffix + ".sha512").read_text().split()[0] == hashlib.sha512(out.read_bytes()).hexdigest()
        data = json.loads(
            subprocess.check_output(
                [ffprobe, "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(out)],
                timeout=30,
            )
        )
        stream_types = [stream["codec_type"] for stream in data["streams"]]
        if operation == "convert":
            assert stream_types == ["video", "audio"]
            assert any("PSNR:" in message for message in logs), logs
        else:
            assert stream_types == ["audio"]
            assert all(not task.path.exists() for task in inputs)
            assert all(task.status == "success" for task in converter.journal.recover_items(inputs))
        assert 1.9 < float(data["format"]["duration"]) < 2.3
