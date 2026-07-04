import unittest

from app.models import ConversionSettings
from app.settings import settings_map_to_model


class SettingsTest(unittest.TestCase):
    def test_explicit_video_settings_override_performance_profile(self) -> None:
        settings = settings_map_to_model(
            {
                "performance_profile": "Balanced",
                "codec": "VP9 (WebM)",
                "hw": "cpu",
                "crf": 17,
                "preset": "veryslow",
            },
            defaults=ConversionSettings(),
        )

        self.assertEqual(settings.video_codec, "VP9 (WebM)")
        self.assertEqual(settings.hw_encoder, "cpu")
        self.assertEqual(settings.crf, 17)
        self.assertEqual(settings.preset, "veryslow")

    def test_profile_still_supplies_defaults_when_fields_are_missing(self) -> None:
        settings = settings_map_to_model(
            {"performance_profile": "Small file"},
            defaults=ConversionSettings(),
        )

        self.assertEqual(settings.video_codec, "H.265 (HEVC)")
        self.assertEqual(settings.hw_encoder, "auto")
        self.assertEqual(settings.crf, 28)
        self.assertEqual(settings.preset, "slow")


if __name__ == "__main__":
    unittest.main()
