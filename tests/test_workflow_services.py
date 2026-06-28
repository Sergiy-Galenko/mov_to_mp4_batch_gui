import sys
import tempfile
import unittest
from pathlib import Path

from app.models import TaskItem
from services.ffmpeg_service import FfmpegService
from services.preview_builder import PreviewBuilder
from services.validation_service import ValidationService


class WorkflowServicesTest(unittest.TestCase):
    def test_validation_rejects_empty_queue_and_missing_ffmpeg(self) -> None:
        service = ValidationService(FfmpegService(None, None))
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.validate(
                {"operation": "Конвертація"},
                tasks=[],
                output_dir=tmpdir,
                ffmpeg_path="",
                include_queue=True,
            )
        self.assertFalse(result["ok"])
        self.assertIn("queue", result["errors"])
        self.assertIn("ffmpeg", result["errors"])

    def test_validation_rejects_invalid_trim_range(self) -> None:
        service = ValidationService(FfmpegService(sys.executable, None))
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.validate(
                {"operation": "Конвертація", "trim_start": "10", "trim_end": "5"},
                tasks=[],
                output_dir=tmpdir,
                ffmpeg_path=sys.executable,
                include_queue=False,
            )
        self.assertFalse(result["ok"])
        self.assertIn("trim_end", result["errors"])

    def test_validation_rejects_operation_that_does_not_support_file_type(self) -> None:
        service = ValidationService(FfmpegService(sys.executable, None))
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            image = tmp / "cover.jpg"
            image.write_text("image", encoding="utf-8")
            result = service.validate(
                {"operation": "Лише аудіо"},
                tasks=[TaskItem(path=image, media_type="image")],
                output_dir=tmpdir,
                ffmpeg_path=sys.executable,
                include_queue=True,
            )
        self.assertFalse(result["ok"])
        self.assertIn("queue", result["errors"])

    def test_preview_builds_audio_and_subtitle_convert_commands(self) -> None:
        ffmpeg = FfmpegService("ffmpeg", None)
        builder = PreviewBuilder(ffmpeg)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            audio = tmp / "voice.wav"
            subtitle = tmp / "captions.srt"
            audio.write_text("audio", encoding="utf-8")
            subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")

            summary = builder.build(
                {"operation": "Конвертація", "out_audio_fmt": "flac", "out_subtitle_fmt": "vtt"},
                tasks=[
                    TaskItem(path=audio, media_type="audio"),
                    TaskItem(path=subtitle, media_type="subtitle"),
                ],
                output_dir=tmpdir,
            )

        self.assertEqual(len(summary.items), 2)
        self.assertTrue(str(summary.items[0].output_path).endswith(".flac"))
        self.assertIn("-c:a flac", summary.items[0].command)
        self.assertTrue(str(summary.items[1].output_path).endswith(".vtt"))
        self.assertIn("webvtt", summary.items[1].command)


if __name__ == "__main__":
    unittest.main()
