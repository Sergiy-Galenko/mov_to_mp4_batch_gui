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

    def test_device_profile_applies_container_video_and_audio_defaults(self) -> None:
        settings = settings_map_to_model(
            {
                "device_profile": "Samsung TV",
                "performance_profile": "Balanced",
                "codec": "VP9 (WebM)",
                "audio_codec": "aac",
            },
            defaults=ConversionSettings(),
        )

        self.assertEqual(settings.device_profile, "Samsung TV")
        self.assertEqual(settings.out_video_format, "mkv")
        self.assertEqual(settings.video_codec, "H.264 (AVC)")
        self.assertEqual(settings.audio_codec, "ac3")
        self.assertEqual(settings.audio_bitrate, "384k")

        android = settings_map_to_model(
            {"device_profile": "Android H.264 baseline"},
            defaults=ConversionSettings(),
        )
        self.assertEqual(android.video_profile, "baseline")

    def test_extended_settings_are_parsed_and_clamped(self) -> None:
        settings = settings_map_to_model(
            {
                "sanitize_metadata": True,
                "commercial_export": True,
                "checksum_algorithm": "SHA256",
                "secure_delete_original": "true",
                "privacy_blur_regions": "10:20:30:40",
                "ai_blur_enabled": "1",
                "subtitle_sync_ms": "-250",
                "subtitle_style_enabled": "1",
                "subtitle_font_size": "500",
                "subtitle_alignment": "12",
                "editor_deinterlace": True,
                "editor_stabilize": True,
                "editor_denoise": "nlmeans",
                "editor_brightness": "-0.2",
                "editor_contrast": "1.25",
                "video_profile": "high",
                "smart_convert_enabled": True,
                "smart_content_type": "screencast",
                "smart_quality_target": "quality",
                "smart_reencode_detection": False,
                "smart_two_pass": True,
                "smart_integrity_check": True,
                "smart_quality_metric": "ssim",
                "smart_ab_test": True,
                "smart_ab_crfs": "18,22,26",
                "smart_ab_duration": "12",
                "cloud_upload_enabled": "yes",
                "cloud_provider": "Dropbox",
                "cloud_rclone_path": "C:/Tools/rclone.exe",
                "cloud_remote_path": "dropbox:converted",
            },
            defaults=ConversionSettings(),
        )

        self.assertTrue(settings.strip_metadata)
        self.assertTrue(settings.commercial_export)
        self.assertEqual(settings.checksum_algorithm, "sha256")
        self.assertTrue(settings.secure_delete_original)
        self.assertEqual(settings.privacy_blur_regions, "10:20:30:40")
        self.assertTrue(settings.ai_blur_enabled)
        self.assertEqual(settings.subtitle_sync_ms, -250)
        self.assertTrue(settings.subtitle_style_enabled)
        self.assertEqual(settings.subtitle_font_size, 200)
        self.assertEqual(settings.subtitle_alignment, 9)
        self.assertTrue(settings.editor_deinterlace)
        self.assertTrue(settings.editor_stabilize)
        self.assertEqual(settings.editor_denoise, "nlmeans")
        self.assertEqual(settings.editor_brightness, -0.2)
        self.assertEqual(settings.editor_contrast, 1.25)
        self.assertEqual(settings.video_profile, "high")
        self.assertTrue(settings.smart_convert_enabled)
        self.assertEqual(settings.smart_content_type, "screencast")
        self.assertEqual(settings.smart_quality_target, "quality")
        self.assertFalse(settings.smart_reencode_detection)
        self.assertTrue(settings.smart_two_pass)
        self.assertTrue(settings.smart_integrity_check)
        self.assertEqual(settings.smart_quality_metric, "ssim")
        self.assertTrue(settings.smart_ab_test)
        self.assertEqual(settings.smart_ab_crfs, "18,22,26")
        self.assertEqual(settings.smart_ab_duration, 12)
        self.assertTrue(settings.cloud_upload_enabled)
        self.assertEqual(settings.cloud_provider, "Dropbox")
        self.assertEqual(settings.cloud_rclone_path, "C:/Tools/rclone.exe")
        self.assertEqual(settings.cloud_remote_path, "dropbox:converted")


if __name__ == "__main__":
    unittest.main()
