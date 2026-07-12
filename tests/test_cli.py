import sys
from unittest.mock import patch

import cli


def test_cli_blocks_duplicate_output_names_before_starting_conversion(tmp_path):
    first = tmp_path / "camera_a" / "clip.mp4"
    second = tmp_path / "camera_b" / "clip.mp4"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    output_dir = tmp_path / "out"

    with patch.object(cli.FfmpegService, "detect_encoders", return_value=set()):
        result = cli.main(
            [
                "--input",
                str(first),
                str(second),
                "--output-dir",
                str(output_dir),
                "--ffmpeg",
                sys.executable,
                "--collision-policy",
                "stop",
            ]
        )

    assert result == 2
    assert output_dir.exists()
    assert not list(output_dir.iterdir())
