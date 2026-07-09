import tempfile
import unittest
from pathlib import Path

from app.models import TaskItem
from services.batch_workflow_service import BatchWorkflowService


class BatchWorkflowServiceTest(unittest.TestCase):
    def test_folder_rules_apply_media_specific_overrides(self) -> None:
        service = BatchWorkflowService()
        rules = service.parse_rules("Downloads -> mp4\nCamera -> h265 priority=3 pinned\nAudio -> mp3")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            video = root / "Camera" / "clip.mov"
            video.parent.mkdir()
            video.write_text("video", encoding="utf-8")
            audio = root / "Audio" / "voice.wav"
            audio.parent.mkdir()
            audio.write_text("audio", encoding="utf-8")

            video_item = TaskItem(path=video, media_type="video")
            audio_item = TaskItem(path=audio, media_type="audio")

            self.assertTrue(service.apply_rules(video_item, rules))
            self.assertTrue(service.apply_rules(audio_item, rules))

        self.assertEqual(video_item.overrides["codec"], "H.265 (HEVC)")
        self.assertEqual(video_item.overrides["out_video_fmt"], "mp4")
        self.assertEqual(video_item.priority, 3)
        self.assertTrue(video_item.pinned)
        self.assertEqual(audio_item.overrides["out_audio_fmt"], "mp3")

    def test_unknown_rule_lines_are_ignored(self) -> None:
        service = BatchWorkflowService()
        rules = service.parse_rules("bad line\n# comment\nDownloads -> format=mp4 template={stem}_web")

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].match, "Downloads")
        self.assertEqual(rules[0].overrides["out_video_fmt"], "mp4")
        self.assertEqual(rules[0].overrides["output_template"], "{stem}_web")


if __name__ == "__main__":
    unittest.main()
