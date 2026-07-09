import tempfile
import unittest
from pathlib import Path

from services.settings_manager import SettingsManager


class SettingsManagerTest(unittest.TestCase):
    def test_output_dir_requires_explicit_config_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            manager = SettingsManager(state_path)

            manager.save(
                recent_folders=[],
                watch_folder="",
                output_dir=str(Path(tmpdir) / "out"),
                output_dir_configured=False,
                ffmpeg_path="",
                ui_language="uk",
                last_settings={},
                queue_items=[],
                pending_recovery=False,
            )
            reloaded = SettingsManager(state_path)
            self.assertFalse(reloaded.output_dir_configured())
            self.assertEqual(reloaded.output_dir(), str(Path(tmpdir) / "out"))

            manager.save(
                recent_folders=[],
                watch_folder="",
                output_dir=str(Path(tmpdir) / "out"),
                output_dir_configured=True,
                ffmpeg_path="",
                ui_language="uk",
                last_settings={},
                queue_items=[],
                pending_recovery=False,
            )
            reloaded = SettingsManager(state_path)
            self.assertTrue(reloaded.output_dir_configured())

    def test_notification_settings_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            manager = SettingsManager(state_path)

            self.assertTrue(manager.push_notifications_enabled())
            self.assertFalse(manager.tray_enabled())

            manager.save(
                recent_folders=[],
                watch_folder="",
                output_dir="",
                output_dir_configured=False,
                ffmpeg_path="",
                ui_language="uk",
                last_settings={},
                queue_items=[],
                pending_recovery=False,
                tray_enabled=True,
                push_notifications_enabled=False,
            )

            reloaded = SettingsManager(state_path)
            self.assertTrue(reloaded.tray_enabled())
            self.assertFalse(reloaded.push_notifications_enabled())

    def test_batch_workflow_settings_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            manager = SettingsManager(state_path)

            manager.save(
                recent_folders=[],
                watch_folder="",
                output_dir="",
                output_dir_configured=False,
                ffmpeg_path="",
                ui_language="uk",
                last_settings={},
                queue_items=[],
                pending_recovery=False,
                watch_auto_convert_enabled=True,
                watch_rules_text="Downloads -> mp4",
                scheduler_enabled=True,
                scheduler_mode="idle",
                scheduler_time="01:30",
                scheduler_cpu_limit=35,
                scheduler_gpu_limit=25,
                completion_action="open_output",
                webhook_enabled=True,
                webhook_url="https://example.test/hook",
                discord_webhook_url="https://discord.test/hook",
                telegram_bot_token="123:abc",
                telegram_chat_id="42",
                license_payload={"license_id": "lic-001"},
                trial_started_at=123.5,
                trial_signature="sig-001",
                paid_auto_update_enabled=True,
                paid_update_manifest_url="https://example.test/updates.json",
            )

            reloaded = SettingsManager(state_path)
            self.assertTrue(reloaded.watch_auto_convert_enabled())
            self.assertEqual(reloaded.watch_rules_text(), "Downloads -> mp4")
            self.assertTrue(reloaded.scheduler_enabled())
            self.assertEqual(reloaded.scheduler_mode(), "idle")
            self.assertEqual(reloaded.scheduler_time(), "01:30")
            self.assertEqual(reloaded.scheduler_cpu_limit(), 35)
            self.assertEqual(reloaded.scheduler_gpu_limit(), 25)
            self.assertEqual(reloaded.completion_action(), "open_output")
            self.assertTrue(reloaded.webhook_enabled())
            self.assertEqual(reloaded.webhook_url(), "https://example.test/hook")
            self.assertEqual(reloaded.discord_webhook_url(), "https://discord.test/hook")
            self.assertEqual(reloaded.telegram_bot_token(), "123:abc")
            self.assertEqual(reloaded.telegram_chat_id(), "42")
            self.assertEqual(reloaded.license_payload(), {"license_id": "lic-001"})
            self.assertEqual(reloaded.trial_started_at(), 123.5)
            self.assertEqual(reloaded.trial_signature(), "sig-001")
            self.assertTrue(reloaded.paid_auto_update_enabled())
            self.assertEqual(reloaded.paid_update_manifest_url(), "https://example.test/updates.json")


if __name__ == "__main__":
    unittest.main()
