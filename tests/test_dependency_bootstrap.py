import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from app import dependency_bootstrap as bootstrap
from app.install_lock import install_lock


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    path = tmp_path / "requirements.txt"
    path.write_text("yt-dlp>=2025.1,<2027\n", encoding="utf-8")
    monkeypatch.delenv("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", raising=False)
    monkeypatch.delenv("MEDIA_CONVERTER_AUTO_INSTALL_DEPS", raising=False)
    monkeypatch.setattr(bootstrap.sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(bootstrap, "missing_runtime_dependencies", Mock(return_value=["yt-dlp"]))
    return path


def test_import_map_and_required_versions(tmp_path, monkeypatch):
    path = tmp_path / "requirements.txt"
    path.write_text("# runtime\nPySide6>=6.9,<7\nyt-dlp>=2025.1\npsutil>=5.9\ndefusedxml>=0.7\n")
    monkeypatch.setattr(
        bootstrap.importlib.util, "find_spec", lambda name: object() if name in {"PySide6", "psutil", "defusedxml"} else None
    )
    monkeypatch.setattr(
        bootstrap.importlib.metadata, "version", lambda name: {"PySide6": "6.8.3", "psutil": "6.1.0", "defusedxml": "0.7.1"}[name]
    )
    assert bootstrap.missing_runtime_dependencies(path) == ["PySide6", "yt-dlp"]


@pytest.mark.parametrize(
    "version,bounds,expected",
    [
        ("6.9", ">=6.9,<7", True),
        ("7", ">=6.9,<7", False),
        ("6.10.1", ">=6.9,<7", True),
        ("6.9.0rc1", ">=6.9,<7", False),
        ("2026.1.4", ">=2025.1,<2027", True),
    ],
)
def test_version_bounds(version, bounds, expected):
    assert bootstrap.compatible_version(version, bounds) is expected


def test_missing_requirements_is_an_error(tmp_path):
    with pytest.raises(bootstrap.DependencyBootstrapError, match="missing"):
        bootstrap.missing_runtime_dependencies(tmp_path / "missing.txt")


def test_default_install_uses_requirements_and_verifies_afterward(runtime, monkeypatch):
    process = Mock()
    probe = Mock(side_effect=[["yt-dlp"], []])
    monkeypatch.setattr(bootstrap, "probe_runtime", probe)
    result = bootstrap.prepare_runtime(runtime, process)
    assert result.installed == ["yt-dlp"]
    install = next(call.args[0] for call in process.run.call_args_list if "install" in call.args[0])
    assert install[0] == sys.executable
    assert install[-2:] == ["-r", str(runtime)]
    assert "--upgrade" not in install
    assert "--break-system-packages" not in install
    assert probe.call_count == 2


def test_system_python_installs_only_into_managed_environment(runtime, monkeypatch, tmp_path):
    from app import paths

    monkeypatch.setattr(paths, "APP_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(bootstrap.sys, "prefix", bootstrap.sys.base_prefix)
    monkeypatch.setattr(bootstrap, "probe_runtime", Mock(side_effect=[["yt-dlp"], []]))
    process = Mock()
    result = bootstrap.prepare_runtime(runtime, process)
    assert Path(result.python).is_relative_to(tmp_path / "data")
    assert result.python != sys.executable
    assert process.run.call_args_list[0].args[0][1:3] == ["-m", "venv"]
    install = next(call.args[0] for call in process.run.call_args_list if "install" in call.args[0])
    assert install[0] == result.python


def test_second_instance_rechecks_environment_after_obtaining_lock(runtime, monkeypatch):
    monkeypatch.setattr(bootstrap, "probe_runtime", Mock(return_value=[]))
    process = Mock()
    result = bootstrap.prepare_runtime(runtime, process)
    assert result.installed == []
    process.run.assert_not_called()


def test_ready_environment_does_not_run_pip_or_contact_network(runtime, monkeypatch):
    monkeypatch.setattr(bootstrap, "missing_runtime_dependencies", Mock(return_value=[]))
    process = Mock()
    assert bootstrap.prepare_runtime(runtime, process).installed == []
    process.run.assert_not_called()


def test_failed_verification_never_reports_ready(runtime, monkeypatch):
    monkeypatch.setattr(bootstrap, "probe_runtime", Mock(return_value=["yt-dlp"]))
    with pytest.raises(bootstrap.DependencyBootstrapError, match="still missing"):
        bootstrap.prepare_runtime(runtime, Mock())


def test_explicit_disable_and_skip(runtime, monkeypatch):
    monkeypatch.setenv("MEDIA_CONVERTER_AUTO_INSTALL_DEPS", "0")
    with pytest.raises(bootstrap.DependencyBootstrapError, match="disabled"):
        bootstrap.prepare_runtime(runtime, Mock())
    monkeypatch.setenv("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", "1")
    assert bootstrap.prepare_runtime(runtime, Mock()).installed == []


def test_frozen_application_never_runs_exe_as_pip(runtime, monkeypatch):
    monkeypatch.setattr(bootstrap.sys, "frozen", True, raising=False)
    process = Mock()
    with pytest.raises(bootstrap.DependencyBootstrapError, match="bundle is incomplete"):
        bootstrap.prepare_runtime(runtime, process)
    process.run.assert_not_called()


def test_bootstrap_subprocess_streams_progress_and_stops_on_cancel_or_timeout():
    progress = Mock()
    process = bootstrap.BootstrapProcess(progress)
    assert process.run([sys.executable, "-c", "print('package installed')"]).strip() == "package installed"
    progress.assert_called_with("package installed")
    started = time.monotonic()
    with pytest.raises(bootstrap.DependencyBootstrapError, match="timed out"):
        process.run([sys.executable, "-c", "import time; time.sleep(20)"], timeout=0.2)
    assert time.monotonic() - started < 3
    timer = threading.Timer(0.2, process.cancelled.set)
    timer.start()
    with pytest.raises(bootstrap.BootstrapCancelled):
        process.run([sys.executable, "-c", "import time; time.sleep(20)"])
    timer.join()


def test_install_lock_blocks_other_process_and_releases(tmp_path):
    lock = tmp_path / "environment.lock"
    script = "from pathlib import Path; from app.install_lock import install_lock; import sys;\nwith install_lock(Path(sys.argv[1]), timeout=.2): print('acquired')"
    with install_lock(lock):
        result = subprocess.run([sys.executable, "-c", script, str(lock)], capture_output=True, text=True, timeout=5)
        assert result.returncode != 0
        assert "Another Media Converter" in result.stderr
    result = subprocess.run([sys.executable, "-c", script, str(lock)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert "acquired" in result.stdout


def test_install_in_clean_venv_and_second_launch_without_downloads(tmp_path):
    """Exercise real pip with a local wheel: no internet or global environment changes."""
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    with zipfile.ZipFile(wheels / "bootstrap_probe-1.0-py3-none-any.whl", "w") as archive:
        archive.writestr("bootstrap_probe.py", "VALUE = 42\n")
        archive.writestr("bootstrap_probe-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: bootstrap-probe\nVersion: 1.0\n")
        archive.writestr(
            "bootstrap_probe-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )
        archive.writestr("bootstrap_probe-1.0.dist-info/RECORD", "")
    venv = tmp_path / "fresh env"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True, timeout=60)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    path = tmp_path / "requirements.txt"
    path.write_text("bootstrap-probe>=1,<2\n")
    script = (
        "from app.dependency_bootstrap import prepare_runtime; from pathlib import Path; import json,sys; "
        "r=prepare_runtime(Path(sys.argv[1])); print('RESULT='+json.dumps(r.installed)); "
        "import bootstrap_probe; assert bootstrap_probe.VALUE == 42"
    )
    env = dict(
        os.environ,
        PIP_NO_INDEX="1",
        PIP_FIND_LINKS=str(wheels),
        PIP_CONFIG_FILE=os.devnull,
        MEDIA_CONVERTER_AUTO_INSTALL_DEPS="1",
        MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP="0",
    )
    results = []
    for _ in range(2):
        result = subprocess.run([str(python), "-c", script, str(path)], capture_output=True, text=True, env=env, timeout=60)
        assert result.returncode == 0, result.stderr + result.stdout
        results.append(json.loads(next(line[7:] for line in result.stdout.splitlines() if line.startswith("RESULT="))))
    assert results == [["bootstrap-probe"], []]
