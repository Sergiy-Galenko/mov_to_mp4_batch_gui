from __future__ import annotations

import os
import sys
from pathlib import Path

import PyInstaller.__main__

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import find_ffmpeg, find_ffprobe


def main() -> int:
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe(ffmpeg)

    if ffmpeg and ffprobe:
        ffmpeg_dir = Path(ffmpeg).resolve().parent
        if Path(ffprobe).resolve().parent == ffmpeg_dir:
            os.environ["MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR"] = str(ffmpeg_dir)
            print(f"Bundling FFmpeg from: {ffmpeg_dir}")
        else:
            print("FFmpeg and FFprobe found in different directories. Bundle them manually if needed.")
    else:
        print("FFmpeg/FFprobe not both found. Build will continue without bundling those binaries.")
        print("Use scripts/find_ffmpeg.py for setup hints.")

    PyInstaller.__main__.run(
        [
            "--noconfirm",
            str(PROJECT_ROOT / "media_converter.spec"),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
