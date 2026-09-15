import hashlib
import io
import json
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services import whisper_model_manager as manager_module
from services import whisper_runtime
from services.whisper_model_manager import WhisperModelManager, faster_repo


@pytest.fixture
def manager(tmp_path):
    instance = WhisperModelManager(tmp_path)
    yield instance
    instance.shutdown()


def response(payload, length=None):
    stream = io.BytesIO(payload)
    stream.headers = {"Content-Length": str(len(payload) if length is None else length)}
    return stream


def test_verified_download_progress_and_delete(manager, monkeypatch):
    payload = b"model weights" * 100000
    monkeypatch.setitem(manager_module._CHECKSUMS, "tiny", hashlib.sha256(payload).hexdigest())
    fetch = Mock(side_effect=lambda *args, **kwargs: response(payload))
    monkeypatch.setattr(manager_module.urllib.request, "urlopen", fetch)
    events = []
    assert manager.download_model("tiny", lambda pct, message: events.append(pct)).result(timeout=3)
    assert manager.model_path("tiny").read_bytes() == payload
    assert any(0 < value < 1 for value in events)
    assert events[-1] == 1
    assert manager.list_models()[0]["state"] == "ready"
    assert manager.delete_model("tiny")
    assert not manager.is_model_downloaded("tiny")
    assert not list(manager.cache_dir.rglob("*.part"))


@pytest.mark.parametrize("mode", ["checksum", "truncated", "network"])
def test_download_failure_is_visible_and_never_publishes(manager, monkeypatch, mode):
    if mode == "network":
        fetch = Mock(side_effect=OSError("network unavailable"))
    else:
        fetch = Mock(return_value=response(b"bad weights", 99 if mode == "truncated" else None))
    monkeypatch.setattr(manager_module.urllib.request, "urlopen", fetch)
    assert not manager.download_model("tiny").result(timeout=3)
    row = manager.list_models()[0]
    assert row["state"] == "error"
    assert row["error"]
    assert not row["downloaded"]
    assert not list(manager.cache_dir.rglob("*.part"))


def test_cancel_download_excludes_duplicates_and_deletion_then_allows_retry(manager, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    payload = b"test model"
    monkeypatch.setitem(manager_module._CHECKSUMS, "tiny", hashlib.sha256(payload).hexdigest())

    def fetch(*args, **kwargs):
        started.set()
        assert release.wait(3)
        return response(payload)

    monkeypatch.setattr(manager_module.urllib.request, "urlopen", fetch)
    future = manager.download_model("tiny")
    try:
        assert started.wait(3)
        with pytest.raises(RuntimeError):
            manager.download_model("base")
        with pytest.raises(RuntimeError):
            manager.delete_model("tiny")
        manager.cancel_download()
    finally:
        release.set()
    assert not future.result(timeout=3)
    assert manager.list_models()[0]["state"] == "cancelled"
    assert not manager.is_model_downloaded("tiny")
    assert manager.download_model("tiny").result(timeout=3)


def test_shutdown_cancels_without_publishing_or_accepting_more_work(manager, monkeypatch):
    monkeypatch.setattr(manager_module.urllib.request, "urlopen", Mock(side_effect=TimeoutError("timeout")))
    manager.shutdown()
    with pytest.raises(RuntimeError):
        manager.download_model("tiny")


@pytest.mark.parametrize("name", ["../outside", "../../tiny", "/tmp/model", "models/custom", ""])
def test_model_paths_are_restricted_to_catalog(manager, name):
    with pytest.raises(ValueError):
        manager.delete_model(name)
    with pytest.raises(ValueError):
        manager.download_model(name)


def test_faster_cache_requires_complete_snapshot_and_counts_blobs_once(manager):
    repository = manager.get_cache_paths("large-v3-turbo", "faster-whisper")[1]
    assert "mobiuslabsgmbh" in repository.name
    snapshot = repository / "snapshots" / "revision"
    snapshot.mkdir(parents=True)
    (repository / "blobs").mkdir()
    (repository / "blobs" / "unfinished.incomplete").write_bytes(b"partial")
    assert not manager.is_model_downloaded("large-v3-turbo", "faster-whisper")
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.json"):
        blob = repository / "blobs" / name
        blob.write_bytes(b"data")
        (snapshot / name).symlink_to(blob)
    assert manager.model_path("large-v3-turbo", "faster-whisper") == snapshot
    assert not manager.is_model_downloaded("large-v3-turbo", "whisper")
    row = manager.list_models("faster-whisper")[-1]
    assert row["disk_bytes"] == 4 * 4 + 7
    assert manager.delete_model("large-v3-turbo", "faster-whisper")
    assert not repository.exists()


def test_faster_download_uses_pinned_revision_and_atomic_complete_directory(manager, monkeypatch):
    files = {"model.bin": b"weights", "config.json": b"{}", "tokenizer.json": b"{}", "vocabulary.json": b"[]"}
    manifest = {"sha": "abc123", "siblings": [
        {"rfilename": name, "lfs": {"sha256": hashlib.sha256(data).hexdigest()}}
        for name, data in files.items()
    ]}
    urls = []

    def fetch(url, **kwargs):
        urls.append(url)
        return response(json.dumps(manifest).encode() if "/api/" in url else files[url.rsplit("/", 1)[1]])

    monkeypatch.setattr(manager_module.urllib.request, "urlopen", fetch)
    assert manager.download_model("large-v3-turbo", engine="faster-whisper").result(timeout=3)
    assert all("/resolve/abc123/" in url for url in urls[1:])
    assert all(faster_repo("turbo") in url for url in urls)
    assert manager.model_path("turbo", "faster-whisper").joinpath("model.bin").read_bytes() == b"weights"
    assert not list(manager.cache_dir.rglob("*.partial"))


def test_environment_cache_roots_are_shared(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hub"))
    manager = WhisperModelManager()
    try:
        assert manager.get_cache_paths("tiny")[0] == tmp_path / "xdg" / "whisper" / "tiny.pt"
        assert manager.hub_dir == tmp_path / "hub"
    finally:
        manager.shutdown()


def test_devices_follow_runtime_availability_and_engine(monkeypatch):
    monkeypatch.setattr(whisper_runtime, "package_available", lambda name: name == "whisper")
    monkeypatch.setitem(__import__("sys").modules, "torch", SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
    ))
    assert whisper_runtime.available_devices() == ["auto", "cpu", "mps"]
    assert whisper_runtime.resolve_device("auto", "whisper") == "mps"
    with pytest.raises(RuntimeError, match="CUDA"):
        whisper_runtime.resolve_device("cuda", "whisper")
    with pytest.raises(ValueError, match="MPS"):
        whisper_runtime.engine_for("mps", "faster-whisper")
    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", SimpleNamespace(get_cuda_device_count=lambda: 1))
    assert whisper_runtime.available_devices("faster-whisper") == ["auto", "cpu", "cuda"]
    monkeypatch.setitem(__import__("sys").modules, "torch", None)
    assert whisper_runtime.available_devices("whisper") == ["auto", "cpu"]
