import io
import os
import subprocess
import threading
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from app.models import ConversionSettings, MediaInfo, TaskItem
from services.adaptive_scheduler import MIB, AdaptiveScheduler, TaskCost, bound_ffmpeg_threads
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from services.frame_stream import MAX_FRAME_BYTES, read_ppm_frame, sample_frames
from services.hardware_service import discover_encoders
from services.resource_monitor import ResourceMonitor


class Monitor:
    def __init__(self, **sample):
        self.values = {"cpu": 0.0, "gpu": None, "available_bytes": None, **sample}

    def sample(self):
        return dict(self.values)


def scheduler(**kwargs):
    return AdaptiveScheduler(4, Monitor(), cpu_threads=8, memory_bytes=1024 * MIB, **kwargs)


@pytest.mark.parametrize("cost", [TaskCost(8, 128 * MIB), TaskCost(1, 1024 * MIB), TaskCost(1, 128 * MIB, 2), TaskCost(1, 128 * MIB, 0, 2)])
def test_reservations_exclude_over_budget_work_until_release(cost):
    service = scheduler()
    stop, pause = threading.Event(), threading.Event()
    attempted, admitted = threading.Event(), threading.Event()
    settings = ConversionSettings()

    def worker():
        attempted.set()
        with service.reserve(cost, settings, stop, pause) as acquired:
            if acquired:
                admitted.set()

    with service.reserve(cost, settings, stop, pause) as acquired:
        assert acquired
        thread = threading.Thread(target=worker)
        thread.start()
        assert attempted.wait(1)
        assert not admitted.wait(0.15)
    thread.join(2)
    assert not thread.is_alive()
    assert admitted.is_set()
    assert service._active == 0


def test_pause_and_cancellation_never_acquire_or_leak_reservations():
    service = scheduler()
    stop, pause = threading.Event(), threading.Event()
    pause.set()
    result = []

    def worker():
        with service.reserve(TaskCost(1, MIB), ConversionSettings(), stop, pause) as acquired:
            result.append(acquired)

    thread = threading.Thread(target=worker)
    thread.start()
    stop.set()
    thread.join(2)
    assert result == [False]
    assert service._active == 0


def test_exception_releases_budget_and_unknown_gpu_does_not_block():
    service = scheduler()
    with (
        pytest.raises(RuntimeError, match="failed"),
        service.reserve(TaskCost(8, 1024 * MIB, 2, 2), ConversionSettings(), threading.Event(), threading.Event()) as admitted,
    ):
        assert admitted
        raise RuntimeError("failed")
    with service.reserve(TaskCost(8, 1024 * MIB, 2, 2), ConversionSettings(), threading.Event(), threading.Event()) as admitted:
        assert admitted


def test_load_and_live_memory_restrict_admission():
    service = scheduler()
    settings = ConversionSettings(cpu_load_limit=80, gpu_load_limit=80)
    cost = TaskCost(1, 512 * MIB, 1)
    service.monitor.values["cpu"] = 90
    assert not service._fits(cost, settings)
    service.monitor.values.update(cpu=10, gpu=90)
    assert not service._fits(cost, settings)
    service.monitor.values.update(gpu=None, available_bytes=600 * MIB)
    assert not service._fits(cost, settings)
    service.monitor.values["available_bytes"] = 2048 * MIB
    assert service._fits(cost, settings)


def test_estimates_distinguish_thumbnail_4k_and_transcription():
    service = AdaptiveScheduler(4, Monitor(), cpu_threads=8, memory_bytes=8 * 1024 * MIB)
    ffmpeg = FfmpegService("ffmpeg", None)
    ffmpeg.encoder_caps = {"h264_nvenc"}
    task = TaskItem(Path("clip.mov"), "video")
    info = MediaInfo(width=3840, height=2160)
    video = service.estimate(task, ConversionSettings(), info, ffmpeg)
    thumbnail = service.estimate(task, ConversionSettings(operation="thumbnail"), info, ffmpeg)
    speech = service.estimate(task, ConversionSettings(operation="auto_subtitle", subtitle_model="medium"), info, ffmpeg)
    assert video.memory_bytes > thumbnail.memory_bytes
    assert video.hardware_sessions == 1
    assert thumbnail.cpu_threads == 1 and thumbnail.hardware_sessions == 0
    assert speech.memory_bytes > video.memory_bytes


@pytest.mark.parametrize("encoder,option", [("libx265", "-x265-params"), ("libsvtav1", "-svtav1-params")])
def test_thread_budget_bounds_every_decoder_and_private_encoder_pool(encoder, option):
    command = ["ffmpeg", "-y", "-i", "a.mp4", "-i", "b.wav", "-c:v", encoder, "out.mp4"]
    bounded = bound_ffmpeg_threads(command, 2)
    assert command[-1] == bounded[-1]
    assert bounded.count("-threads") == 3
    assert all(bounded[i + 1] == "2" for i, value in enumerate(bounded) if value == "-threads")
    assert option in bounded


def test_hardware_listing_does_not_claim_an_unusable_driver(monkeypatch):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if "-encoders" in command:
            return SimpleNamespace(returncode=0, stdout=" V....D libx264\n V....D h264_nvenc\n V....D h264_qsv", stderr="")
        return SimpleNamespace(returncode=0 if "h264_qsv" in command else 1, stdout="", stderr="driver unavailable")

    assert discover_encoders("ffmpeg", run=run) == {"libx264", "h264_qsv"}
    assert len(commands) == 3


def test_gpu_without_telemetry_remains_unknown(monkeypatch):
    monkeypatch.setattr("services.resource_monitor.shutil.which", lambda name: None)
    monitor = ResourceMonitor()
    monitor._collect()
    assert monitor._sample["gpu"] is None


@pytest.mark.parametrize("codec", ["pcm_s16le", "flac", "vorbis"])
def test_mov_to_mp4_copies_video_but_encodes_incompatible_audio(codec):
    ffmpeg = FfmpegService("ffmpeg", None)
    command = ffmpeg.build_video_command(
        Path("in.mov"), Path("out.mp4"), ConversionSettings(fast_copy=True), MediaInfo(vcodec="h264", acodec=codec, audio_streams=1), False
    )
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[command.index("-c:a") + 1] == "aac"


def test_copy_never_bypasses_video_filters_or_missing_probe():
    ffmpeg = FfmpegService("ffmpeg", None)
    for settings, info in [
        (ConversionSettings(fast_copy=True, resize_w=640), MediaInfo(vcodec="h264")),
        (ConversionSettings(fast_copy=True), None),
    ]:
        command = ffmpeg.build_video_command(Path("in.mov"), Path("out.mp4"), settings, info, True)
        assert command[command.index("-c:v") + 1] != "copy"


def test_audio_filter_preserves_video_copy_and_encodes_audio():
    ffmpeg = FfmpegService("ffmpeg", None)
    settings = ConversionSettings(fast_copy=True)
    ffmpeg.build_audio_filter = Mock(return_value="volume=0.5")
    command = ffmpeg.build_video_command(Path("in.mov"), Path("out.mp4"), settings, MediaInfo(vcodec="h264", acodec="aac"), False)
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[command.index("-c:a") + 1] == "aac"
    assert command[command.index("-filter:a") + 1] == "volume=0.5"


def test_ppm_reader_handles_concatenated_frames_and_rejects_truncation():
    frame = b"P6\n2 1\n255\n" + b"\xff\x00\x00\x00\xff\x00"
    stream = io.BytesIO(frame * 2)
    assert read_ppm_frame(stream).getpixel((0, 0)) == (255, 0, 0)
    assert read_ppm_frame(stream).size == (2, 1)
    assert read_ppm_frame(stream) is None
    with pytest.raises(RuntimeError, match="Truncated"):
        read_ppm_frame(io.BytesIO(frame[:-1]))
    with pytest.raises(RuntimeError, match="memory limit"):
        read_ppm_frame(io.BytesIO(f"P6\n{MAX_FRAME_BYTES} 2\n255\n".encode()))


def test_reframe_consumes_frames_in_memory(monkeypatch):
    from services import smart_reframe_service

    service = smart_reframe_service.SmartReframeService()
    monkeypatch.setattr(service, "probe_dimensions", lambda path: (1920, 1080, 2))
    monkeypatch.setattr(
        smart_reframe_service,
        "sample_frames",
        lambda *a, **kw: iter([(0, Image.new("RGB", (320, 180))), (1, Image.new("RGB", (320, 180)))]),
    )
    seen = []

    def detect(frame):
        assert isinstance(frame, Image.Image)
        seen.append(frame)
        return 0.8

    monkeypatch.setattr(service, "_detect_subject_center", detect)
    result = service.analyze_reframe("in.mov")
    assert len(seen) == len(result.keyframes) == 2
    assert result.keyframes[1].center_x > result.keyframes[0].center_x > 0.5


def test_real_ffmpeg_pipe_and_mixed_stream_copy(tmp_path):
    executable = os.environ.get("MEDIA_CONVERTER_TEST_FFMPEG")
    if not executable:
        pytest.skip("Set MEDIA_CONVERTER_TEST_FFMPEG to exercise real FFmpeg")
    source = tmp_path / "source.mov"
    output = tmp_path / "output.mp4"
    subprocess.run(
        [
            executable,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x48:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-c:a",
            "pcm_s16le",
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    frames = list(sample_frames(executable, source, 0.5, width=32))
    assert len(frames) == 4
    assert frames[0][1].size == (32, 24)
    ffmpeg = FfmpegService(executable, None)
    command = ffmpeg.build_video_command(
        source,
        output,
        ConversionSettings(fast_copy=True, overwrite=True),
        MediaInfo(vcodec="h264", acodec="pcm_s16le", audio_streams=1),
        False,
    )
    subprocess.run(bound_ffmpeg_threads(command, 2), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert output.stat().st_size > 0
    subprocess.run([executable, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, stderr=subprocess.PIPE)
    # Closing a partially consumed generator must kill/reap the producer too.
    stream = sample_frames(executable, source, 0.1)
    next(stream)
    stream.close()
    # Exercise the actual converter/worker/thread-budget path, not just command building.
    second = tmp_path / "second.mov"
    second.write_bytes(source.read_bytes())
    out_dir = tmp_path / "batch"
    out_dir.mkdir()
    events = Queue()
    converter = ConverterService(ffmpeg, events)
    converter.resource_monitor = Monitor(available_bytes=8 * 1024 * MIB)
    ffmpeg.encoder_caps = {"libx264"}
    converter._run([TaskItem(source, "video"), TaskItem(second, "video")], ConversionSettings(concurrency_limit=2, overwrite=True), out_dir)
    summaries = [event[1] for event in list(events.queue) if event[0] == "run_summary"]
    assert summaries and len(summaries[-1]["results"]) == 2
    assert {result["status"] for result in summaries[-1]["results"]} == {"success"}
    assert (out_dir / "source.mp4").exists()
    assert (out_dir / "second.mp4").exists()
    assert not list(out_dir.glob("*.partial*"))


def test_frame_watchdog_cancels_a_blocked_producer(monkeypatch):
    cancel, blocked, killed = threading.Event(), threading.Event(), threading.Event()

    class Pipe:
        def readline(self, limit):
            blocked.set()
            assert killed.wait(2)
            return b""

        def close(self):
            pass

    class Producer:
        stdout = Pipe()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def poll(self):
            return 1 if killed.is_set() else None

        def kill(self):
            killed.set()

        def wait(self, timeout=None):
            return 1

    monkeypatch.setattr("services.frame_stream.subprocess.Popen", lambda *a, **kw: Producer())
    result = []
    thread = threading.Thread(target=lambda: result.extend(sample_frames("ffmpeg", Path("in.mov"), 1, cancel=cancel)))
    thread.start()
    assert blocked.wait(1)
    cancel.set()
    thread.join(2)
    assert not thread.is_alive()
    assert killed.is_set()
    assert result == []


@pytest.mark.parametrize("interval", [0, -1, float("nan"), float("inf")])
def test_frame_interval_is_validated_before_launch(interval, monkeypatch):
    launch = Mock()
    monkeypatch.setattr("services.frame_stream.subprocess.Popen", launch)
    with pytest.raises(ValueError, match="interval"):
        next(sample_frames("ffmpeg", Path("in.mov"), interval))
    launch.assert_not_called()


def test_audio_replacement_can_preserve_compatible_video(tmp_path):
    replacement = tmp_path / "sound.wav"
    replacement.write_bytes(b"placeholder")
    ffmpeg = FfmpegService("ffmpeg", None)
    command = ffmpeg.build_video_command(
        Path("in.mov"),
        Path("out.mp4"),
        ConversionSettings(fast_copy=True, replace_audio_path=str(replacement)),
        MediaInfo(vcodec="h264", acodec="aac"),
        False,
    )
    assert command[command.index("-c:v") + 1] == "copy"
    assert "1:a:0?" in command
    assert "-shortest" in command
    assert command[command.index("-c:a") + 1] == "aac"
