import math
import os
import shutil
import struct
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.models import ConversionSettings, MediaInfo
from services.conversion_sample_service import create_sample
from services.ffmpeg_service import FfmpegService


def test_sample_rejects_whole_file_operations(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    ffmpeg = FfmpegService("ffmpeg", None)
    for settings in (ConversionSettings(merge=True), ConversionSettings(target_size_mb=8)):
        with pytest.raises(ValueError, match="цільовий розмір"):
            create_sample(ffmpeg, source, "video", settings, tmp_path / "samples")
    assert not (tmp_path / "samples").exists()


def test_failed_sample_cleans_partial_output(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.touch()
    ffmpeg = FfmpegService("ffmpeg", None)
    monkeypatch.setattr(ffmpeg, "probe_media", Mock(return_value=MediaInfo(duration=30, audio_streams=1)))

    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, "", "Permission denied")

    monkeypatch.setattr("services.conversion_sample_service.subprocess.run", fail)
    with pytest.raises(RuntimeError, match="Немає прав"):
        create_sample(ffmpeg, source, "audio", ConversionSettings(), tmp_path / "samples")
    assert not list((tmp_path / "samples").rglob("*.mp3"))


def test_real_video_and_audio_samples_preserve_source_and_track(tmp_path, monkeypatch):
    binary = os.environ.get("MEDIA_CONVERTER_TEST_FFMPEG") or shutil.which("ffmpeg")
    if not binary:
        pytest.skip("Set MEDIA_CONVERTER_TEST_FFMPEG to run real media sample conversion")
    source = tmp_path / "two tracks.mp4"
    subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=8000",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=8000",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "2:a",
            "-t",
            "22",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            str(source),
        ],
        capture_output=True,
        check=True,
        timeout=45,
    )
    original = source.read_bytes()
    ffmpeg = FfmpegService(binary, None)
    monkeypatch.setattr(
        ffmpeg, "probe_media", Mock(return_value=MediaInfo(duration=22, width=160, height=90, audio_streams=2, vcodec="h264", acodec="aac"))
    )
    cache = tmp_path / "samples"
    settings = ConversionSettings(operation="audio_only", audio_track_index=1, trim_start=3)
    audio = create_sample(ffmpeg, source, "video", settings, cache)
    video = create_sample(ffmpeg, source, "video", ConversionSettings(trim_start=3, preset="ultrafast"), cache)
    assert audio.suffix == ".mp3"
    assert video.suffix == ".mp4"
    assert audio != video
    for output in (audio, video):
        progress = subprocess.run(
            [binary, "-v", "error", "-i", str(output), "-f", "null", "-", "-progress", "pipe:1"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        duration = [int(line.split("=")[1]) / 1_000_000 for line in progress.stdout.splitlines() if line.startswith("out_time_us=")][-1]
        assert 14.8 <= duration <= 15.3, progress.stdout
    decoded = subprocess.run(
        [binary, "-v", "error", "-i", str(audio), "-t", "1", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"],
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    samples = struct.unpack("<" + "h" * (len(decoded) // 2), decoded)
    # Measure the selected 880 Hz tone in the steady part of the MP3. Decoder
    # padding and low-level ringing can add zero crossings in quiet samples.
    steady = samples[2000:6000]
    assert len(steady) == 4000
    phase_step = math.tau * 880 / 8000
    cosine = sum(value * math.cos(phase_step * i) for i, value in enumerate(steady))
    sine = sum(value * math.sin(phase_step * i) for i, value in enumerate(steady))
    energy = sum(value * value for value in steady)
    assert 2 * (cosine**2 + sine**2) > 0.8 * len(steady) * energy
    assert source.read_bytes() == original


def test_backend_audio_preview_preserves_queue_and_overrides(tmp_path, monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from app.models import TaskItem, TaskStatus
    from ui.backend import Backend

    app = QApplication.instance() or QApplication([])
    backend = Backend()
    backend.settings_manager.save = Mock()
    source = tmp_path / "input.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "sample.mp3"
    output.write_bytes(b"audio")
    task = TaskItem(
        source,
        "video",
        status=TaskStatus.SUCCESS,
        last_output="original-output.mp4",
        overrides={"operation": "convert", "audio_track_index": 1, "trim_start": 4},
    )
    backend.queue_model.set_items([task])
    producer = Mock(return_value=output)
    monkeypatch.setattr("services.conversion_sample_service.create_sample", producer)
    finished = []
    backend.conversionSampleFinished.connect(lambda path, error: finished.append((path, error)))
    try:
        assert backend.createConversionSample(str(source), {"_sample_audio_only": True}, 15)
        for _ in range(50):
            QTest.qWait(20)
            if finished:
                break
        assert finished == [(str(output), "")]
        assert not backend._sample_busy
        resolved = producer.call_args.args[3]
        assert resolved.operation == "audio_only"
        assert resolved.audio_track_index == 1
        assert resolved.trim_start == 4
        assert task.status == TaskStatus.SUCCESS
        assert task.last_output == "original-output.mp4"
        assert task.overrides["operation"] == "convert"
    finally:
        backend.shutdown()
        app.processEvents()
