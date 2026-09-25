import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QSettings, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from services.telegram_note_service import TelegramNoteService
from ui.backend import Backend


class TestTelegramNoteService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        QQuickStyle.setStyle("Basic")
        cls._app = QApplication.instance() or QApplication([])
        QSettings.setDefaultFormat(QSettings.IniFormat)

    def setUp(self):
        self.backend = Backend()
        self.service = TelegramNoteService(self.backend)

    def tearDown(self):
        self.backend.shutdown()

    def test_backend_has_telegram_note_property(self):
        self.assertIsNotNone(self.backend.telegramNote)
        self.assertIsInstance(self.backend.telegramNote, TelegramNoteService)

    def test_build_render_command_center_crop(self):
        source = Path("/tmp/sample_video.mov")
        target = Path("/tmp/sample_video_note.mp4")
        options = {
            "start_time": 5.0,
            "end_time": 25.0,
            "resolution": 480,
            "crop_mode": "center",
            "bitrate": "1400k",
            "audio_enabled": True,
            "volume_boost": 1.2,
            "burn_circle": False,
        }
        cmd = self.service.build_render_command(source, target, options)

        # Check binary and timing
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-ss", cmd)
        ss_idx = cmd.index("-ss")
        self.assertEqual(cmd[ss_idx + 1], "5.000")
        t_idx = cmd.index("-t")
        self.assertEqual(cmd[t_idx + 1], "20.000")

        # Check video filters: 1:1 square crop & scale to 480:480
        vf_idx = cmd.index("-vf")
        vf = cmd[vf_idx + 1]
        self.assertIn("crop='min(iw,ih)':'min(iw,ih)'", vf)
        self.assertIn("scale=480:480", vf)
        self.assertIn("format=yuv420p", vf)

        # Check codecs and faststart
        self.assertIn("-c:v", cmd)
        cv_idx = cmd.index("-c:v")
        self.assertEqual(cmd[cv_idx + 1], "libx264")
        self.assertIn("-c:a", cmd)
        ca_idx = cmd.index("-c:a")
        self.assertEqual(cmd[ca_idx + 1], "aac")
        self.assertIn("-movflags", cmd)
        mf_idx = cmd.index("-movflags")
        self.assertEqual(cmd[mf_idx + 1], "+faststart")

    def test_build_render_command_blur_pad_and_burn_circle(self):
        source = Path("/tmp/sample_video.mp4")
        target = Path("/tmp/sample_video_note.mp4")
        options = {
            "start_time": 0.0,
            "end_time": 80.0,  # exceeds 60s limit -> should be clamped to 60s
            "resolution": 640,
            "crop_mode": "blur_pad",
            "bitrate": "2000k",
            "audio_enabled": False,
            "burn_circle": True,
        }
        cmd = self.service.build_render_command(source, target, options)

        # Verify max duration is clamped to 60.0s
        t_idx = cmd.index("-t")
        self.assertEqual(cmd[t_idx + 1], "60.000")

        # Check blur_pad split and boxblur
        vf_idx = cmd.index("-vf")
        vf = cmd[vf_idx + 1]
        self.assertIn("boxblur", vf)
        self.assertIn("scale=640:640", vf)
        self.assertIn("geq=lum=", vf)  # burn_circle matte

        # Audio should be disabled
        self.assertIn("-an", cmd)
        self.assertNotIn("-c:a", cmd)

    def test_add_to_queue(self):
        temp_file = Path("/tmp/test_telegram_input.mov")
        temp_file.touch(exist_ok=True)
        try:
            initial_count = self.backend.queue_model.rowCount()
            options = {
                "start_time": 2.0,
                "end_time": 30.0,
                "resolution": 480,
            }
            ok = self.service.addToQueue(str(temp_file), options)
            self.assertTrue(ok)
            self.assertEqual(self.backend.queue_model.rowCount(), initial_count + 1)
            item = self.backend.queue_model.items()[-1]
            self.assertEqual(item.overrides["resolution"], "480x480")
            self.assertEqual(item.overrides["aspect_ratio"], "1:1")
            self.assertEqual(item.overrides["trim_start"], 2.0)
            self.assertEqual(item.overrides["trim_end"], 30.0)
            self.assertTrue(item.overrides["fast_start"])
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_inspect_missing_file(self):
        info = self.service.inspect("/path/to/nonexistent/file.mp4")
        self.assertFalse(info["valid"])
        self.assertEqual(info["duration"], 0.0)
        self.assertEqual(info["width"], 0)

    @patch("subprocess.run")
    def test_inspect_valid_file(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "45.5"}, "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"}, {"codec_type": "audio"}]}',
        )
        fake_file = Path("/tmp/fake_vid.mp4")
        fake_file.touch(exist_ok=True)
        try:
            info = self.service.inspect(str(fake_file))
            self.assertTrue(info["valid"])
            self.assertEqual(info["duration"], 45.5)
            self.assertEqual(info["width"], 1920)
            self.assertEqual(info["height"], 1080)
            self.assertTrue(info["has_audio"])
        finally:
            if fake_file.exists():
                fake_file.unlink()

    def test_qml_telegram_note_screen_loads(self):
        project_root = Path(__file__).resolve().parents[1]
        qml_dir = project_root / "ui" / "qml"
        screen_qml = qml_dir / "screens" / "TelegramNoteScreen.qml"

        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir))
        engine.rootContext().setContextProperty("backend", self.backend)

        component = QQmlComponent(engine, QUrl.fromLocalFile(str(screen_qml)))
        obj = component.create()
        self.assertIsNotNone(
            obj,
            f"TelegramNoteScreen.qml should instantiate without errors: {component.errorString()}",
        )
