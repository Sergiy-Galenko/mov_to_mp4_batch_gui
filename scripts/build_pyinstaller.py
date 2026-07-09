from __future__ import annotations

import os
import sys
from pathlib import Path

import PyInstaller.__main__

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_FILE = PROJECT_ROOT / "build" / "media_converter.spec"
ICON_SOURCE = PROJECT_ROOT / "assets" / "app-logo.png"
ICON_FILE = PROJECT_ROOT / "assets" / "app-logo.ico"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _ensure_windows_icon() -> None:
    if not ICON_SOURCE.exists():
        print("App icon source not found; build will use the default executable icon.")
        return
    if ICON_FILE.exists() and ICON_FILE.stat().st_mtime >= ICON_SOURCE.stat().st_mtime:
        return
    try:
        from PIL import Image
    except Exception as exc:
        print(f"Could not generate Windows .ico from {ICON_SOURCE.name}: {exc}")
        return

    with Image.open(ICON_SOURCE) as image:
        image.save(
            ICON_FILE,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    print(f"Generated Windows icon: {ICON_FILE}")


def main() -> int:
    from app.paths import find_ffmpeg, find_ffprobe

    _ensure_windows_icon()

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
            str(SPEC_FILE),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
