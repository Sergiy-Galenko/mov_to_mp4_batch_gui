import unittest

from app.presets import DEFAULT_PRESETS


class PresetsTest(unittest.TestCase):
    def test_platform_presets_exist(self) -> None:
        expected = {
            "YouTube • 1080p H.264",
            "TikTok • 9:16",
            "Instagram Reels • 9:16",
            "Instagram Stories • 9:16",
            "Telegram • Compact MP4",
            "WhatsApp • Share MP4",
        }
        self.assertTrue(expected.issubset(DEFAULT_PRESETS.keys()))


if __name__ == "__main__":
    unittest.main()


def test_failed_writes_leave_memory_and_disk_unchanged(tmp_path):
    from unittest.mock import patch

    import pytest

    from services.preset_manager import PresetManager

    manager = PresetManager(tmp_path / "presets.json")
    manager.save("Personal", {"crf": 18})
    previous = manager.path.read_bytes()
    for operation in (lambda: manager.save("Personal", {"crf": 25}), lambda: manager.delete("Personal")):
        with patch("services.preset_manager.save_presets", side_effect=OSError("full disk")), pytest.raises(OSError):
            operation()
        assert manager.get("Personal") == {"crf": 18}
        assert manager.path.read_bytes() == previous


def test_import_conflicts_are_explicit_and_builtins_are_protected(tmp_path):
    import json

    import pytest

    from services.preset_manager import PresetManager

    manager = PresetManager(tmp_path / "presets.json")
    manager.save("Personal", {"crf": 18})
    imported = tmp_path / "import.json"
    imported.write_text(json.dumps({"Personal": {"crf": 25}}))
    with pytest.raises(ValueError, match="вже існують"):
        manager.import_json(imported)
    manager.import_json(imported, conflict_policy="keep")
    assert manager.get("Personal")["crf"] == 18
    manager.import_json(imported, conflict_policy="replace")
    assert manager.get("Personal")["crf"] == 25
    builtin = manager.builtin_names()[0]
    original = manager.get(builtin)
    imported.write_text(json.dumps({builtin: {"crf": 25}}))
    manager.import_json(imported, conflict_policy="replace")
    assert manager.get(builtin) == original
    assert any(name.startswith(builtin) for name in manager.custom_names())
    with pytest.raises(ValueError, match="захищено"):
        manager.save(builtin, {"crf": 1})


def test_presets_reject_malformed_fields():
    import pytest

    from app.presets import validate_presets

    for settings in (
        {"crf": 99},
        {"crf": True},
        {"crf": "bad"},
        {"target_size_mb": "inf"},
        {"fast_copy": "false"},
        {"codec": "invalid"},
        {"codec": {}},
        {"unknown": 1},
    ):
        with pytest.raises(ValueError):
            validate_presets({"Broken": settings})
