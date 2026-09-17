import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models import ConversionSettings
from app.settings import settings_map_to_model
from services import transcription_service as transcription
from services.transcription_service import TranscriptionService


def install_python_whisper(monkeypatch, model):
    load = Mock(return_value=model)
    whisper = SimpleNamespace(load_model=load)

    def writer_for(fmt, folder):
        def write(result, source):
            Path(folder, Path(source).stem + "." + fmt).write_text("WEBVTT\n\nHello", encoding="utf-8")

        return write

    monkeypatch.setitem(sys.modules, "whisper", whisper)
    monkeypatch.setitem(sys.modules, "whisper.utils", SimpleNamespace(get_writer=writer_for))
    return load


@pytest.mark.parametrize("device", ["cpu", "cuda", "mps"])
def test_python_whisper_uses_selected_device_and_managed_cache(tmp_path, monkeypatch, device):
    model = Mock()
    model.to.return_value = model
    model.transcribe.return_value = {"text": "Hello"}
    load = install_python_whisper(monkeypatch, model)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setattr(transcription, "resolve_device", lambda requested, engine: device)
    settings = ConversionSettings(subtitle_engine="whisper", subtitle_device=device, subtitle_model="turbo")
    output = tmp_path / "out.vtt"
    assert TranscriptionService().generate(tmp_path / "input.wav", output, settings) == 0
    assert output.read_text().startswith("WEBVTT")
    load.assert_called_once_with(
        "large-v3-turbo", device="cpu" if device == "mps" else device, download_root=str(tmp_path / "cache" / "whisper")
    )
    assert model.transcribe.call_args.kwargs["fp16"] == (device == "cuda")
    if device == "mps":
        model.alignment_heads.to_dense.assert_called_once()
        model.to.assert_called_once_with("mps")
        assert model.transcribe.call_args.kwargs["word_timestamps"] is False


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_faster_whisper_uses_selected_device_and_cache(tmp_path, monkeypatch, device):
    constructor = Mock()
    constructor.return_value.transcribe.return_value = ([SimpleNamespace(start=0, end=1, text=" Hello ")], None)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=constructor))
    monkeypatch.setattr(transcription, "resolve_device", lambda requested, engine: device)
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hf"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    settings = ConversionSettings(subtitle_engine="faster-whisper", subtitle_device=device)
    output = tmp_path / "out.srt"
    assert TranscriptionService().generate(tmp_path / "input.wav", output, settings) == 0
    assert "Hello" in output.read_text()
    assert constructor.call_args.kwargs["device"] == device
    assert constructor.call_args.kwargs["download_root"] == str(tmp_path / "hf")
    assert constructor.call_args.kwargs["compute_type"] == ("float16" if device == "cuda" else "int8")


def test_inference_failure_keeps_selected_device_and_original_error(tmp_path, monkeypatch):
    model = Mock()
    model.transcribe.side_effect = RuntimeError("CUDA out of memory")
    install_python_whisper(monkeypatch, model)
    monkeypatch.setattr(transcription, "resolve_device", lambda *args: "cuda")
    cli = Mock()
    monkeypatch.setattr(transcription.subprocess, "run", cli)
    with pytest.raises(RuntimeError, match="CUDA out of memory"):
        TranscriptionService().generate(
            tmp_path / "in.wav", tmp_path / "out.srt", ConversionSettings(subtitle_engine="whisper", subtitle_device="cuda")
        )
    cli.assert_not_called()


def test_cli_passes_device_and_model_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(TranscriptionService, "_generate_with_python", lambda *args: False)
    monkeypatch.setattr(TranscriptionService, "_resolve_cli", lambda *args: "whisper")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    commands = []

    def run(cmd, **kwargs):
        commands.append(cmd)
        Path(cmd[cmd.index("--output_dir") + 1], "in.srt").write_text("transcript")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(transcription.subprocess, "run", run)
    TranscriptionService().generate(
        tmp_path / "in.wav", tmp_path / "out.srt", ConversionSettings(subtitle_engine="whisper", subtitle_device="cpu")
    )
    assert commands[0][commands[0].index("--device") + 1] == "cpu"
    assert commands[0][commands[0].index("--model_dir") + 1] == str(tmp_path / "cache" / "whisper")


def test_device_round_trip_through_settings_and_worker_configuration():
    settings = settings_map_to_model({"subtitle_device": "mps", "subtitle_model": "large-v3-turbo"})
    restored = ConversionSettings(**asdict(settings))
    assert restored.subtitle_device == "mps"
    assert restored.subtitle_model == "large-v3-turbo"
    assert settings_map_to_model({"subtitle_device": "invalid"}).subtitle_device == "auto"
    assert settings_map_to_model({"hw": "videotoolbox"}).hw_encoder == "Apple (VideoToolbox)"


def test_managed_worker_receives_configured_ffmpeg_without_changing_parent_environment(tmp_path, monkeypatch):
    import json
    import os

    monkeypatch.setenv("MEDIA_CONVERTER_FFMPEG", "original")
    captured = {}

    def run(command, **kwargs):
        captured.update(kwargs)
        captured["settings"] = json.loads(Path(command[-1]).read_text())
        return SimpleNamespace(returncode=0)

    ffmpeg = str(tmp_path / "custom ffmpeg" / "ffmpeg")
    TranscriptionService().generate_managed(
        tmp_path / "in.wav", tmp_path / "out.srt", ConversionSettings(subtitle_device="mps"), run, ffmpeg
    )
    assert captured["env"]["MEDIA_CONVERTER_FFMPEG"] == ffmpeg
    assert captured["settings"]["subtitle_device"] == "mps"
    assert os.environ["MEDIA_CONVERTER_FFMPEG"] == "original"
