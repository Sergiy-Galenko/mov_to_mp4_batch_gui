import queue
import tempfile
import unittest
from pathlib import Path

from core.models import ConversionSettings, TaskItem
from services.converter_service import ConverterService


class FakeFfmpegService:
    def __init__(self) -> None:
        self.ffmpeg_path = "/usr/bin/ffmpeg"
        self.ffprobe_path = None
        self.audio_called = False
        self.video_called = False
        self.auto_audio_processing = False

    def output_extension_for(self, media_type_name, settings):
        if settings.operation == "audio_only":
            return "mp3"
        if settings.operation == "auto_subtitle":
            return "srt"
        return "mp4" if media_type_name == "video" else "jpg"

    def build_audio_speed_filter(self, settings):
        return None

    def has_audio_processing(self, settings):
        return self.auto_audio_processing

    def build_video_filter_spec(self, inp, settings, out_ext, log_cb=None):
        return None, None, None, [], False

    def fast_copy_allowed(self, inp, out_ext, info, filters_used, audio_filter_used):
        return True, ""

    def build_video_command(self, inp, outp, settings, info, allow_fast_copy, log_cb=None):
        self.video_called = True
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_image_command(self, inp, outp, settings, log_cb=None):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_audio_command(self, inp, outp, settings, log_cb=None):
        self.audio_called = True
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_subtitle_extract_command(self, inp, outp, settings):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_thumbnail_command(self, inp, outp, settings, log_cb=None):
        return ["ffmpeg", "-i", str(inp), str(outp)]

    def build_contact_sheet_command(self, inp, outp, settings):
        return ["ffmpeg", "-i", str(inp), str(outp)]


class FakeTranscriber:
    def __init__(self) -> None:
        self.called = False

    def generate(self, inp, outp, settings, log_cb=None):
        self.called = True
        Path(outp).write_text("subtitle", encoding="utf-8")
        return 0


class MockConverterService(ConverterService):
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
        events: "queue.Queue[tuple]" = queue.Queue()
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
        events: "queue.Queue[tuple]" = queue.Queue()
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
        events: "queue.Queue[tuple]" = queue.Queue()
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
        events: "queue.Queue[tuple]" = queue.Queue()
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


if __name__ == "__main__":
    unittest.main()
