from __future__ import annotations

import queue
import threading
import unittest
from contextlib import suppress
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6 import QtWidgets
from PySide6.QtTest import QAbstractItemModelTester

from app.models import ConversionSettings, MediaInfo, TaskItem, TaskStatus
from services.converter_service import ConverterService
from services.event_queue import UiEventQueue
from services.ffmpeg_service import FfmpegService
from services.folder_scanner import FolderScanner
from services.queue_manager import QueueManager
from services.resource_monitor import ResourceMonitor
from services.taskbar_service import TaskbarService
from services.theme_manager import ThemeManager
from services.transcription_service import TranscriptionService
from ui.models import LogModel, QueueFilterModel, QueueModel
from utils.files import render_output_stem


class Version2UpgradesTest(unittest.TestCase):
    def test_render_output_stem_rich_tokens(self) -> None:
        path = Path("/files/video_sample.mov")
        info = MediaInfo(
            width=1920,
            height=1080,
            vcodec="h264",
            acodec="aac",
            duration=90.5,
            fps=60.0,
        )
        stem = render_output_stem(
            "{name}_{res}_{vcodec}_{fps}_{dur}",
            path,
            index=1,
            operation="convert",
            media_type_name="video",
            info=info,
        )
        self.assertEqual(stem, "video_sample_1080p_h264_60fps_90s")

    def test_gpu_encoder_detection_and_fallback(self) -> None:
        self.assertTrue(FfmpegService.is_gpu_encoder("h264_nvenc"))
        self.assertTrue(FfmpegService.is_gpu_encoder("hevc_qsv"))
        self.assertFalse(FfmpegService.is_gpu_encoder("libx264"))
        self.assertEqual(FfmpegService.get_cpu_fallback_encoder("h264_nvenc"), "libx264")
        self.assertEqual(FfmpegService.get_cpu_fallback_encoder("hevc_aof"), "libx265")

    def test_create_cpu_fallback_command(self) -> None:
        ffmpeg = FfmpegService("ffmpeg", "ffprobe")
        srv = ConverterService(ffmpeg, None, None)
        cmd = ["ffmpeg", "-i", "in.mp4", "-c:v", "h264_nvenc", "-gpu", "0", "out.mp4"]
        fallback = srv._create_cpu_fallback_command(cmd)
        self.assertIsNotNone(fallback)
        self.assertIn("libx264", fallback)
        self.assertNotIn("h264_nvenc", fallback)
        self.assertNotIn("-gpu", fallback)

    def test_theme_modes(self) -> None:
        tm = ThemeManager(Path("scratch_theme.json"))
        tm.set_theme_mode("obsidian")
        self.assertEqual(tm.theme_mode(), "obsidian")
        tm.set_theme_mode("oled")
        self.assertEqual(tm.theme_mode(), "oled")
        tm.set_queue_view_mode("grid")
        self.assertEqual(tm.queue_view_mode(), "grid")
        if Path("scratch_theme.json").exists():
            Path("scratch_theme.json").unlink(missing_ok=True)

    def test_taskbar_service_states_safety(self) -> None:
        tb = TaskbarService(None)
        tb.set_running_progress(0.75)
        tb.set_paused()
        tb.set_error()
        tb.clear_progress()

    def test_transcription_service_format(self) -> None:
        ts = TranscriptionService()
        settings = ConversionSettings(out_subtitle_format="vtt")
        fmt = ts._resolve_format(settings, Path("out.vtt"))
        self.assertEqual(fmt, "vtt")


if __name__ == "__main_":
    unittest.main()


_APP = None


@pytest.fixture
def qt_app():
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return _APP


def test_progress_does_not_refilter_or_invalidate_thumbnails(qt_app):
    model = QueueModel()
    task = TaskItem(Path("/clip.mp4"), "video", status=TaskStatus.RUNNING)
    model.add_items([task])
    proxy = QueueFilterModel()
    proxy.setSourceModel(model)
    proxy.set_filters("clip", "processing", "all")
    assert proxy.rowCount() == 1
    changes = []
    model.dataChanged.connect(lambda _a, _b, roles: changes.append(roles))
    with patch.object(proxy, "filterAcceptsRow", wraps=proxy.filterAcceptsRow) as accepts:
        model.set_task_progress(task.path, 0.5, "00:05", "2x")
        assert proxy.rowCount() == 1
        accepts.assert_not_called()
    assert changes == [[QueueModel.ProgressRole, QueueModel.EtaRole, QueueModel.SpeedRole]]
    model.update_task_state(task.path, TaskStatus.SUCCESS)
    assert proxy.rowCount() == 0


def test_index_survives_reordering_replacement_and_removal(qt_app):
    model = QueueModel()
    tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
    first, second, third = [TaskItem(Path(f"/{name}.txt"), "text") for name in ("a", "b", "c")]
    model.add_items([first, second])
    model.add_items([third])
    model.set_items([third, first, second])
    assert model.index_for_path(first.path) == 1
    replacement = TaskItem(Path("/new.txt"), "text")
    model.update_item(1, replacement)
    assert model.item_by_path(first.path) is None
    assert model.item_by_path(replacement.path) is replacement
    model.set_items([second])
    model.set_task_progress(third.path, 1.0)
    assert model.index_for_path(second.path) == 0
    assert second.progress == 0.0
    assert tester.model() is model


def test_log_is_bounded_and_keeps_latest_entries(qt_app):
    model = LogModel()
    model.MAX_ENTRIES = 3
    for number in range(10):
        model.append("INFO", str(number))
    assert model.rowCount() == 3
    assert model.data(model.index(0), LogModel.MessageRole) == "7"
    assert model.data(model.index(2), LogModel.MessageRole) == "9"


def test_progress_bursts_keep_terminal_events_and_accounting():
    events = UiEventQueue()
    for number in range(10000):
        events.put(("progress", number))
    events.put(("task_state", "a", "success"))
    events.put(("progress", 0))
    events.put(("log", "INFO", "finished"))
    assert events.qsize() == 4
    assert events.get_nowait() == ("progress", 9999)
    events.task_done()
    assert events.get_nowait() == ("task_state", "a", "success")
    events.task_done()
    assert events.get_nowait() == ("progress", 0)
    events.task_done()
    assert events.get_nowait() == ("log", "INFO", "finished")
    events.task_done()
    assert events.unfinished_tasks == 0
    with pytest.raises(queue.Empty):
        events.get_nowait()


def test_progress_for_different_tasks_is_not_discarded():
    events = UiEventQueue()
    events.put(("task_progress", "a", 0.2))
    events.put(("task_progress", "b", 0.7))
    events.put(("task_progress", "b", 0.8))
    assert events.get_nowait() == ("task_progress", "a", 0.2)
    assert events.get_nowait() == ("task_progress", "b", 0.8)


def test_resource_sampler_returns_while_worker_is_blocked():
    release = threading.Event()
    started = threading.Event()
    monitor = ResourceMonitor()

    def slow_collect():
        started.set()
        release.wait(5)

    try:
        with patch.object(monitor, "_collect", side_effect=slow_collect) as collect:
            assert monitor.sample()["cpu"] == 100.0
            assert started.wait(1)
            for _ in range(5):
                monitor.sample()
            assert collect.call_count == 1
    finally:
        release.set()
        monitor._worker.join(timeout=2)


def test_scanner_preserves_filters_and_does_not_follow_directory_symlinks(tmp_path):
    (tmp_path / "a.MP4").write_bytes(b"1234")
    (tmp_path / "b.txt").write_bytes(b"1234")
    (tmp_path / "c.mp4").write_bytes(b"1")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "d.mp4").write_bytes(b"1234")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "e.mp4").write_bytes(b"1234")
    with suppress(OSError):
        (nested / "loop").symlink_to(tmp_path, target_is_directory=True)
    scanner = FolderScanner(type_filter="video", min_size_bytes=2)
    expected = [tmp_path / "a.MP4", nested / "e.mp4"]
    assert scanner.scan(tmp_path) == expected
    stats = scanner.scan_with_stats(tmp_path)
    assert stats == {"files": expected, "total_scanned": 5, "excluded": 1, "type_filtered": 1, "size_filtered": 1}
    scanner.exclude_patterns = {"A.*"}
    assert scanner.scan(tmp_path) == [nested / "e.mp4"]


def test_hash_dedup_skips_unique_sizes_and_refreshes_stale_hashes(tmp_path):
    tasks = []
    for name, data in (("a", b"same"), ("b", b"same"), ("c", b"different size")):
        path = tmp_path / f"{name}.txt"
        path.write_bytes(data)
        tasks.append(TaskItem(path, "text"))
    from utils.files import file_sha256

    with patch("services.queue_manager.file_sha256", wraps=file_sha256) as digest:
        unique, removed, _ = QueueManager().deduplicate_by_hash(tasks)
    assert unique == [tasks[0], tasks[2]]
    assert removed == 1
    assert digest.call_count == 2
    tasks[1].path.write_bytes(b"edit")
    unique, removed, _ = QueueManager().deduplicate_by_hash(tasks)
    assert unique == tasks
    assert removed == 0


def test_backend_stats_never_reads_disk_and_event_processing_yields(qt_app):
    from ui.backend import Backend

    backend = Backend()
    try:
        backend.queue_model.set_items([TaskItem(Path("/a.txt"), "text", input_bytes=1024, output_bytes=256)])
        with patch.object(Path, "stat", side_effect=AssertionError("UI statistics performed disk I/O")):
            backend._refresh_session_stats()
        assert backend._session_input_text == "1.0 KB"
        backend._append_log = Mock()
        for number in range(1000):
            backend.event_queue.put(("log", "INFO", str(number)))
        backend._poll_events()
        assert 0 < backend._append_log.call_count <= 128
        assert not backend.event_queue.empty()
    finally:
        backend.settings_manager.save = Mock()
        backend.shutdown()
