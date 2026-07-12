import queue
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from app.models import ConversionSettings, TaskItem
from services.converter_service import ConverterService


class FakeFfmpegService:
    def __init__(self) -> None:
        self.ffmpeg_path = "/usr/bin/ffmpeg"
        self.ffprobe_path = None
        self.encoder_caps = set()
        self.audio_called = False
        self.video_called = False
        self.auto_audio_processing = False

    def output_extension_for(self, media_type_name, settings):
        if settings.operation == "audio_only":
            return "mp3"
        if settings.operation == "auto_subtitle":
            return "srt"
        if media_type_name == "video":
            return "mp4"
        if media_type_name == "audio":
            return "mp3"
        if media_type_name == "subtitle":
            return "srt"
        if media_type_name == "text":
            return settings.out_text_format
        return "jpg"

    def build_audio_speed_filter(self, settings):
        return None

    def has_audio_processing(self, settings):
        return self.auto_audio_processing

    def build_video_filter_spec(self, inp, settings, out_ext, log_cb=None):
        return None, None, None, [], False

    def fast_copy_allowed(self, inp, out_ext, info, filters_used, audio_filter_used, allow_remux=False):
        return True, ""

    def build_video_command(self, inp, outp, settings, info, allow_fast_copy, log_cb=None):
        self.video_called = True
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_image_command(self, inp, outp, settings, log_cb=None):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_audio_command(self, inp, outp, settings, duration=None, log_cb=None):
        self.audio_called = True
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_subtitle_file_command(self, inp, outp, settings):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_subtitle_extract_command(self, inp, outp, settings):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_thumbnail_command(self, inp, outp, settings, log_cb=None):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_contact_sheet_command(self, inp, outp, settings):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def check_media_integrity(self, _output_path):
        return True, ""


class FakeTranscriber:
    def __init__(self) -> None:
        self.called = False

    def generate(self, inp, outp, settings, log_cb=None):
        self.called = True
        Path(outp).write_text("subtitle", encoding="utf-8")
        return 0


class MockConverterService(ConverterService):
    def _create_child_service(self, result_queue):
        child = MockConverterService(self.ffmpeg, result_queue, self.transcriber)
        child._output_path_lock = self._output_path_lock
        child._reserved_output_paths = self._reserved_output_paths
        return child

    def _run_ffmpeg(self, cmd, duration, total_done, total_duration, done_files, total_files, total_start):
        Path(cmd[-1]).write_text("ok", encoding="utf-8")
        return 0


def drain_events(event_queue: "queue.Queue[tuple]") -> list[tuple]:
    events = []
    while True:
        try:
            events.append(event_queue.get_nowait())
        except queue.Empty:
            return events


class ConverterServiceTest(unittest.TestCase):
    def test_skip_existing_marks_task_as_skipped(self) -> None:
        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.mp4"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("video", encoding="utf-8")
            (out_dir / "input.mp4").write_text("existing", encoding="utf-8")

            task = TaskItem(path=inp, media_type="video")
            settings = ConversionSettings(skip_existing=True, out_video_format="mp4")
            service._run([task], settings, out_dir)

            payloads = drain_events(events)
            task_events = [event for event in payloads if event[0] == "task_state"]
            self.assertTrue(any(event[2] == "skipped" for event in task_events))

    def test_audio_only_uses_audio_builder_and_marks_success(self) -> None:
        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.mp4"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("video", encoding="utf-8")

            task = TaskItem(path=inp, media_type="video")
            settings = ConversionSettings(operation="audio_only", out_audio_format="mp3")
            service._run([task], settings, out_dir)

            self.assertTrue(fake.audio_called)
            task_events = [event for event in drain_events(events) if event[0] == "task_state"]
            self.assertTrue(any(event[2] == "success" for event in task_events))

    def test_missing_file_marks_failed(self) -> None:
        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            task = TaskItem(path=out_dir / "missing.mp4", media_type="video")
            settings = ConversionSettings()
            service._run([task], settings, out_dir)

            task_events = [event for event in drain_events(events) if event[0] == "task_state"]
            self.assertTrue(any(event[2] == "failed" for event in task_events))

    def test_auto_subtitle_uses_transcriber(self) -> None:
        fake = FakeFfmpegService()
        transcriber = FakeTranscriber()
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)
        service.transcriber = transcriber

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.mp4"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("video", encoding="utf-8")

            task = TaskItem(path=inp, media_type="video")
            settings = ConversionSettings(operation="auto_subtitle", out_subtitle_format="srt")
            service._run([task], settings, out_dir)

            self.assertTrue(transcriber.called)
            task_events = [event for event in drain_events(events) if event[0] == "task_state"]
            self.assertTrue(any(event[2] == "success" for event in task_events))

    def test_convert_audio_source_uses_audio_builder(self) -> None:
        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.wav"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("audio", encoding="utf-8")

            task = TaskItem(path=inp, media_type="audio")
            settings = ConversionSettings(operation="convert", out_audio_format="mp3")
            service._run([task], settings, out_dir)

            self.assertTrue(fake.audio_called)
            task_events = [event for event in drain_events(events) if event[0] == "task_state"]
            self.assertTrue(any(event[2] == "success" for event in task_events))

    def test_text_conversion_does_not_require_ffmpeg(self) -> None:
        fake = FakeFfmpegService()
        fake.ffmpeg_path = None
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "notes.txt"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("hello\nworld", encoding="utf-8")

            task = TaskItem(path=inp, media_type="text")
            settings = ConversionSettings(operation="convert", out_text_format="html")
            service._run([task], settings, out_dir)

            output = out_dir / "notes.html"
            self.assertTrue(output.exists())
            self.assertIn("<pre>hello", output.read_text(encoding="utf-8"))
            task_events = [event for event in drain_events(events) if event[0] == "task_state"]
            self.assertTrue(any(event[2] == "success" for event in task_events))

    def test_parallel_conversion_preserves_output_template_index(self) -> None:
        fake = FakeFfmpegService()
        fake.encoder_caps = {"h264_nvenc"}
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            out_dir = tmp / "out"
            out_dir.mkdir()
            first = tmp / "first.mp4"
            second = tmp / "second.mp4"
            first.write_text("video", encoding="utf-8")
            second.write_text("video", encoding="utf-8")

            settings = ConversionSettings(out_video_format="mp4", output_template="{index}_{stem}")
            service._run(
                [
                    TaskItem(path=first, media_type="video"),
                    TaskItem(path=second, media_type="video"),
                ],
                settings,
                out_dir,
            )

            self.assertTrue((out_dir / "001_first.mp4").exists())
            self.assertTrue((out_dir / "002_second.mp4").exists())

    def test_parallel_conversion_reserves_duplicate_output_names(self) -> None:
        fake = FakeFfmpegService()
        fake.encoder_caps = {"h264_nvenc"}
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            out_dir = tmp / "out"
            out_dir.mkdir()
            first = tmp / "camera_a" / "clip.mp4"
            second = tmp / "camera_b" / "clip.mp4"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")

            service._run(
                [TaskItem(path=first, media_type="video"), TaskItem(path=second, media_type="video")],
                ConversionSettings(out_video_format="mp4", output_template="{stem}"),
                out_dir,
            )

            self.assertTrue((out_dir / "clip.mp4").exists())
            self.assertTrue((out_dir / "clip (1).mp4").exists())

    def test_successful_conversion_writes_checksum_sidecar(self) -> None:
        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.mp4"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("video", encoding="utf-8")

            task = TaskItem(path=inp, media_type="video")
            settings = ConversionSettings(out_video_format="mp4", checksum_algorithm="sha256")
            service._run([task], settings, out_dir)

            sidecar = out_dir / "input.mp4.sha256"
            self.assertTrue(sidecar.exists())
            self.assertIn("input.mp4", sidecar.read_text(encoding="utf-8"))

    def test_integrity_failure_keeps_original_when_secure_delete_is_enabled(self) -> None:
        fake = FakeFfmpegService()
        fake.check_media_integrity = lambda _output_path: (False, "decode error")
        events: queue.Queue[tuple] = queue.Queue()
        service = MockConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.mp4"
            out_dir = tmp / "out"
            out_dir.mkdir()
            inp.write_text("original", encoding="utf-8")

            service._run(
                [TaskItem(path=inp, media_type="video")],
                ConversionSettings(secure_delete_original=True, smart_integrity_check=True),
                out_dir,
            )

            self.assertTrue(inp.exists())
            self.assertTrue((out_dir / "input.mp4").exists())

    def test_missing_ffmpeg_is_recorded_in_run_summary(self) -> None:
        class MissingFfmpegConverter(MockConverterService):
            def _run_ffmpeg(self, *_args, **_kwargs):
                raise FileNotFoundError

        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = MissingFfmpegConverter(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inp = tmp / "input.mp4"
            inp.write_text("video", encoding="utf-8")
            service._run([TaskItem(path=inp, media_type="video")], ConversionSettings(), tmp)

        summaries = [event[1] for event in drain_events(events) if event[0] == "run_summary"]
        self.assertEqual(summaries[0]["results"][0]["status"], "failed")

    def test_cancelling_overwrite_keeps_previous_output(self) -> None:
        fake = FakeFfmpegService()
        events: queue.Queue[tuple] = queue.Queue()
        service = ConverterService(fake, events)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            output = tmp / "output.mp4"
            output.write_text("previous result", encoding="utf-8")
            worker = tmp / "writer.py"
            worker.write_text(
                "from pathlib import Path\n"
                "import sys\n"
                "import time\n"
                "Path(sys.argv[-1]).write_text('partial result', encoding='utf-8')\n"
                "print('progress=continue', flush=True)\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            result: list[int] = []
            thread = threading.Thread(
                target=lambda: result.append(
                    service._run_ffmpeg([sys.executable, str(worker), str(output)], None, 0, 0, 0, 1, time.time())
                )
            )
            thread.start()
            for _ in range(100):
                if service.current_proc is not None:
                    break
                time.sleep(0.01)
            service.stop()
            thread.join(timeout=5)

            self.assertFalse(thread.is_alive())
            self.assertEqual(output.read_text(encoding="utf-8"), "previous result")
            self.assertFalse(list(tmp.glob("*.partial.mp4")))
            self.assertNotEqual(result, [0])


if __name__ == "__main__":
    unittest.main()
