import tempfile
from pathlib import Path

from app.models import ConversionSettings, MediaInfo
from services.ffmpeg_service import FfmpegService
from services.scripting_service import ScriptingService
from ui.backend import Backend
from utils.files import build_output_path


def test_build_output_path_with_scripting_service():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "output"
        in_path = Path("/mock/media/DJI_0042.mov")
        info = MediaInfo(width=3840, height=2160, fps=60.0, vcodec="hevc", duration=80.0)

        svc = ScriptingService(path=Path(tmp_dir) / "scripts.json")
        svc.save({
            "enabled": True,
            "rename_enabled": True,
            "rename_script": "function formatOutputName(file) { return `[${file.resolution}]_${file.name}_${file.vcodec}`; }",
            "route_enabled": True,
            "route_script": 'function routeOutputFolder(file) { return file.width >= 3840 ? "UHD" : "HD"; }',
            "filter_enabled": False,
        })

        out = build_output_path(
            out_dir,
            in_path,
            "mp4",
            template="{stem}",
            index=1,
            operation="convert",
            media_type_name="video",
            overwrite=True,
            skip_existing=False,
            info=info,
            script_service=svc,
        )

        assert out.name == "[4K]_DJI_0042_hevc.mp4"
        assert out.parent.name == "UHD"


def test_build_output_path_with_inline_js_template():
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir) / "output"
        in_path = Path("/mock/media/test_clip.mov")
        info = MediaInfo(width=1920, height=1080)

        # Template starts with js:
        out = build_output_path(
            out_dir,
            in_path,
            "mp4",
            template="js:return `inline_${file.name}_${file.resolution}`",
            index=1,
            operation="convert",
            media_type_name="video",
            overwrite=True,
            skip_existing=False,
            info=info,
        )

        assert out.name == "inline_test_clip_1080p.mp4"


def test_ffmpeg_service_with_scripting_filter():
    with tempfile.TemporaryDirectory() as tmp_dir:
        svc = ScriptingService(path=Path(tmp_dir) / "scripts.json")
        svc.save({
            "enabled": True,
            "filter_enabled": True,
            "filter_script": (
                "function buildVideoFilter(file, settings) {\n"
                '    return "scale=1920:-2,unsharp=5:5:0.8";\n'
                "}"
            ),
        })

        ffmpeg = FfmpegService(ffmpeg_path="/usr/bin/ffmpeg", ffprobe_path="/usr/bin/ffprobe")
        ffmpeg.scripting_service = svc

        inp = Path("/mock/sample.mp4")
        info = MediaInfo(width=3840, height=2160)
        settings = ConversionSettings()

        flag, vf, _, _, _ = ffmpeg.build_video_filter_spec(inp, settings, ".mp4", info=info)
        assert flag == "-vf"
        assert "scale=1920:-2" in vf
        assert "unsharp=5:5:0.8" in vf


def test_backend_scripting_slots():
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as tmp_dir:
        backend = Backend()
        backend.scripting_service = ScriptingService(path=Path(tmp_dir) / "scripts.json")

        cfg = backend.getScriptingConfig()
        assert "enabled" in cfg
        assert "rename_script" in cfg

        cfg["enabled"] = True
        saved = backend.saveScriptingConfig(cfg)
        assert saved is True
        assert backend.getScriptingConfig()["enabled"] is True

        rep = backend.testUserScript("rename", "function formatOutputName(file) { return 'BACKEND_TEST'; }")
        assert rep["success"] is True
        assert "BACKEND_TEST" in rep["result"]

        snips = backend.getScriptSnippets("route")
        assert len(snips) > 0

        def_filter = backend.resetScriptToDefault("filter")
        assert "buildVideoFilter" in def_filter
