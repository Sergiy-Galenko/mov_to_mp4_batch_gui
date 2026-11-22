import queue
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models import ConversionSettings, MediaInfo
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from services.preset_manager import PresetManager


def test_custom_presets_roundtrip_and_invalid_import(tmp_path):
    manager = PresetManager(tmp_path / "config" / "presets.json")
    manager.save("Personal", {"crf": 18})
    manager.save("Personal", {"crf": 20})
    exported = tmp_path / "export.json"
    manager.export_json(exported)
    other = PresetManager(tmp_path / "other.json")
    other.import_json(exported)
    assert other.get("Personal") == {"crf": 20}
    assert other.delete("Personal")
    assert PresetManager(other.path).get("Personal") is None
    exported.write_text('{"Broken": 42}')
    with pytest.raises(ValueError):
        other.import_json(exported)
    assert "Broken" not in other.names()


def test_target_bitrate_accounts_for_trim_speed_audio():
    ffmpeg = FfmpegService("ffmpeg", None)
    settings = ConversionSettings(target_size_mb=8, trim_start=10, trim_end=50, speed=2, audio_bitrate="128k")
    info = MediaInfo(duration=60, audio_streams=1)
    assert ffmpeg.target_video_bitrate_kbps(settings, info) == int(8 * 8000 * 0.94 / 20 - 128)
    settings.remove_audio = True
    assert ffmpeg.target_video_bitrate_kbps(settings, info) == int(8 * 8000 * 0.94 / 20)
    settings.target_size_mb = 0.01
    with pytest.raises(ValueError, match="Мінімально розумне"):
        ffmpeg.target_video_bitrate_kbps(settings, info)


def test_target_forces_encoding_and_two_pass_cleanup_on_exception(tmp_path):
    ffmpeg = FfmpegService("ffmpeg", None)
    ffmpeg.encoder_caps = {"libx264", "h264_videotoolbox"}
    settings = ConversionSettings(target_size_mb=8, fast_copy=True, smart_two_pass=False)
    cmd = ffmpeg.build_video_command(tmp_path / "in.mov", tmp_path / "out.mp4", settings, MediaInfo(duration=30, audio_streams=1), True)
    assert cmd[cmd.index("-c:v") + 1] == "libx264"
    assert "-b:v" in cmd and "-crf" not in cmd
    service = ConverterService(ffmpeg, queue.Queue())
    logs = []

    def fail(command, *args, **kwargs):
        prefix = Path(command[command.index("-passlogfile") + 1])
        log = prefix.with_name(prefix.name + "-0.log")
        log.write_text("stats")
        logs.append(log)
        raise RuntimeError("cancelled")

    with patch.object(service, "_run_ffmpeg", side_effect=fail), pytest.raises(RuntimeError):
        service._run_video_command(cmd, tmp_path / "out.mp4", settings, 30, 0, 30, 0, 1, 0, True)
    assert logs and not logs[0].exists()


def test_target_runs_both_passes_without_smart_flag(tmp_path):
    ffmpeg = FfmpegService("ffmpeg", None)
    service = ConverterService(ffmpeg, queue.Queue())
    cmd = ["ffmpeg", "-c:v", "libx264", "-b:v", "1000k", str(tmp_path / "out.mp4")]
    with patch.object(service, "_run_ffmpeg", return_value=0) as run:
        assert service._run_video_command(cmd, tmp_path / "out.mp4", ConversionSettings(target_size_mb=8), 30, 0, 30, 0, 1, 0, False) == 0
    assert [call.args[0][call.args[0].index("-pass") + 1] for call in run.call_args_list] == ["1", "2"]
    assert run.call_args_list[0].kwargs["publish_output"] is False


def test_validation_warns_with_minimum_and_rejects_invalid_sizes(tmp_path):
    from app.models import TaskItem
    from services.validation_service import ValidationService

    service = ValidationService(FfmpegService("ffmpeg", None))
    source = tmp_path / "in.mp4"
    source.write_bytes(b"video")
    warnings, errors = [], {}
    service._validate_media_compatibility(
        [TaskItem(path=source, media_type="video", probe_data=MediaInfo(duration=600, audio_streams=1))],
        {"target_size_mb": "0.1"},
        {},
        errors.setdefault,
        warnings.append,
    )
    assert "target_size_mb" in errors
    assert any("мінімально розумне" in warning for warning in warnings)
    for value in ("nan", "inf", "-1", "zero"):
        errors = {}
        service._validate_fields({"target_size_mb": value}, errors.setdefault)
        assert "target_size_mb" in errors


def test_preflight_rejects_prores_and_incompatible_task_overrides(tmp_path):
    from app.models import TaskItem
    from services.validation_service import ValidationService

    ffmpeg = FfmpegService("ffmpeg", None)
    service = ValidationService(ffmpeg)
    result = service.validate(
        {"target_size_mb": 8, "codec": "ProRes", "out_video_fmt": "mov"},
        tasks=[],
        output_dir="",
        ffmpeg_path="",
        include_queue=False,
        require_output_dir=False,
    )
    assert "ProRes" in result["errors"]["target_size_mb"]
    source = TaskItem(
        path=tmp_path / "in.mp4",
        media_type="video",
        overrides={"codec": "H.265 (HEVC)"},
        probe_data=MediaInfo(duration=30, audio_streams=1),
    )
    errors = {}
    service._validate_media_compatibility([source], {"target_size_mb": 8}, {}, errors.setdefault, lambda _: None)
    assert "H.265" in errors["target_size_mb"]
