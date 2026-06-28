# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path


project_root = Path(SPEC).resolve().parent.parent
bundle_dir = os.environ.get("MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR", "").strip()

datas = [
    (str(project_root / "ui" / "qml"), "ui/qml"),
    (str(project_root / "ui" / "i18n"), "ui/i18n"),
    (str(project_root / "assets"), "assets"),
]
binaries = []

if bundle_dir:
    for binary_name in ("ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"):
        candidate = Path(bundle_dir) / binary_name
        if candidate.exists():
            binaries.append((str(candidate), "."))


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "email",
        "html",
        "http",
        "xmlrpc",
        "pydoc",
        "doctest",
        "difflib",
        "multiprocessing.pool",
    ],
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
    upx_exclude=[],
    console=False,
)

