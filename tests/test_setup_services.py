import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models import ConversionSettings
from app.settings import settings_map_to_model
from services import system_profile, whisper_environment, whisper_setup, whisper_worker
from services.background_job import BackgroundJob, JobCancelled, JobContext
from services.converter_service import ConverterService
from services.system_profile import GIB, recommend_workload, scan_system


@pytest.mark.parametrize("cpus,total,available,expected", [(8, 8, 4, 1), (16, 32, 25, 4), (8, 64, 40, 2), (32, 64, 3, 1), (1, 2, 1, 1)])
def test_tuning_reserves_cpu_and_memory_and_reaches_converter(cpus, total, available, expected):
    recommendation = recommend_workload(cpus, total, available)
    assert recommendation["concurrency_limit"] == expected
    assert 1 <= recommendation["cpu_load_limit"] < 100
    settings = settings_map_to_model(recommendation)
    assert ConverterService(Mock(), Mock()).conversion_worker_limit(settings) == expected


@pytest.mark.parametrize("system,label", [("Darwin", "macOS"), ("Windows", "Windows"), ("Linux", "Linux")])
def test_scan_reports_os_and_only_working_hardware_encoders(monkeypatch, system, label):
    monkeypatch.setattr(system_profile.platform, "system", lambda: system)
    monkeypatch.setattr(system_profile.psutil, "cpu_count", lambda **kw: 8)
    monkeypatch.setattr(system_profile.psutil, "virtual_memory", lambda: SimpleNamespace(total=8 * GIB, available=5 * GIB))
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        output = ""
        if "-encoders" in command:
            output = " V.... h264_nvenc\n V.... h264_videotoolbox\n V.... prores_videotoolbox"
        elif "-c:v" in command:
            return SimpleNamespace(returncode=0 if "h264_videotoolbox" in command else 1, stdout="", stderr="unsupported")
        elif "sysctl" in command[0]:
            output = "Apple M1"
        elif "system_profiler" in command[0]:
            output = '{"SPDisplaysDataType": [{"sppci_model": "Apple M1"}]}'
        elif "powershell" in command[0]:
            output = '{"cpu": "Intel", "gpu": ["NVIDIA"]}'
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    context = SimpleNamespace(run=run, check=Mock(), progress=Mock())
    result = scan_system(context, "/fake/ffmpeg")
    assert result["os"] == label
    assert result["ram_gib"] == 8
    assert result["encoders"] == ["VideoToolbox H.264"]
    assert "NVENC H.264" not in result["encoders"]
    assert all(command[command.index("-allow_sw") + 1] == "0" for command in commands if "videotoolbox" in " ".join(command) and "-c:v" in command)


def test_scan_missing_ffmpeg_still_returns_useful_profile():
    context = SimpleNamespace(run=Mock(side_effect=OSError("unavailable")), check=Mock(), progress=Mock())
    result = scan_system(context, "")
    assert result["logical_cpus"] >= 1
    assert result["recommendation"]["concurrency_limit"] >= 1
    assert result["warnings"]


def test_job_is_async_and_cancellable(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    gate = threading.Event()
    job = BackgroundJob()
    completed = Mock()
    job.completed.connect(completed)

    def work(context):
        context.progress("devices", 50)
        gate.wait(2)
        context.check()
        return {"ready": True}

    assert job.start_job(work)
    assert job.busy
    assert not job.start_job(work)
    QTest.qWait(20)
    assert job.progress == 50
    job.cancel()
    gate.set()
    for _ in range(50):
        app.processEvents()
        if not job.busy:
            break
        QTest.qWait(10)
    assert job.stage == "cancelled"
    completed.assert_not_called()
    job.shutdown()


def test_process_timeout_and_cancellation_are_bounded():
    context = JobContext(Mock())
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        context.run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)
    assert time.monotonic() - started < 3
    context.cancelled.set()
    with pytest.raises(JobCancelled):
        context.run([sys.executable, "-c", "raise RuntimeError('should not start')"])


def test_installer_uses_isolated_environment_and_fixed_package(tmp_path, monkeypatch):
    monkeypatch.setattr(whisper_setup, "APP_DATA_DIR", tmp_path)
    saved = Mock()
    monkeypatch.setattr(whisper_setup, "save_runtime", saved)
    report = {"engines": {"whisper": {"installed": True, "devices": ["cpu", "mps"], "errors": []}}}
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        text = "WHISPER_RESULT=" + json.dumps(report) if "diagnose" in command else ""
        return subprocess.CompletedProcess(command, 0, text, "")

    context = SimpleNamespace(run=run, progress=Mock(), check=Mock())
    assert whisper_setup.install_runtime(context, "whisper", "/python path/python") == report
    assert commands[0] == ["/python path/python", "-m", "venv", str(tmp_path / "whisper-runtime")]
    assert commands[1][-1] == "openai-whisper>=20250625"
    assert Path(commands[1][0]).is_relative_to(tmp_path)
    saved.assert_called_once()
    with pytest.raises(ValueError, match="Unsupported"):
        whisper_setup.install_runtime(context, "--malicious-option")


def test_failed_install_does_not_activate_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(whisper_setup, "APP_DATA_DIR", tmp_path)
    save = Mock()
    monkeypatch.setattr(whisper_setup, "save_runtime", save)
    context = SimpleNamespace(check=Mock(), progress=Mock(), run=Mock(return_value=subprocess.CompletedProcess([], 1, "", "pip failed")))
    with pytest.raises(RuntimeError, match="pip failed"):
        whisper_setup.install_runtime(context, "whisper")
    save.assert_not_called()


def test_short_recognition_uses_selected_runtime_and_cleans_sample(tmp_path, monkeypatch):
    source = tmp_path / "speech clip.mp4"
    source.touch()
    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, 'WHISPER_RESULT={"text":"Hello", "device":"cpu", "seconds":1}', "")

    context = SimpleNamespace(progress=Mock(), run=run)
    result = whisper_setup.test_recognition(context, str(source), "tiny", "whisper", "cpu", "/my ffmpeg")
    sample = commands[0][0]
    assert sample[0] == "/my ffmpeg"
    assert sample[sample.index("-t") + 1] == "12"
    assert str(source) in sample
    assert commands[1][0][-3:] == ["tiny", "whisper", "cpu"]
    assert commands[1][1]["env"]["MEDIA_CONVERTER_FFMPEG"] == "/my ffmpeg"
    assert not Path(sample[-1]).parent.exists()
    assert result["text"] == "Hello"


def test_recognition_requires_a_downloaded_model(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    with pytest.raises(RuntimeError, match="Download"):
        whisper_worker.recognition_test("speech.wav", "out.txt", "tiny", "whisper", "cpu")


def test_managed_runtime_used_by_converter_and_device_selector(tmp_path, monkeypatch):
    from services import transcription_service, whisper_runtime

    python = tmp_path / "python"
    python.touch()
    monkeypatch.setattr(whisper_environment, "APP_DATA_DIR", tmp_path)
    monkeypatch.delenv("MEDIA_CONVERTER_WHISPER_WORKER", raising=False)
    whisper_environment.save_runtime(str(python), {"engines": {"whisper": {"installed": True, "devices": ["cpu", "mps"]}}})
    assert whisper_runtime.available_devices("whisper") == ["auto", "cpu", "mps"]
    assert whisper_runtime.package_available("whisper")
    run = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    transcription_service.TranscriptionService().generate_managed(tmp_path / "in.wav", tmp_path / "out.srt", ConversionSettings(), run)
    command = run.call_args.args[0]
    assert command[0] == str(python)
    assert "transcribe" in command
    assert run.call_args.kwargs["env"]["MEDIA_CONVERTER_WHISPER_WORKER"] == "1"


def test_diagnostic_worker_can_run_without_qt_or_whisper(tmp_path):
    command = whisper_environment.worker_command("diagnose", python=sys.executable)
    # -S hides site-packages, proving the shipped worker has no Qt dependency.
    command.insert(1, "-S")
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, env=whisper_environment.worker_environment())
    report = whisper_setup.read_worker_result(result)
    assert report["engines"]["whisper"]["installed"] is False


def test_diagnostics_verify_mps_execution_and_preserve_cpu_on_cuda_failure(monkeypatch):
    from services import whisper_runtime

    monkeypatch.setattr(whisper_runtime, "package_available", lambda name: True)

    def tensor(shape, device):
        if device == "mps":
            raise RuntimeError("MPS allocation failed")
        return MockTensor()

    class MockTensor:
        def __matmul__(self, other):
            return self

        def sum(self):
            return self

        def item(self):
            return 64

    def compute_types(device):
        if device == "cuda":
            raise RuntimeError("CUDA driver missing")
        return {"int8"}

    torch = SimpleNamespace(ones=tensor, cuda=SimpleNamespace(is_available=lambda: False),
                            backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "whisper", SimpleNamespace(__version__="test"))
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(__version__="test"))
    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(get_supported_compute_types=compute_types, get_cuda_device_count=lambda: 1))
    report = whisper_worker.diagnose()
    for engine in report["engines"].values():
        assert engine["installed"] is True
        assert engine["devices"] == ["cpu"]
        assert engine["errors"]


def test_workload_preferences_survive_regular_state_save(tmp_path):
    from services.settings_manager import SettingsManager

    manager = SettingsManager(tmp_path / "settings.json")
    manager.state.update(auto_tune_enabled=False, concurrency_limit=3)
    manager.save(recent_folders=[], watch_folder="", output_dir="", output_dir_configured=False,
                 ffmpeg_path="", ui_language="uk", last_settings={}, queue_items=[], pending_recovery=False)
    restored = SettingsManager(manager.path)
    assert restored.state["auto_tune_enabled"] is False
    assert restored.state["concurrency_limit"] == 3


def test_startup_setup_uses_working_engine_without_installing(monkeypatch):
    report = {"engines": {"whisper": {"installed": False}, "faster-whisper": {"installed": True}}}
    monkeypatch.setattr(whisper_setup, "check_runtime", Mock(return_value=report))
    install = Mock()
    monkeypatch.setattr(whisper_setup, "install_runtime", install)
    assert whisper_setup.ensure_runtime(Mock(), "auto") == report
    install.assert_not_called()
    whisper_setup.ensure_runtime(Mock(), "whisper")
    assert install.call_args.args[1] == "whisper"


def test_startup_setup_defaults_to_whisper_and_propagates_failure(monkeypatch):
    monkeypatch.setattr(whisper_setup, "check_runtime", Mock(return_value={"engines": {}}))
    install = Mock(side_effect=RuntimeError("offline"))
    monkeypatch.setattr(whisper_setup, "install_runtime", install)
    with pytest.raises(RuntimeError, match="offline"):
        whisper_setup.ensure_runtime(Mock(), "auto")
    assert install.call_args.args[1] == "whisper"


def test_startup_backend_honours_preference_environment_and_selected_engine(monkeypatch):
    from ui.backend import Backend

    app = QApplication.instance() or QApplication([])
    backend = Backend()
    monkeypatch.setattr(backend, "_save_state", Mock())
    ensure = Mock()
    monkeypatch.setattr(backend._whisper_setup, "ensure", ensure)
    monkeypatch.delenv("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", raising=False)
    monkeypatch.delenv("MEDIA_CONVERTER_AUTO_INSTALL_DEPS", raising=False)
    backend.settings_manager.state["auto_dependency_setup"] = True
    backend._last_settings_map["subtitle_engine"] = "faster-whisper"
    backend.startDependencySetup()
    ensure.assert_called_once_with("faster-whisper")
    ensure.reset_mock()
    backend.autoDependencySetup = False
    backend.startDependencySetup()
    ensure.assert_not_called()
    backend.retryDependencySetup()
    ensure.assert_called_once_with("faster-whisper")
    ensure.reset_mock()
    monkeypatch.setenv("MEDIA_CONVERTER_AUTO_INSTALL_DEPS", "0")
    backend.autoDependencySetup = True
    backend.startDependencySetup()
    ensure.assert_not_called()
    backend.shutdown()
    app.processEvents()
