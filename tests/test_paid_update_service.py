import json
import tempfile
import unittest
from pathlib import Path

from services.paid_update_service import PaidUpdateService


class PaidUpdateServiceTest(unittest.TestCase):
    def test_file_manifest_reports_available_paid_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "updates.json"
            manifest.write_text(
                json.dumps({"version": "9.9.0", "download_url": "https://example.test/app.exe"}),
                encoding="utf-8",
            )

            info = PaidUpdateService().check(manifest.resolve().as_uri(), "1.0.0")

        self.assertTrue(info.checked)
        self.assertTrue(info.available)
        self.assertEqual(info.latest_version, "9.9.0")
        self.assertEqual(info.download_url, "https://example.test/app.exe")

    def test_missing_manifest_url_returns_actionable_status(self) -> None:
        info = PaidUpdateService().check("", "1.0.0")

        self.assertTrue(info.checked)
        self.assertFalse(info.available)
        self.assertIn("manifest URL", info.message)

    def test_version_comparison_handles_suffixes(self) -> None:
        service = PaidUpdateService()

        self.assertGreater(service._version_tuple("2.0.0-paid"), service._version_tuple("1.9.9"))
        self.assertEqual(service._version_tuple("1.0.0"), service._version_tuple("1.0.0"))


if __name__ == "__main__":
    unittest.main()
