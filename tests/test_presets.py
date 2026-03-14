import unittest

from core.presets import DEFAULT_PRESETS


class PresetsTest(unittest.TestCase):
    def test_platform_presets_exist(self) -> None:
        expected = {
            "YouTube • 1080p H.264",
            "TikTok • 9:16",
            "Instagram Reels • 9:16",
            "Instagram Stories • 9:16",
            "Telegram • Compact MP4",
            "WhatsApp • Share MP4",
        }
        self.assertTrue(expected.issubset(DEFAULT_PRESETS.keys()))


if __name__ == "__main__":
    unittest.main()
