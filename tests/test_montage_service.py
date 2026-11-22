from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models import TaskItem, TaskStatus
from services.montage_service import MontageService, MontageSession, MontageSessionStore
from ui.backend import Backend


def test_montage_session_dataclass():
    session = MontageSession(
        file_path="/tmp/test.mp4",
        in_point=5.0,
        out_point=15.0,
        crop_x=10,
        crop_y=20,
        crop_w=800,
        crop_h=600,
        crop_aspect="4:3",
        audio_enabled=False,
        output_format="mkv",
    )
    d = session.to_dict()
    assert d["in_point"] == 5.0
    assert d["out_point"] == 15.0
    assert d["crop_w"] == 800
    assert d["audio_enabled"] is False

    restored = MontageSession.from_dict(d)
    assert restored.file_path == "/tmp/test.mp4"
    assert restored.crop_aspect == "4:3"
    assert restored.output_format == "mkv"


def test_montage_session_store_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = Path(tmpdir) / "montage.json"
        store = MontageSessionStore(store_file)

        # Initially empty
        assert store.get_session("/dummy/file.mp4") is None

        # Save session
        dummy_path = Path(tmpdir) / "sample.mp4"
        data = {
            "in_point": 2.5,
            "out_point": 10.0,
            "crop_x": 0,
            "crop_y": 0,
            "crop_w": 1280,
            "crop_h": 720,
        }
        store.save_session(dummy_path, data)

        loaded = store.get_session(dummy_path)
        assert loaded is not None
        assert loaded["in_point"] == 2.5
        assert loaded["out_point"] == 10.0
        assert str(dummy_path.resolve()) == loaded["file_path"]

        # Re-instantiate store from same file
        store2 = MontageSessionStore(store_file)
        loaded2 = store2.get_session(dummy_path)
        assert loaded2 is not None
        assert loaded2["crop_w"] == 1280

        # Delete session
        deleted = store.delete_session(dummy_path)
        assert deleted is True
        assert store.get_session(dummy_path) is None

        # Corrupted JSON recovery
        store_file.write_text("NOT_A_VALID_JSON{{{", encoding="utf-8")
        store_corrupt = MontageSessionStore(store_file)
        assert store_corrupt.get_session(dummy_path) is None


def test_montage_service_get_media_metadata_mocked():
    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = Path(tmpdir) / "montage.json"
        service = MontageService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe", store_path=store_file)

        test_file = Path(tmpdir) / "video.mp4"
        test_file.write_bytes(b"dummy")

        ffprobe_output = {
            "format": {"duration": "123.45"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "24000/1001",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                },
            ],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["ffprobe"],
                returncode=0,
                stdout=json.dumps(ffprobe_output),
                stderr="",
            )
            meta = service.get_media_metadata(test_file)
            assert meta["duration"] == 123.45
            assert meta["width"] == 1920
            assert meta["height"] == 1080
            assert meta["fps"] == 23.976
            assert meta["vcodec"] == "h264"
            assert meta["acodec"] == "aac"
            assert meta["has_video"] is True
            assert meta["has_audio"] is True


def test_montage_service_get_session_with_overrides():
    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = Path(tmpdir) / "montage.json"
        service = MontageService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe", store_path=store_file)
        test_file = Path(tmpdir) / "clip.mov"
        test_file.write_bytes(b"dummy")

        service.get_media_metadata = MagicMock(
            return_value={
                "duration": 60.0,
                "width": 1280,
                "height": 720,
                "fps": 30.0,
                "has_video": True,
                "has_audio": True,
            }
        )

        overrides = {
            "trim_start": 5.0,
            "trim_end": 25.0,
            "crop_x": 10,
            "crop_y": 10,
            "crop_w": 640,
            "crop_h": 480,
            "remove_audio": True,
            "out_video_format": "mp4",
        }

        sess = service.get_session(test_file, existing_overrides=overrides)
        assert sess["in_point"] == 5.0
        assert sess["out_point"] == 25.0
        assert sess["crop_w"] == 640
        assert sess["audio_enabled"] is False
        assert sess["metadata"]["duration"] == 60.0


def test_backend_montage_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = Path(tmpdir) / "montage.json"
        test_video = Path(tmpdir) / "movie.mp4"
        test_video.write_bytes(b"content")

        backend = Backend()
        backend.settings_manager.save = MagicMock()
        backend.montage_service = MontageService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe", store_path=store_file)
        backend.montage_service.get_media_metadata = MagicMock(
            return_value={
                "duration": 100.0,
                "width": 1920,
                "height": 1080,
                "fps": 24.0,
                "has_video": True,
                "has_audio": True,
            }
        )

        # Add task to queue
        task = TaskItem(
            path=test_video,
            media_type="video",
            status=TaskStatus.QUEUED,
        )
        backend.queue_model.add_items([task])

        # Get initial session
        session = backend.getMontageSession(str(test_video))
        assert session["in_point"] == 0.0
        assert session["out_point"] == 100.0

        # Update and apply montage
        new_session_data = {
            "in_point": 10.0,
            "out_point": 50.0,
            "crop_x": 100,
            "crop_y": 50,
            "crop_w": 800,
            "crop_h": 600,
            "crop_aspect": "4:3",
            "audio_enabled": False,
            "output_format": "mov",
        }

        signal_emitted = []
        backend.montageSessionUpdated.connect(lambda p: signal_emitted.append(p))

        backend.applyMontageToTask(str(test_video), new_session_data)

        assert len(signal_emitted) == 1
        assert Path(signal_emitted[0]) == test_video.expanduser()

        # Verify task overrides in queue
        index = backend.queue_model.index_for_path(test_video)
        item = backend.queue_model.item_at(index)
        assert item is not None
        assert item.overrides.get("trim_start") == 10.0
        assert item.overrides.get("trim_end") == 50.0
        assert item.overrides.get("crop_x") == 100
        assert item.overrides.get("crop_y") == 50
        assert item.overrides.get("crop_w") == 800
        assert item.overrides.get("crop_h") == 600
        assert item.overrides.get("remove_audio") is True
        assert item.overrides.get("out_video_format") == "mov"
        # Since crop is specified, fast_copy MUST be forced to False
        assert item.overrides.get("fast_copy") is False

        backend.shutdown()


def test_backend_pick_video_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_video = Path(tmpdir) / "sample.mp4"
        test_video.write_bytes(b"data")

        backend = Backend()
        backend.settings_manager.save = MagicMock()
        initial_count = backend.queue_model.rowCount()
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileNames") as mock_dialog:
            mock_dialog.return_value = ([str(test_video)], "Videos")
            picked = backend.pickVideoFile()
            assert picked == str(test_video)
            assert backend.queue_model.rowCount() == initial_count + 1

        backend.shutdown()
