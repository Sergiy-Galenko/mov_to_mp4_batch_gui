import json
import tempfile
import unittest
from pathlib import Path

from services.paid_update_service import PaidUpdateService


class PaidUpdateServiceTest(unittest.TestCase):
    def test_file_manifest_reports_available_paid_update(self) -> None:
        service = PaidUpdateService(allow_file_urls=True, manifest_secret="test-secret")
        payload = {"version": "9.9.0", "download_url": "https://example.test/app.exe"}
        payload["manifest_signature"] = service.sign_manifest(payload, "test-secret")
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "updates.json"
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            info = service.check(manifest.resolve().as_uri(), "1.0.0")

        self.assertTrue(info.checked)
        self.assertTrue(info.available)
        self.assertEqual(info.latest_version, "9.9.0")
        self.assertEqual(info.download_url, "https://example.test/app.exe")

    def test_missing_manifest_url_returns_actionable_status(self) -> None:
        info = PaidUpdateService().check("", "1.0.0")

        self.assertTrue(info.checked)
        self.assertFalse(info.available)
        self.assertIn("manifest URL", info.message)

    def test_unsigned_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "updates.json"
            manifest.write_text(json.dumps({"version": "9.9.0"}), encoding="utf-8")

            info = PaidUpdateService(allow_file_urls=True, manifest_secret="test-secret").check(manifest.resolve().as_uri(), "1.0.0")

        self.assertTrue(info.checked)
        self.assertFalse(info.available)
        self.assertIn("signature", info.message)

    def test_non_https_manifest_is_blocked(self) -> None:
        info = PaidUpdateService(manifest_secret="test-secret").check("http://example.test/updates.json", "1.0.0")

        self.assertTrue(info.checked)
        self.assertIn("blocked", info.message)

    def test_version_comparison_handles_suffixes(self) -> None:
        service = PaidUpdateService()

        self.assertGreater(service._version_tuple("2.0.0-paid"), service._version_tuple("1.9.9"))
        self.assertEqual(service._version_tuple("1.0.0"), service._version_tuple("1.0.0"))


if __name__ == "__main__":
    unittest.main()
