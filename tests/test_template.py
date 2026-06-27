import unittest
from pathlib import Path

from utils.template import render_template, validate_template


class TemplateTest(unittest.TestCase):
    def test_empty_template_returns_stem(self) -> None:
        result = render_template("", source_path=Path("video.mp4"))
        self.assertEqual(result, "video")

    def test_name_placeholder(self) -> None:
        result = render_template("{name}", source_path=Path("clip.mov"))
        self.assertEqual(result, "clip")

    def test_index_with_padding(self) -> None:
        result = render_template("{index:3}", source_path=Path("a.mp4"), index=5)
        self.assertEqual(result, "005")

    def test_counter_placeholder(self) -> None:
        result = render_template("{counter:4}", source_path=Path("a.mp4"), counter=42)
        self.assertEqual(result, "0042")

    def test_operation_and_type(self) -> None:
        result = render_template(
            "{name}_{operation}_{type}",
            source_path=Path("video.mp4"),
            operation="convert",
            media_type_name="video",
        )
        self.assertEqual(result, "video_convert_video")

    def test_resolution_from_probe(self) -> None:
        result = render_template(
            "{name}_{resolution}",
            source_path=Path("clip.mp4"),
            probe_data={"width": 1920, "height": 1080},
        )
        self.assertEqual(result, "clip_1920x1080")

    def test_parent_placeholder(self) -> None:
        result = render_template("{parent}_{name}", source_path=Path("/videos/2024/clip.mp4"))
        self.assertEqual(result, "2024_clip")

    def test_unknown_placeholder_preserved(self) -> None:
        result = render_template("{name}_{unknown}", source_path=Path("a.mp4"))
        self.assertEqual(result, "a_{unknown}")

    def test_unsafe_chars_sanitized(self) -> None:
        result = render_template("{name}", source_path=Path('te:st<>.mp4'))
        self.assertNotIn(":", result)
        self.assertNotIn("<", result)

    def test_validate_template_valid(self) -> None:
        self.assertIsNone(validate_template("{name}_{index:3}"))

    def test_validate_template_unknown_key(self) -> None:
        error = validate_template("{bogus}")
        self.assertIsNotNone(error)
        self.assertIn("bogus", error)

    def test_validate_empty_is_valid(self) -> None:
        self.assertIsNone(validate_template(""))


if __name__ == "__main__":
    unittest.main()
