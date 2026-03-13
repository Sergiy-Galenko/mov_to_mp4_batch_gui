from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import find_ffmpeg, find_ffprobe


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate ffmpeg/ffprobe for Media Converter.")
    parser.add_argument("--quiet", action="store_true", help="Only print resolved paths when found.")
    args = parser.parse_args()

    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe(ffmpeg)

    if ffmpeg:
        print(f"ffmpeg: {ffmpeg}")
    if ffprobe:
        print(f"ffprobe: {ffprobe}")

    if ffmpeg and ffprobe:
        bundle_dir = Path(ffmpeg).resolve().parent
        if not args.quiet:
            print(f"Bundle hint: MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR={bundle_dir}")
        return 0

    if args.quiet:
        return 1

    print("FFmpeg not fully resolved.")
    print("Hints:")
    print("  1. Install ffmpeg and ffprobe into PATH.")
    print("  2. Or set MEDIA_CONVERTER_FFMPEG / MEDIA_CONVERTER_FFPROBE.")
    print("  3. Or set MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR to a folder containing both binaries.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
