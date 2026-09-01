from __future__ import annotations

import unittest
from pathlib import Path

from app.models import ConversionSettings, MediaInfo
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from services.taskbar_service import TaskbarService
from services.theme_manager import ThemeManager
from services.transcription_service import TranscriptionService
from utils.files import render_output_stem


class Version2UpgradesTest(unittest.TestCase):
    def test_render_output_stem_rich_tokens(self) -> None:
        path = Path("/files/video_sample.mov")
        info = MediaInfo(
            width=1920,
            height=1080,
            vcodec="h264",
            acodec="aac",
            duration=90.5,
            fps=60.0,
        )
        stem = render_output_stem(
            "{name}_{res}_{vcodec}_{fps}_{dur}",
            path,
            index=1,
            operation="convert",
            media_type_name="video",
            info=info,
        )
        self.assertEqual(stem, "video_sample_1080p_h264_60fps_90s")

    def test_gpu_encoder_detection_and_fallback(self) -> None:
        self.assertTrue(FfmpegService.is_gpu_encoder("h264_nvenc"))
        self.assertTrue(FfmpegService.is_gpu_encoder("hevc_qsv"))
        self.assertFalse(FfmpegService.is_gpu_encoder("libx264"))
        self.assertEqual(FfmpegService.get_cpu_fallback_encoder("h264_nvenc"), "libx264")
        self.assertEqual(FfmpegService.get_cpu_fallback_encoder("hevc_aof"), "libx265")

    def test_create_cpu_fallback_command(self) -> None:
        ffmpeg = FfmpegService("ffmpeg", "ffprobe")
        srv = ConverterService(ffmpeg, None, None)
        cmd = ["ffmpeg", "-i", "in.mp4", "-c:v", "h264_nvenc", "-gpu", "0", "out.mp4"]
        fallback = srv._create_cpu_fallback_command(cmd)
        self.assertIsNotNone(fallback)
        self.assertIn("libx264", fallback)
        self.assertNotIn("h264_nvenc", fallback)
        self.assertNotIn("-gpu", fallback)

    def test_theme_modes(self) -> None:
        tm = ThemeManager(Path("scratch_theme.json"))
        tm.set_theme_mode("obsidian")
        self.assertEqual(tm.theme_mode(), "obsidian")
        tm.set_theme_mode("oled")
        self.assertEqual(tm.theme_mode(), "oled")
        tm.set_queue_view_mode("grid")
        self.assertEqual(tm.queue_view_mode(), "grid")
        if Path("scratch_theme.json").exists():
            Path("scratch_theme.json").unlink(missing_ok=True)

    def test_taskbar_service_states_safety(self) -> None:
        tb = TaskbarService(None)
        tb.set_running_progress(0.75)
        tb.set_paused()
        tb.set_error()
        tb.clear_progress()

    def test_transcription_service_format(self) -> None:
        ts = TranscriptionService()
        settings = ConversionSettings(out_subtitle_format="vtt")
        fmt = ts._resolve_format(settings, Path("out.vtt"))
        self.assertEqual(fmt, "vtt")


if __name__ == '__main_':
    unittest.main()
