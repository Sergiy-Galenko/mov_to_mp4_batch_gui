import tempfile
import unittest
from pathlib import Path

from app.models import ConversionSettings, MediaInfo
from services.ffmpeg_service import FfmpegService


class FfmpegServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FfmpegService("/usr/bin/ffmpeg", "/usr/bin/ffprobe")
        self.service.encoder_caps = {"libx264", "libvpx-vp9", "libsvtav1"}

    def test_build_trim_args(self) -> None:
        settings = ConversionSettings(trim_start=5.0, trim_end=10.5)
        self.assertEqual(self.service.build_trim_args(settings), ["-ss", "5.000", "-to", "10.500"])

    def test_video_command_includes_resize_crop_and_metadata(self) -> None:
        settings = ConversionSettings(
            out_video_format="mp4",
            resize_w=1280,
            resize_h=720,
            crop_w=1000,
            crop_h=700,
            crop_x=10,
            crop_y=20,
            copy_metadata=True,
            meta_title="Demo",
            meta_author="Tester",
            video_codec="H.264 (AVC)",
            hw_encoder="Тільки CPU",
        )
        info = MediaInfo(duration=60.0, vcodec="h264", acodec="aac")
        cmd = self.service.build_video_command(Path("/tmp/input.mov"), Path("/tmp/output.mp4"), settings, info, False)
        joined = " ".join(cmd)
        self.assertIn("-vf", cmd)
        self.assertIn("scale=1280:720,crop=1000:700:10:20", joined)
        self.assertIn("-metadata title=Demo", joined)
        self.assertIn("-metadata artist=Tester", joined)
        self.assertIn("-movflags +faststart", joined)
        self.assertIn("-c:v libx264", joined)

    def test_fast_copy_checks_filters_and_container(self) -> None:
        info = MediaInfo(vcodec="h264")
        allowed, reason = self.service.fast_copy_allowed(Path("/tmp/input.mov"), ".mp4", info, False, False)
        self.assertFalse(allowed)
        self.assertIn("Контейнер", reason)

        allowed, reason = self.service.fast_copy_allowed(
            Path("/tmp/input.mov"),
            ".mp4",
            info,
            False,
            False,
            allow_remux=True,
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

        allowed, reason = self.service.fast_copy_allowed(Path("/tmp/input.mp4"), ".mp4", info, True, False)
        self.assertFalse(allowed)
        self.assertIn("фільтри", reason)

        allowed, reason = self.service.fast_copy_allowed(Path("/tmp/input.mp4"), ".mp4", info, False, False)
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_select_encoder_falls_back_to_libx264(self) -> None:
        self.service.encoder_caps = {"libx264"}
        encoder, is_hw = self.service.select_encoder("h265", "cpu")
        self.assertEqual(encoder, "libx264")
        self.assertFalse(is_hw)

    def test_build_merge_command_with_fast_copy(self) -> None:
        settings = ConversionSettings(overwrite=True, out_video_format="mp4", fast_copy=True)
        infos = {
            Path("/tmp/a.mp4"): MediaInfo(vcodec="h264", acodec="aac"),
            Path("/tmp/b.mp4"): MediaInfo(vcodec="h264", acodec="aac"),
        }
        cmd, list_path = self.service.build_merge_command(
            [Path("/tmp/a.mp4"), Path("/tmp/b.mp4")],
            Path("/tmp/out.mp4"),
            settings,
            infos,
            allow_fast_copy=True,
        )
        try:
            self.assertIn("-f", cmd)
            self.assertIn("concat", cmd)
            self.assertIn("-c", cmd)
            self.assertIn("copy", cmd)
            self.assertTrue(Path(list_path).exists())
        finally:
            Path(list_path).unlink(missing_ok=True)

    def test_build_specialized_commands(self) -> None:
        audio_settings = ConversionSettings(operation="audio_only", out_audio_format="mp3", audio_bitrate="128k")
        audio_cmd = self.service.build_audio_command(Path("/tmp/input.mp4"), Path("/tmp/output.mp3"), audio_settings)
        self.assertIn("-vn", audio_cmd)
        self.assertIn("libmp3lame", audio_cmd)

        subtitle_settings = ConversionSettings(operation="subtitle_extract", out_subtitle_format="srt", subtitle_stream=1)
        subtitle_cmd = self.service.build_subtitle_extract_command(
            Path("/tmp/input.mkv"),
            Path("/tmp/output.srt"),
            subtitle_settings,
        )
        self.assertIn("0:s:1?", subtitle_cmd)
        self.assertIn("srt", subtitle_cmd)

        subtitle_file_cmd = self.service.build_subtitle_file_command(
            Path("/tmp/input.srt"),
            Path("/tmp/output.vtt"),
            subtitle_settings,
        )
        self.assertIn("webvtt", subtitle_file_cmd)

        thumb_settings = ConversionSettings(operation="thumbnail", thumbnail_time=12.0)
        thumb_cmd = self.service.build_thumbnail_command(Path("/tmp/input.mp4"), Path("/tmp/output.jpg"), thumb_settings)
        self.assertIn("-frames:v", thumb_cmd)
        self.assertIn("1", thumb_cmd)

        sheet_settings = ConversionSettings(operation="contact_sheet", contact_sheet_cols=3, contact_sheet_rows=2, contact_sheet_width=200, contact_sheet_interval=15)
        sheet_cmd = self.service.build_contact_sheet_command(Path("/tmp/input.mp4"), Path("/tmp/output.jpg"), sheet_settings)
        self.assertIn("tile=3x2", " ".join(sheet_cmd))
        self.assertIn("fps=1/15", " ".join(sheet_cmd))

    def test_build_audio_filter_supports_normalize_peak_and_silence_trim(self) -> None:
        settings = ConversionSettings(
            normalize_audio="ebu_r128",
            audio_peak_limit_db=-1.0,
            trim_silence=True,
            silence_threshold_db=-42,
            silence_duration=0.5,
            speed=1.25,
        )
        audio_filter = self.service.build_audio_filter(settings)
        assert audio_filter is not None
        self.assertIn("atempo=", audio_filter)
        self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11", audio_filter)
        self.assertIn("alimiter=limit=", audio_filter)
        self.assertIn("silenceremove=", audio_filter)

    def test_video_command_can_replace_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            replace_audio = tmp / "music.wav"
            replace_audio.write_text("audio", encoding="utf-8")
            settings = ConversionSettings(replace_audio_path=str(replace_audio), out_video_format="mp4")
            cmd = self.service.build_video_command(
                Path("/tmp/input.mp4"),
                Path("/tmp/output.mp4"),
                settings,
                MediaInfo(vcodec="h264", acodec="aac"),
                allow_fast_copy=False,
            )
            joined = " ".join(cmd)
            self.assertIn(str(replace_audio), joined)
            self.assertIn("-shortest", cmd)
            self.assertIn("-map", cmd)

    def test_audio_command_supports_cover_art_and_track_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cover = tmp / "cover.jpg"
            cover.write_text("cover", encoding="utf-8")
            settings = ConversionSettings(
                operation="audio_only",
                out_audio_format="mp3",
                cover_art_path=str(cover),
                audio_track_index=1,
            )
            cmd = self.service.build_audio_command(Path("/tmp/input.mp4"), Path("/tmp/output.mp3"), settings)
            joined = " ".join(cmd)
            self.assertIn("0:a:1?", joined)
            self.assertIn(str(cover), joined)
            self.assertIn("attached_pic", joined)

    def test_fast_copy_video_command_respects_selected_audio_track(self) -> None:
        settings = ConversionSettings(out_video_format="mp4", audio_track_index=1)
        cmd = self.service.build_video_command(
            Path("/tmp/input.mp4"),
            Path("/tmp/output.mp4"),
            settings,
            MediaInfo(vcodec="h264", acodec="aac"),
            allow_fast_copy=True,
        )
        joined = " ".join(cmd)
        self.assertIn("0:a:1?", joined)
        self.assertIn("-c copy", joined)

    def test_video_command_supports_privacy_editor_filters_and_audio_codec(self) -> None:
        settings = ConversionSettings(
            out_video_format="mkv",
            video_codec="H.264 (AVC)",
            hw_encoder="cpu",
            privacy_blur_regions="10:20:30:40",
            editor_deinterlace=True,
            editor_stabilize=True,
            editor_denoise="hqdn3d",
            editor_brightness=0.1,
            editor_contrast=1.2,
            editor_saturation=0.9,
            editor_gamma=1.1,
            audio_codec="ac3",
            audio_bitrate="384k",
            video_profile="baseline",
        )
        cmd = self.service.build_video_command(
            Path("/tmp/input.mp4"),
            Path("/tmp/output.mkv"),
            settings,
            MediaInfo(vcodec="h264", acodec="aac"),
            allow_fast_copy=False,
        )
        joined = " ".join(cmd)
        self.assertIn("delogo=x=10:y=20:w=30:h=40:show=0", joined)
        self.assertIn("yadif", joined)
        self.assertIn("deshake", joined)
        self.assertIn("hqdn3d", joined)
        self.assertIn("eq=brightness=0.100:contrast=1.200:saturation=0.900:gamma=1.100", joined)
        self.assertIn("-profile:v baseline", joined)
        self.assertIn("-c:a ac3", joined)
        self.assertIn("-b:a 384k", joined)

    def test_subtitle_style_and_sync_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            subtitle = Path(tmpdir) / "input.srt"
            subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
            settings = ConversionSettings(
                subtitle_mode="burn",
                subtitle_path=str(subtitle),
                subtitle_style_enabled=True,
                subtitle_font_name="Arial",
                subtitle_font_size=42,
                subtitle_primary_color="#112233",
                subtitle_outline=3,
                subtitle_shadow=2,
                subtitle_alignment=8,
                subtitle_sync_ms=-250,
            )

            subtitle_filter = self.service.build_subtitle_burn_filter(Path("/tmp/input.mp4"), settings)
            assert subtitle_filter is not None
            self.assertIn("force_style=", subtitle_filter)
            self.assertIn("FontName=Arial", subtitle_filter)
            self.assertIn("PrimaryColour=&H00332211", subtitle_filter)
            self.assertIn("Alignment=8", subtitle_filter)

            cmd = self.service.build_subtitle_file_command(subtitle, Path("/tmp/output.vtt"), settings)
            self.assertIn("-itsoffset", cmd)
            self.assertIn("-0.250", cmd)

    def test_device_codecs_generate_prores_and_mpeg2_commands(self) -> None:
        self.service.encoder_caps = {"prores_ks", "mpeg2video", "libx264"}

        prores = ConversionSettings(out_video_format="mov", video_codec="ProRes", hw_encoder="auto")
        prores_cmd = self.service.build_video_command(
            Path("/tmp/input.mp4"),
            Path("/tmp/output.mov"),
            prores,
            MediaInfo(vcodec="h264", acodec="aac"),
            allow_fast_copy=False,
        )
        self.assertIn("-c:v prores_ks", " ".join(prores_cmd))
        self.assertIn("yuv422p10le", prores_cmd)
        self.assertIn("-profile:v 3", " ".join(prores_cmd))

        dvd = ConversionSettings(out_video_format="mpg", video_codec="MPEG-2", audio_codec="ac3", audio_bitrate="192k")
        dvd_cmd = self.service.build_video_command(
            Path("/tmp/input.mp4"),
            Path("/tmp/output.mpg"),
            dvd,
            MediaInfo(vcodec="h264", acodec="aac"),
            allow_fast_copy=False,
        )
        joined = " ".join(dvd_cmd)
        self.assertIn("-c:v mpeg2video", joined)
        self.assertIn("-q:v", dvd_cmd)
        self.assertIn("-c:a ac3", joined)

    def test_two_pass_and_quality_commands_are_built(self) -> None:
        final_cmd = ["ffmpeg", "-i", "in.mp4", "-c:v", "libx264", "-b:v", "1200k", "out.mp4"]
        pass1, pass2 = self.service.build_two_pass_commands(final_cmd, Path("/tmp/passlog"))
        self.assertIn("-pass", pass1)
        self.assertIn("1", pass1)
        self.assertIn("-f", pass1)
        self.assertIn("null", pass1)
        self.assertEqual(pass2[-1], "out.mp4")
        self.assertIn("2", pass2)

        integrity = self.service.build_integrity_check_command(Path("/tmp/out.mp4"))
        self.assertIn("-f", integrity)
        self.assertIn("null", integrity)

        ssim = " ".join(self.service.build_quality_metric_command(Path("/tmp/in.mp4"), Path("/tmp/out.mp4"), "ssim"))
        self.assertIn("ssim", ssim)
        vmaf = " ".join(self.service.build_quality_metric_command(Path("/tmp/in.mp4"), Path("/tmp/out.mp4"), "vmaf"))
        self.assertIn("libvmaf", vmaf)

    def test_source_matches_codec_choice(self) -> None:
        self.assertTrue(self.service.source_matches_codec_choice(MediaInfo(vcodec="h264"), "H.264 (AVC)", ".mp4"))
        self.assertFalse(self.service.source_matches_codec_choice(MediaInfo(vcodec="hevc"), "H.264 (AVC)", ".mp4"))


if __name__ == "__main__":
    unittest.main()
