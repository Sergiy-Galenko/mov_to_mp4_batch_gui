import subprocess
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models import ConversionSettings, MediaInfo
from services import hardware_service
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from services.hardware_service import HardwareCapabilities, usable_videotoolbox_encoders


@pytest.mark.parametrize("codec,label,encoder,cpu,pixel_format", [
    ("h264", "H.264 (AVC)", "h264_videotoolbox", "libx264", "yuv420p"),
    ("h265", "H.265 (HEVC)", "hevc_videotoolbox", "libx265", "yuv420p"),
    ("prores", "ProRes", "prores_videotoolbox", "prores_ks", "ayuv64le"),
])
def test_videotoolbox_auto_selection_commands_merge_and_cpu_fallback(codec, label, encoder, cpu, pixel_format):
    ffmpeg = FfmpegService("ffmpeg", "ffprobe")
    ffmpeg.encoder_caps = {encoder, cpu}
    assert ffmpeg.select_encoder(codec, "auto") == (encoder, True)
    assert ffmpeg.select_encoder(codec, "apple") == (encoder, True)
    assert ffmpeg.select_encoder(codec, "cpu") == (cpu, False)
    settings = ConversionSettings(video_codec=label, hw_encoder="Apple (VideoToolbox)", out_video_format="mov")
    cmd = ffmpeg.build_video_command(Path("in.mov"), Path("out.mov"), settings, None, False)
    merge, listing = ffmpeg.build_merge_command([Path("a.mov"), Path("b.mov")], Path("out.mov"), settings, {}, False)
    try:
        for command in (cmd, merge):
            assert command[command.index("-c:v") + 1] == encoder
            assert command[command.index("-pix_fmt") + 1] == pixel_format
            assert command[command.index("-allow_sw") + 1] == "0"
            assert "-preset" not in command
            if codec == "h265":
                assert command[command.index("-tag:v") + 1] == "hvc1"
    finally:
        Path(listing).unlink(missing_ok=True)
    converter = ConverterService(ffmpeg, Queue())
    assert converter._has_gpu_encoder()
    fallback = converter._create_cpu_fallback_command(cmd)
    assert fallback[fallback.index("-c:v") + 1] == cpu
    assert "-allow_sw" not in fallback
    assert "-q:v" not in fallback
    if codec == "prores":
        assert "-crf" not in fallback
        assert fallback[fallback.index("-profile:v") + 1] == "3"
        assert fallback[fallback.index("-pix_fmt") + 1] == "yuv422p10le"
    else:
        assert fallback[fallback.index("-crf") + 1] == str(settings.crf)
    ffmpeg.encoder_caps = {cpu}
    assert ffmpeg.select_encoder(codec, "apple") == (cpu, False)


def test_videotoolbox_is_excluded_from_software_two_pass():
    ffmpeg = FfmpegService("ffmpeg", "ffprobe")
    converter = ConverterService(ffmpeg, Queue())
    settings = ConversionSettings(smart_two_pass=True, target_size_mb=5)
    assert not converter._can_use_two_pass(settings, ["ffmpeg", "-c:v", "h264_videotoolbox", "-b:v", "300k", "out.mp4"], False)
    assert HardwareCapabilities(apple_available=True).has_gpu


def test_prores_requires_compatible_container_and_ignores_target_bitrate():
    ffmpeg = FfmpegService("ffmpeg", "ffprobe")
    ffmpeg.encoder_caps = {"prores_videotoolbox"}
    with pytest.raises(ValueError, match="MOV or MKV"):
        ffmpeg.resolve_codec(".mp4", "ProRes")
    settings = ConversionSettings(video_codec="ProRes", target_size_mb=1)
    cmd = ffmpeg.build_video_command(Path("in.mp4"), Path("out.mov"), settings, MediaInfo(duration=10), False)
    assert "-b:v" not in cmd
    assert cmd[cmd.index("-profile:v") + 1] == "hq"


def test_runtime_probe_removes_unusable_prores_and_enforces_hardware(monkeypatch):
    monkeypatch.setattr(hardware_service.sys, "platform", "darwin")
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=1 if "prores_videotoolbox" in cmd else 0)

    monkeypatch.setattr(hardware_service.subprocess, "run", run)
    assert usable_videotoolbox_encoders("ffmpeg", {"h264_videotoolbox", "prores_videotoolbox", "libx264"}) == {"h264_videotoolbox", "libx264"}
    assert len(calls) == 2
    assert all(cmd[cmd.index("-allow_sw") + 1] == "0" for cmd in calls)


def test_runtime_probe_timeout_and_non_mac_do_not_claim_apple_hardware(monkeypatch):
    monkeypatch.setattr(hardware_service.sys, "platform", "darwin")
    run = Mock(side_effect=subprocess.TimeoutExpired("ffmpeg", 10))
    monkeypatch.setattr(hardware_service.subprocess, "run", run)
    assert usable_videotoolbox_encoders("ffmpeg", {"h264_videotoolbox", "libx264"}) == {"libx264"}
    monkeypatch.setattr(hardware_service.sys, "platform", "linux")
    run.reset_mock()
    assert usable_videotoolbox_encoders("ffmpeg", {"h264_videotoolbox"}) == set()
    run.assert_not_called()
