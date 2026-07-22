import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.media_preview_service import MediaPreviewService


class MediaPreviewServiceTest(unittest.TestCase):
    def test_video_preview_reuses_its_duration_for_thumbnail_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            video = root / "clip.mp4"
            video.write_bytes(b"video")
            with patch("services.media_preview_service.PREVIEW_CACHE_DIR", root / "previews"):
                service = MediaPreviewService("ffmpeg", "ffprobe")

                def write_thumbnail(command, **_kwargs) -> None:
                    Path(command[-1]).write_bytes(b"thumbnail")

                with (
                    patch.object(service, "_get_duration", return_value=12.5) as get_duration,
                    patch("services.media_preview_service.subprocess.run", side_effect=write_thumbnail),
                ):
                    preview = service.generate_preview(video, "video")
                thumbnails_exist = all(Path(path).is_file() for path in preview["paths"])

        self.assertEqual(preview["type"], "thumbnails")
        self.assertEqual(preview["duration"], 12.5)
        self.assertEqual(len(preview["paths"]), 8)
        self.assertTrue(thumbnails_exist)
        get_duration.assert_called_once_with(video)


if __name__ == "__main__":
    unittest.main()
