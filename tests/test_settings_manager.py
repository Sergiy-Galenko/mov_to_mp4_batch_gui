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


if __name__ == "__main__":
    unittest.main()
