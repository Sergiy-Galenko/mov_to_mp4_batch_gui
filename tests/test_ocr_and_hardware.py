import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image, ImageDraw

from app.models import ConversionSettings
from services.ffmpeg_service import FfmpegService
from services.hardware_service import HardwareService
from services.ocr_service import OcrService
from services.whisper_model_manager import WhisperModelManager


def test_ocr_service_synthetic_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        img_path = tmp / "test_scan.png"
        img = Image.new("RGB", (300, 100), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Hello MediaConverter OCR Test", fill=(0, 0, 0))
        d.text((10, 40), "Second line of text here", fill=(0, 0, 0))
        img.save(img_path)

        ocr = OcrService()
        result = ocr.recognize_image(img_path)
        # Even on pure python fallback, it should detect lines or text
        assert len(result) > 0


def test_hardware_service_apple_videotoolbox():
    hw = HardwareService()
    # Mock encoder list returning Apple VideoToolbox encoders
    hw._list_encoders = MagicMock(return_value={"h264_videotoolbox", "hevc_videotoolbox", "prores_videotoolbox", "libx264"})
    caps = hw.detect("ffmpeg")
    assert caps.apple_available is True
    assert "h264_videotoolbox" in caps.videotoolbox_encoders
    assert caps.best_vendor == "apple"
    assert "Apple VideoToolbox" in caps.summary()


def test_two_pass_loudnorm_filter_construction():
    ffmpeg = FfmpegService("ffmpeg", "ffprobe")
    measured = {
        "input_i": "-24.50",
        "input_tp": "-3.20",
        "input_lra": "7.80",
        "input_thresh": "-35.00",
        "target_offset": "-0.50",
    }
    f = ffmpeg.build_two_pass_loudnorm_filter(measured, target_i=-16.0, target_tp=-1.5)
    assert "measured_I=-24.50" in f
    assert "measured_TP=-3.20" in f
    assert "measured_LRA=7.80" in f
    assert "linear=true" in f


def test_build_audio_merge_command():
    ffmpeg = FfmpegService("ffmpeg", "ffprobe")
    settings = ConversionSettings()
    inputs = [Path("a.mp3"), Path("b.mp3")]
    outp = Path("merged.mp3")

    cmd, _list_file = ffmpeg.build_audio_merge_command(inputs, outp, settings, allow_fast_copy=True)
    assert "-c" in cmd
    assert "copy" in cmd
    assert str(outp) in cmd


def test_whisper_model_manager_catalog():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = WhisperModelManager(cache_dir=Path(tmpdir))
        models = mgr.list_models()
        assert len(models) >= 5
        names = [m["name"] for m in models]
        assert "tiny" in names
        assert "base" in names
        assert "small" in names
        assert "large-v3" in names

        devices = mgr.detect_available_devices()
        assert "cpu" in devices
        assert "auto" in devices


def test_whisper_detect_devices_windows(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "platform", "win32")
    devices = WhisperModelManager.detect_available_devices()
    assert "cpu" in devices
    assert "auto" in devices

