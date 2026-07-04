import unittest
from pathlib import Path

from app.models import ConversionSettings, MediaInfo
from services.smart_convert_service import apply_smart_settings, classify_content, parse_ab_crfs, recommend_settings


class SmartConvertServiceTest(unittest.TestCase):
    def test_classifies_content_from_name_and_media_info(self) -> None:
        self.assertEqual(classify_content(None, Path("anime_clip.mp4")), "animation")
        self.assertEqual(classify_content(MediaInfo(width=1920, height=1080, fps=30, frame_rate_mode="CFR")), "screencast")
        self.assertEqual(classify_content(MediaInfo(width=1920, height=1080, fps=60)), "live_action")

    def test_recommends_codec_crf_and_preset(self) -> None:
        settings = ConversionSettings(smart_convert_enabled=True, smart_quality_target="quality")
        rec = recommend_settings(settings, MediaInfo(width=3840, height=2160, dynamic_range="HDR"), Path("video.mov"))

        self.assertEqual(rec.video_codec, "H.265 (HEVC)")
        self.assertEqual(rec.preset, "slow")
        self.assertLessEqual(rec.crf, 19)

    def test_apply_smart_settings_only_for_video_when_enabled(self) -> None:
        settings = ConversionSettings(smart_convert_enabled=True, smart_quality_target="small")
        smart = apply_smart_settings(settings, MediaInfo(width=1280, height=720, fps=12), media_type="video", source_path=Path("toon.mp4"))
        self.assertNotEqual(smart.crf, settings.crf)
        self.assertTrue(smart.fast_copy)

        audio = apply_smart_settings(settings, None, media_type="audio")
        self.assertEqual(audio, settings)

    def test_parse_ab_crfs(self) -> None:
        self.assertEqual(parse_ab_crfs("18, 23; 28, bad, 99, 23"), [18, 23, 28])


if __name__ == "__main__":
    unittest.main()
