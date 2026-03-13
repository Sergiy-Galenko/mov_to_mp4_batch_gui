# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path


project_root = Path(__file__).resolve().parent
bundle_dir = os.environ.get("MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR", "").strip()

datas = [
    (str(project_root / "ui" / "qml"), "ui/qml"),
    (str(project_root / "assets"), "assets"),
]
binaries = []

if bundle_dir:
    for binary_name in ("ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"):
        candidate = Path(bundle_dir) / binary_name
        if candidate.exists():
            binaries.append((str(candidate), "."))


a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MediaConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

