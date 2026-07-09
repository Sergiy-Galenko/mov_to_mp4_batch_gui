from types import SimpleNamespace

from app import dependency_bootstrap


def test_missing_runtime_dependencies_uses_requirement_import_map(tmp_path, monkeypatch) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        """
        # comments are ignored
        PySide6>=6.8.1,<7
        yt-dlp>=2025.1
        psutil>=5.9
        """,
        encoding="utf-8",
    )

    def fake_find_spec(name):
        return object() if name == "psutil" else None

    monkeypatch.setattr(dependency_bootstrap.importlib.util, "find_spec", fake_find_spec)

    assert dependency_bootstrap.missing_runtime_dependencies(requirements) == ["PySide6", "yt-dlp"]


def test_ensure_runtime_dependencies_runs_pip_for_missing_packages(tmp_path, monkeypatch) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("yt-dlp>=2025.1\n", encoding="utf-8")
    calls = []
    installed = {"done": False}

    def fake_find_spec(name):
        return object() if installed["done"] else None

    def fake_run(cmd, stdout=None, stderr=None, text=True):
        calls.append(cmd)
        installed["done"] = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dependency_bootstrap.importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(dependency_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setenv("MEDIA_CONVERTER_AUTO_INSTALL_DEPS", "1")

    assert dependency_bootstrap.ensure_runtime_dependencies(requirements) == ["yt-dlp"]
    assert calls and calls[0][-2:] == ["-r", str(requirements.resolve())]


def test_ensure_runtime_dependencies_blocks_auto_install_by_default(tmp_path, monkeypatch) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("yt-dlp>=2025.1\n", encoding="utf-8")

    monkeypatch.setattr(dependency_bootstrap.importlib.util, "find_spec", lambda name: None)

    try:
        dependency_bootstrap.ensure_runtime_dependencies(requirements)
    except dependency_bootstrap.DependencyBootstrapError as exc:
        assert "Missing Python libraries" in str(exc)
    else:
        raise AssertionError("expected dependency bootstrap to be blocked")


def test_ensure_runtime_dependencies_can_be_disabled(tmp_path, monkeypatch) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("yt-dlp>=2025.1\n", encoding="utf-8")

    monkeypatch.setenv("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", "1")
    monkeypatch.setattr(dependency_bootstrap.importlib.util, "find_spec", lambda name: None)

    assert dependency_bootstrap.ensure_runtime_dependencies(requirements) == []
