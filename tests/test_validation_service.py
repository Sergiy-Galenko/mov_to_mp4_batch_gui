from types import SimpleNamespace
from unittest.mock import patch

from app.models import ConversionSettings, TaskItem
from services.validation_service import ValidationService


class FakeFfmpegService:
    def output_extension_for(self, _media_type_name, _settings):
        return "mp4"


def test_disk_preflight_blocks_when_temporary_and_output_space_is_insufficient(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"x" * 1024)
    errors: dict[str, str] = {}
    warnings: list[str] = []
    settings = ConversionSettings(target_size_mb=10, smart_ab_test=True, smart_two_pass=True, disk_safety_margin_mb=1)
    service = ValidationService(FakeFfmpegService())

    with patch("services.validation_service.shutil.disk_usage", return_value=SimpleNamespace(free=1024)):
        service._validate_disk_space(
            [TaskItem(path=source, media_type="video")],
            settings,
            tmp_path,
            errors.setdefault,
            warnings.append,
        )

    assert "disk_space" in errors
    assert not warnings
