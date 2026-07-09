import json
import tempfile
import unittest
from pathlib import Path

from services.license_service import DEFAULT_LICENSE_FEATURES, LicenseService


class LicenseServiceTest(unittest.TestCase):
    def test_license_key_activation_enables_commercial_features(self) -> None:
        service = LicenseService(secret="test-secret", now_func=lambda: 1_700_000_000.0)
        package = service.create_license_package(
            holder="Acme Studio",
            expires_at="2099-12-31",
            license_id="lic-001",
        )

        payload = service.activate_key(service.encode_license_key(package))
        info = service.info_from_state({"license_payload": payload})

        self.assertEqual(info.status, "licensed")
        self.assertEqual(info.holder, "Acme Studio")
        self.assertEqual(info.license_id, "lic-001")
        self.assertTrue(info.pro_enabled)
        self.assertTrue(info.commercial_export_allowed)
        self.assertIn("ai_blur", info.features)
        self.assertEqual(payload["source"], "key")

    def test_offline_license_file_is_verified(self) -> None:
        service = LicenseService(secret="test-secret", now_func=lambda: 1_700_000_000.0)
        package = service.create_license_package(holder="Offline Customer", license_id="offline-001")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "license.json"
            path.write_text(json.dumps(package), encoding="utf-8")

            payload = service.load_offline_file(path)

        self.assertEqual(payload["source"], "offline")
        self.assertEqual(payload["license_id"], "offline-001")

    def test_tampered_or_expired_license_is_rejected(self) -> None:
        service = LicenseService(secret="test-secret", now_func=lambda: 1_700_000_000.0)
        package = service.create_license_package(holder="Acme Studio")
        package["holder"] = "Changed"

        with self.assertRaises(ValueError):
            service.activate_key(service.encode_license_key(package))

        expired = service.create_license_package(holder="Old Customer", expires_at="2000-01-01")
        with self.assertRaises(ValueError):
            service.activate_key(service.encode_license_key(expired))

    def test_trial_mode_exposes_pro_features_until_expiry(self) -> None:
        started_at = 1_000.0
        service = LicenseService(secret="test-secret", now_func=lambda: started_at)

        updated = service.start_trial({})
        info = service.info_from_state(updated)

        self.assertEqual(updated["trial_started_at"], started_at)
        self.assertEqual(info.status, "trial")
        self.assertTrue(info.pro_enabled)
        self.assertFalse(info.commercial_export_allowed)
        self.assertEqual(set(info.features), set(DEFAULT_LICENSE_FEATURES))
        self.assertEqual(service.trial_days_remaining(started_at), 14)

        expired_service = LicenseService(secret="test-secret", now_func=lambda: started_at + 15 * 86400)
        expired_info = expired_service.info_from_state({"trial_started_at": started_at})
        self.assertEqual(expired_info.status, "trial_expired")
        self.assertFalse(expired_info.pro_enabled)


if __name__ == "__main__":
    unittest.main()
