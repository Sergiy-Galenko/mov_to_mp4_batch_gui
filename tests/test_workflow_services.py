import sys
import tempfile
import unittest
from pathlib import Path

from app.models import TaskItem
from services.ffmpeg_service import FfmpegService
from services.preview_builder import PreviewBuilder
from services.queue_manager import QueueManager
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

    def test_draft_validation_ignores_runtime_preflight_requirements(self) -> None:
        service = ValidationService(FfmpegService(None, None))
        result = service.validate(
            {"operation": "Конвертація"},
            tasks=[],
            output_dir="",
            ffmpeg_path="",
            include_queue=False,
            require_output_dir=False,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], {})

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

    def test_preview_uses_image_format_for_image_sources(self) -> None:
        ffmpeg = FfmpegService("ffmpeg", None)
        builder = PreviewBuilder(ffmpeg)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            image = tmp / "cover.jpg"
            image.write_text("image", encoding="utf-8")

            summary = builder.build(
                {"operation": "Конвертація", "out_video_fmt": "mp4", "out_image_fmt": "webp"},
                tasks=[TaskItem(path=image, media_type="image")],
                output_dir=tmpdir,
            )

        self.assertEqual(len(summary.items), 1)
        self.assertTrue(str(summary.items[0].output_path).endswith(".webp"))
        self.assertFalse(str(summary.items[0].output_path).endswith(".mp4"))

    def test_merge_preview_uses_single_merged_output(self) -> None:
        ffmpeg = FfmpegService("ffmpeg", None)
        builder = PreviewBuilder(ffmpeg)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            first = tmp / "first.mp4"
            second = tmp / "second.mp4"
            first.write_text("video", encoding="utf-8")
            second.write_text("video", encoding="utf-8")

            summary = builder.build(
                {
                    "operation": "convert",
                    "merge": True,
                    "merge_name": "joined",
                    "out_video_fmt": "mp4",
                    "output_template": "{stem}_individual",
                },
                tasks=[
                    TaskItem(path=first, media_type="video"),
                    TaskItem(path=second, media_type="video"),
                ],
                output_dir=tmpdir,
            )

        self.assertEqual({item.output_path.name for item in summary.items}, {"joined.mp4"})
        self.assertIn("Merge (2", summary.text)
        self.assertIn("concat", summary.selected_command)

    def test_merge_validation_checks_merged_output_path(self) -> None:
        service = ValidationService(FfmpegService(sys.executable, None))
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            first = tmp / "first.mp4"
            second = tmp / "second.mp4"
            merged = tmp / "joined.mp4"
            first.write_text("video", encoding="utf-8")
            second.write_text("video", encoding="utf-8")
            merged.write_text("existing", encoding="utf-8")

            result = service.validate(
                {
                    "operation": "convert",
                    "merge": True,
                    "merge_name": "joined",
                    "out_video_fmt": "mp4",
                    "output_template": "{stem}_individual",
                },
                tasks=[
                    TaskItem(path=first, media_type="video"),
                    TaskItem(path=second, media_type="video"),
                ],
                output_dir=tmpdir,
                ffmpeg_path=sys.executable,
                include_queue=True,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(any("joined.mp4" in warning for warning in result["warnings"]))

    def test_queue_serialization_preserves_smart_priority_fields(self) -> None:
        manager = QueueManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "clip.mp4"
            source.write_text("video", encoding="utf-8")
            task = TaskItem(
                path=source,
                media_type="video",
                smart_recommendation="краще remux",
                pinned=True,
                priority=3,
            )

            restored = manager.deserialize_tasks([manager.serialize_task(task)])

        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].smart_recommendation, "краще remux")
        self.assertTrue(restored[0].pinned)
        self.assertEqual(restored[0].priority, 3)


if __name__ == "__main__":
    unittest.main()
