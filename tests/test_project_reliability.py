import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models import ConversionSettings, MediaInfo, TaskItem, TaskStatus
from services.adaptive_scheduler import MIB, AdaptiveScheduler
from services.cache_manager import CacheManager
from services.converter_service import ConverterService
from services.diagnostic_service import build_report, summarize_command
from services.ffmpeg_service import FfmpegService
from services.hardware_pipeline import configure_pipeline, software_pipeline
from services.media_preview_service import MediaPreviewService
from services.queue_manager import QueueManager
from services.task_journal import TaskJournal
from services.workload_history import WorkloadHistory


def test_cache_keys_include_source_and_all_render_parameters(tmp_path):
    source = tmp_path / "clip.mov"
    source.write_bytes(b"first")
    cache = CacheManager(tmp_path / "cache")
    key = cache.key(source, "snapshots", {"width": 160})
    assert key != cache.key(source, "snapshots", {"width": 320})
    assert key != cache.key(source, "waveforms", {"width": 160})
    source.write_bytes(b"other")  # same byte length, different identity/timestamps
    assert key != cache.key(source, "snapshots", {"width": 160})


def test_concurrent_cache_producers_publish_once(tmp_path):
    source = tmp_path / "input"
    source.write_bytes(b"source")
    cache = CacheManager(tmp_path / "cache")
    calls = []

    def produce(target):
        calls.append(target)
        target.write_bytes(b"complete")
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: cache.produce(source, "metadata", {}, ".json", produce), range(4)))
    assert len(calls) == 1
    assert len(set(results)) == 1
    assert results[0].read_bytes() == b"complete"
    assert not list(cache.root.glob("*/.*.partial*"))


@pytest.mark.parametrize("mode", ["failure", "exception", "source_changed", "oversize"])
def test_failed_or_stale_cache_production_never_becomes_a_hit(tmp_path, mode):
    source = tmp_path / "input"
    source.write_bytes(b"source")
    cache = CacheManager(tmp_path / "cache", max_bytes=10)

    def produce(target):
        target.write_bytes(b"invalid" if mode != "oversize" else b"x" * 11)
        if mode == "exception":
            raise RuntimeError("failed")
        if mode == "source_changed":
            source.write_bytes(b"changed")
        return mode != "failure"

    if mode == "exception":
        with pytest.raises(RuntimeError):
            cache.produce(source, "metadata", {}, ".json", produce)
    else:
        assert cache.produce(source, "metadata", {}, ".json", produce) is None
    assert cache.statistics()["entries"] == 0
    assert not list(cache.root.glob("*/.*.partial*"))


def test_quota_evicts_oldest_but_honors_reader_leases(tmp_path):
    source = tmp_path / "input"
    source.write_bytes(b"source")
    cache = CacheManager(tmp_path / "cache", max_bytes=10)

    def produce(target):
        target.write_bytes(b"123456")
        return True

    first = cache.produce(source, "metadata", {"n": 1}, ".json", produce)
    with cache.lease(first):
        second = cache.produce(source, "metadata", {"n": 2}, ".json", produce)
        assert first.is_file() and second.is_file()
        cache.cleanup(clear=True)
        assert first.is_file() and not second.exists()
    assert cache.cleanup(clear=True) == 1
    assert not first.exists()
    assert source.read_bytes() == b"source"


def test_preview_dimensions_and_colors_do_not_reuse_wrong_artifacts(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"source")
    cache = CacheManager(tmp_path / "cache")
    service = MediaPreviewService("ffmpeg", cache=cache)
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"image")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("services.media_preview_service.subprocess.run", run)
    a = service.video_snapshot(source, 1, width=320)
    b = service.video_snapshot(source, 1, width=640)
    assert a != b
    assert service.video_snapshot(source, 1, width=320) == a
    wave1 = service.audio_waveform(source, color="red")
    wave2 = service.audio_waveform(source, color="blue")
    assert wave1 != wave2
    assert len(commands) == 4


def test_metadata_cache_preserves_chapters_and_invalidates_source_changes(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"source")
    ffmpeg = FfmpegService("ffmpeg", "ffprobe")
    ffmpeg.cache = CacheManager(tmp_path / "cache")
    probe = Mock(return_value=MediaInfo(vcodec="h264", width=1920, height=1080))
    monkeypatch.setattr(ffmpeg, "_probe_media_uncached", probe)
    assert ffmpeg.probe_media(source).width == 1920
    assert ffmpeg.probe_media(source).vcodec == "h264"
    assert probe.call_count == 1
    source.write_bytes(b"changed")
    assert ffmpeg.probe_media(source).vcodec == "h264"
    assert probe.call_count == 2


def test_task_identity_survives_serialization_and_rejects_imported_duplicates(tmp_path):
    task = TaskItem(tmp_path / "clip.mp4", "video")
    manager = QueueManager()
    raw = manager.serialize_task(task)
    restored = manager.deserialize_tasks([raw, raw])
    assert restored[0].task_id == task.task_id
    assert restored[1].task_id != task.task_id
    assert replace(task).task_id == task.task_id


def test_journal_recovers_publication_after_crash_without_reencoding(tmp_path):
    source = tmp_path / "source.mov"
    source.write_bytes(b"source")
    output = tmp_path / "output.mp4"
    task = TaskItem(source, "video")
    journal = TaskJournal(tmp_path / "tasks.sqlite3")
    journal.prepare(task, ConversionSettings())
    journal.plan_output(task.task_id, output)
    journal.transition(task.task_id, TaskStatus.RUNNING)
    output.write_bytes(b"complete result")
    journal.publication(task.task_id, output)
    recovered = TaskJournal(journal.path).recover_items([replace(task)])[0]
    assert recovered.status == TaskStatus.SUCCESS
    assert recovered.last_output == str(output)
    output.write_bytes(b"damaged")
    recovered = journal.recover_items([replace(task)])[0]
    assert recovered.status == TaskStatus.QUEUED


def test_journal_source_change_and_postprocess_interruption_are_explicit(tmp_path):
    source = tmp_path / "source.mov"
    source.write_bytes(b"source")
    output = tmp_path / "output.mp4"
    output.write_bytes(b"output")
    task = TaskItem(source, "video")
    journal = TaskJournal(tmp_path / "tasks.sqlite3")
    journal.prepare(task, ConversionSettings(cloud_upload_enabled=True))
    journal.plan_output(task.task_id, output)
    journal.transition(task.task_id, TaskStatus.RUNNING)
    journal.publication(task.task_id, output)
    recovered = journal.recover_items([replace(task)])[0]
    assert recovered.status == TaskStatus.FAILED
    assert recovered.last_output == str(output)
    assert "post-processing" in recovered.last_error
    source.write_bytes(b"replacement")
    assert journal.recover_items([replace(task)])[0].status == TaskStatus.QUEUED


def test_journal_success_recovery_handles_semicolon_in_filename(tmp_path):
    source = tmp_path / "source.mov"
    source.write_bytes(b"source")
    output = tmp_path / "output;with;separator.mp4"
    output.write_bytes(b"output")
    task = TaskItem(source, "video")
    journal = TaskJournal(tmp_path / "tasks.sqlite3")
    journal.prepare(task, ConversionSettings())
    journal.plan_output(task.task_id, output)
    journal.transition(task.task_id, TaskStatus.SUCCESS, output=str(output))
    assert journal.recover_items([replace(task)])[0].status == TaskStatus.SUCCESS


def test_calibration_uses_only_sufficient_valid_machine_local_samples(tmp_path):
    history = WorkloadHistory(tmp_path / "workloads.sqlite3")
    settings, info = ConversionSettings(), MediaInfo(width=3840, height=2160)
    profile = history.profile(settings, info, "libx264", tool="build1", threads=4)
    for elapsed in (10, 12):
        history.record(profile, elapsed, 20, 2048 * MIB)
    assert history.estimate(profile, 20) == {}
    history.record(profile, 11, 20, 2048 * MIB)
    history.record(profile, float("nan"), 20, 2048 * MIB)
    prediction = history.estimate(profile, 40)
    assert prediction["samples"] == 3
    assert prediction["seconds"] == 22
    assert prediction["memory_bytes"] == 2560 * MIB
    assert history.estimate(history.profile(settings, info, "libx264", tool="build2")) == {}
    scheduler = AdaptiveScheduler(4, history=history, cpu_threads=8, memory_bytes=8 * 1024 * MIB)
    ffmpeg = FfmpegService("build1", None)
    ffmpeg.encoder_caps = {"libx264"}
    cost = scheduler.estimate(TaskItem(tmp_path / "source.mp4", "video"), settings, info, ffmpeg)
    assert cost.memory_bytes == 2560 * MIB


@pytest.mark.parametrize(
    "encoder,backend,scaler",
    [("h264_nvenc", "cuda", "scale_cuda"), ("h264_qsv", "qsv", "scale_qsv"), ("h264_vaapi", "vaapi", "scale_vaapi")],
)
def test_hardware_decode_scale_encode_path_has_a_working_software_fallback(encoder, backend, scaler):
    info = MediaInfo(vcodec="h264", pix_fmt="yuv420p")
    command = ["ffmpeg", "-y", "-i", "in.mp4", "-vf", "scale=640:360", "-map", "0:v:0?", "-c:v", encoder, "-pix_fmt", "yuv420p", "out.mp4"]
    accelerated = configure_pipeline(command, encoder, info, {scaler}, device="/dev/dri/renderD128")
    assert accelerated[accelerated.index("-hwaccel") + 1] == backend
    assert accelerated[accelerated.index("-vf") + 1] == f"{scaler}=640:360:format=nv12"
    converter = ConverterService(FfmpegService("ffmpeg", None), Queue())
    fallback = converter._create_cpu_fallback_command(accelerated)
    assert fallback[fallback.index("-c:v") + 1] == "libx264"
    assert fallback[fallback.index("-vf") + 1] == "scale=640:360"
    assert "-hwaccel" not in fallback and "-hwaccel_device" not in fallback
    assert fallback[fallback.index("-pix_fmt") + 1] == "yuv420p"


def test_complex_vaapi_filters_upload_once_and_fallback_preserves_graph():
    command = ["ffmpeg", "-y", "-i", "in.mp4", "-filter_complex", "[0:v]hflip[vout]", "-map", "[vout]", "-c:v", "h264_vaapi", "out.mp4"]
    accelerated = configure_pipeline(
        command, "h264_vaapi", MediaInfo(vcodec="h264", pix_fmt="yuv420p"), set(), device="/dev/dri/renderD128"
    )
    assert "-hwaccel" not in accelerated
    assert accelerated[accelerated.index("-map") + 1] == "[hardware_output]"
    assert "format=nv12,hwupload" in accelerated[accelerated.index("-filter_complex") + 1]
    fallback = software_pipeline(accelerated)
    assert "hwupload" not in fallback[fallback.index("-filter_complex") + 1]
    assert "hflip" in fallback[fallback.index("-filter_complex") + 1]


def test_vaapi_selection_is_available_in_linux_auto_and_explicit_modes(monkeypatch):
    monkeypatch.setattr("services.ffmpeg_service.sys.platform", "linux")
    ffmpeg = FfmpegService("ffmpeg", None)
    ffmpeg.encoder_caps = {"libx264", "h264_vaapi"}
    assert ffmpeg.select_encoder("h264", "auto") == ("h264_vaapi", True)
    assert ffmpeg.select_encoder("h264", "vaapi") == ("h264_vaapi", True)


def test_diagnostics_never_export_raw_paths_filters_or_secrets(tmp_path, monkeypatch):
    ffmpeg = FfmpegService("/private/user path/ffmpeg", None)
    ffmpeg.encoder_caps = {"libx264"}
    journal = TaskJournal(tmp_path / "tasks.sqlite3")
    journal.transition("test-id", TaskStatus.FAILED, "Permission denied /Users/private/My Videos/a.mov token=SECRET")
    monkeypatch.setattr(
        "services.diagnostic_service.subprocess.run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="ffmpeg version 7.1\n")
    )
    command = ["ffmpeg", "-y", "-i", "/Users/private/My Videos/a.mov", "-vf", "drawtext=text=SECRET", "-c:v", "libx264", "out.mp4"]
    plan = summarize_command(command)
    report = build_report(
        ffmpeg,
        logs=["ERROR /private/data token=SECRET"],
        plans=[{**plan, "path": "/secret/file"}],
        journal=journal,
        cache=CacheManager(tmp_path / "cache"),
    )
    encoded = json.dumps(report)
    for value in ("SECRET", "/Users", "/private", "/secret", "drawtext", "a.mov"):
        assert value not in encoded
    assert report["recent_processing_plans"][0]["video_filter"] is True
    assert report["recent_errors"][0]["category"] == "permission_denied"


def test_benchmark_regression_gate_rejects_different_environments_and_missing_metrics():
    from scripts.performance_suite import compare

    baseline = {"schema_version": 1, "environment_id": "machine", "metrics": {"encode_seconds": 1}}
    current = {**baseline, "metrics": {"encode_seconds": 2}}
    assert compare(current, baseline, 1.5)
    assert compare({**current, "metrics": {}}, baseline, 1.5)
    with pytest.raises(ValueError):
        compare({**current, "environment_id": "different"}, baseline, 1.5)


def test_in_memory_probe_identity_detects_source_replacement(tmp_path):
    from services.cache_manager import media_info_matches_source, source_fingerprint

    source = tmp_path / "source.mp4"
    source.write_bytes(b"old")
    info = MediaInfo(vcodec="h264", source_identity=source_fingerprint(source))
    assert media_info_matches_source(info, source)
    source.write_bytes(b"new")
    assert not media_info_matches_source(info, source)


def test_proxy_mapping_survives_service_restart_and_active_proxy_is_not_evicted(tmp_path):
    from services.proxy_service import ProxyService
    from services.timeline_service import TimelineClip, TimelineProject

    master = tmp_path / "source.mov"
    master.write_bytes(b"source")
    service = ProxyService("ffmpeg", tmp_path / "cache" / "proxies")
    proxy = service.get_proxy_path(master)
    proxy.write_bytes(b"video" * 300)
    service._register_pair(str(master), str(proxy))
    key = service._generate_cache_key(master)
    service.cache.register(key, "proxies", proxy)
    service.cache.cleanup(clear=True)
    assert proxy.is_file()
    service.close()
    reopened = ProxyService("ffmpeg", service.proxy_dir)
    project = TimelineProject(clips=[TimelineClip(source_path=str(proxy), in_point=0, out_point=1)])
    assert reopened.swap_proxies_for_masters(project).clips[0].source_path == str(master.resolve())
    reopened.close()


def test_stream_copy_does_not_reserve_gpu_or_full_frame_memory(tmp_path):
    scheduler = AdaptiveScheduler(4, cpu_threads=8, history=WorkloadHistory(tmp_path / "workloads.sqlite3"))
    ffmpeg = FfmpegService("ffmpeg", None)
    ffmpeg.encoder_caps = {"h264_nvenc", "libx264"}
    source = tmp_path / "source.mov"
    source.write_bytes(b"source")
    cost = scheduler.estimate(
        TaskItem(source, "video"),
        ConversionSettings(fast_copy=True),
        MediaInfo(vcodec="h264", acodec="aac", width=3840, height=2160),
        ffmpeg,
    )
    assert cost.hardware_sessions == 0
    assert cost.cpu_threads == 1
    assert cost.memory_bytes == 128 * MIB


def test_managed_speech_process_records_its_memory_and_time(tmp_path):
    import sys

    converter = ConverterService(FfmpegService("ffmpeg", None), Queue())
    converter.workload_history = WorkloadHistory(tmp_path / "workloads.sqlite3")
    converter._active_settings = ConversionSettings(operation="auto_subtitle", subtitle_model="tiny")
    converter._ffmpeg_thread_budget = 2
    source = tmp_path / "speech.wav"
    source.write_bytes(b"audio")
    converter.active_task_path = source
    info = MediaInfo(duration=2)
    converter.media_info[source] = info
    for _ in range(3):
        result = converter._run_command([sys.executable, "-c", "import time; time.sleep(.15)", "--transcribe-worker"], timeout=2)
        assert result.returncode == 0
    profile = converter.workload_history.profile(converter._active_settings, info, "none", tool="ffmpeg", threads=2)
    assert converter.workload_history.estimate(profile, 2)["samples"] == 3


def test_multiple_readers_share_cache_artifacts_while_eviction_is_excluded(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"source")
    cache = CacheManager(tmp_path / "cache")

    def produce(target):
        target.write_bytes(b"artifact")
        return True

    target = cache.produce(source, "metadata", {}, ".json", produce)
    arrived, release = threading.Event(), threading.Event()

    def reader():
        with CacheManager(cache.root).lease(target):
            arrived.set()
            release.wait(2)

    with cache.lease(target):
        thread = threading.Thread(target=reader)
        thread.start()
        assert arrived.wait(1)
        assert cache.cleanup(clear=True) == 0
        assert target.is_file()
        release.set()
        thread.join(2)
    assert not thread.is_alive()
    assert cache.cleanup(clear=True) == 1


def test_modified_cached_artifact_is_rejected_even_when_size_is_unchanged(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"source")
    cache = CacheManager(tmp_path / "cache")

    def produce(target):
        target.write_bytes(b"original")
        return True

    target = cache.produce(source, "metadata", {}, ".json", produce)
    key = cache.key(source, "metadata", {})
    target.write_bytes(b"tampered")
    assert cache.get(key) is None
    assert cache.produce(source, "metadata", {}, ".json", produce).read_bytes() == b"original"
