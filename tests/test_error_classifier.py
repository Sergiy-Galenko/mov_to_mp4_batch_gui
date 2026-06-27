import unittest

from utils.error_classifier import classify_error, classify_stderr_block, error_summary


class ErrorClassifierTest(unittest.TestCase):
    def test_file_not_found(self) -> None:
        cls = classify_error("input.mp4: No such file or directory")
        self.assertEqual(cls.category, "file")
        self.assertIn("не знайдено", cls.message)

    def test_permission_denied(self) -> None:
        cls = classify_error("output.mp4: Permission denied")
        self.assertEqual(cls.category, "permission")

    def test_nvenc_error(self) -> None:
        cls = classify_error("Error initializing nvenc encoder: unavailable")
        self.assertEqual(cls.category, "hardware")
        self.assertIn("NVENC", cls.message)

    def test_qsv_error(self) -> None:
        cls = classify_error("qsv encoder not found")
        self.assertEqual(cls.category, "hardware")
        self.assertIn("QSV", cls.message)

    def test_moov_atom(self) -> None:
        cls = classify_error("[mov,mp4] moov atom not found")
        self.assertEqual(cls.category, "format")

    def test_out_of_memory(self) -> None:
        cls = classify_error("Cannot allocate memory")
        self.assertEqual(cls.category, "memory")

    def test_no_space(self) -> None:
        cls = classify_error("No space left on device")
        self.assertEqual(cls.category, "disk")

    def test_unknown_error(self) -> None:
        cls = classify_error("some random log line")
        self.assertEqual(cls.category, "unknown")

    def test_empty_input(self) -> None:
        cls = classify_error("")
        self.assertEqual(cls.category, "unknown")

    def test_multi_line_block(self) -> None:
        block = "frame=0 fps=0\nError: No such file or directory\nConversion failed"
        results = classify_stderr_block(block)
        categories = {r.category for r in results}
        self.assertIn("file", categories)

    def test_error_summary(self) -> None:
        summary = error_summary("input.mp4: No such file or directory")
        self.assertIn("не знайдено", summary)

    def test_subtitle_error(self) -> None:
        cls = classify_error("Cannot open subtitle.srt")
        self.assertEqual(cls.category, "subtitle")

    def test_unknown_encoder(self) -> None:
        cls = classify_error("Unknown encoder 'libx999'")
        self.assertEqual(cls.category, "codec")


if __name__ == "__main__":
    unittest.main()
