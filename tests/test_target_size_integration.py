"""Exercise the actual two-pass encoder, size guard and cancellation cleanup."""

import os
import queue
import shutil
import subprocess
import time

import pytest

from app.models import ConversionSettings, MediaInfo
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService


@pytest.fixture
def ffmpeg_binary():
    binary = os.environ.get("MEDIA_CONVERTER_TEST_FFMPEG") or shutil.which("ffmpeg")
    if not binary:
        if os.environ.get("MEDIA_CONVERTER_REQUIRE_FFMPEG_TESTS") == "1":
            pytest.fail("Real FFmpeg is required by this CI job")
        pytest.skip("FFmpeg integration tests need MEDIA_CONVERTER_TEST_FFMPEG or FFmpeg in PATH")
    return binary


@pytest.fixture
def source(ffmpeg_binary, tmp_path):
    path = tmp_path / "source.mp4"
    subprocess.run(
        [
            ffmpeg_binary,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "5",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ],
        check=True,
        timeout=45,
        capture_output=True,
    )
    return path


@pytest.mark.parametrize("force_oversize", [False, True])
def test_real_two_pass_output_respects_decimal_budget(ffmpeg_binary, source, tmp_path, force_oversize):
    ffmpeg = FfmpegService(ffmpeg_binary, None)
    settings = ConversionSettings(target_size_mb=0.2, audio_bitrate="64k", preset="fast")
    output = tmp_path / "result.mp4"
    cmd = ffmpeg.build_video_command(source, output, settings, MediaInfo(duration=5, audio_streams=1), False)
    if force_oversize:
        for flag, value in (("-b:v", "6000k"), ("-maxrate", "8100k"), ("-bufsize", "12000k")):
            cmd[cmd.index(flag) + 1] = value
    events = queue.Queue()
    runner = ConverterService(ffmpeg, events)
    assert runner._run_video_command(cmd, output, settings, 5, 0, 5, 0, 1, time.time(), False) == 0
    assert 0 < output.stat().st_size <= 200_000
    assert not list(tmp_path.glob("*.partial*"))
    subprocess.run([ffmpeg_binary, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, capture_output=True, timeout=30)
    recorded = list(events.queue)
    progress = [event[1] for event in recorded if event[0] == "progress" and event[1] is not None]
    assert progress == sorted(progress)
    assert progress[-1] == 1.0
    assert any("Прохід 1/2" in str(event) for event in recorded)
    assert any("Прохід 2/2" in str(event) for event in recorded)
    if force_oversize:
        assert any("перевищує ліміт" in str(event) for event in recorded)


def test_oversized_temporary_output_preserves_existing_result(ffmpeg_binary, source, tmp_path):
    output = tmp_path / "existing.mp4"
    output.write_bytes(b"previous result")
    runner = ConverterService(FfmpegService(ffmpeg_binary, None), queue.Queue())
    rc = runner._run_ffmpeg(
        [ffmpeg_binary, "-y", "-i", str(source), "-c", "copy", str(output)], 5, 0, 5, 0, 1, time.time(), size_limit_bytes=1
    )
    assert rc == runner.OVERSIZE_RC
    assert output.read_bytes() == b"previous result"
    assert not list(tmp_path.glob(".*.partial*"))


def test_trim_and_speed_are_applied_before_target_duration(ffmpeg_binary, source, tmp_path):
    ffmpeg = FfmpegService(ffmpeg_binary, None)
    settings = ConversionSettings(target_size_mb=0.1, audio_bitrate="64k", preset="fast", trim_start=1, trim_end=3, speed=2)
    output = tmp_path / "trimmed.mp4"
    cmd = ffmpeg.build_video_command(source, output, settings, MediaInfo(duration=5, audio_streams=1), False)
    assert cmd.index("-ss") < cmd.index("-i")
    runner = ConverterService(ffmpeg, queue.Queue())
    assert runner._run_video_command(cmd, output, settings, 5, 0, 5, 0, 1, time.time(), False) == 0
    assert output.stat().st_size <= 100_000
    checked = subprocess.run(
        [ffmpeg_binary, "-v", "error", "-i", str(output), "-progress", "pipe:1", "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    last_time = [line for line in checked.stdout.splitlines() if line.startswith("out_time_us=")][-1]
    assert float(last_time.split("=")[1]) / 1_000_000 == pytest.approx(1.0, abs=0.15)
