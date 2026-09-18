import tempfile
from pathlib import Path

from services.scripting_service import ScriptingService


def test_scripting_service_default_and_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_path = Path(tmp_dir) / "scripts.json"
        svc = ScriptingService(path=cfg_path)
        cfg = svc.get_config()
        assert cfg["enabled"] is False
        assert cfg["rename_enabled"] is True
        assert "formatOutputName" in cfg["rename_script"]

        # Modify and save
        cfg["enabled"] = True
        cfg["rename_script"] = "function formatOutputName(file) { return file.name.toLowerCase(); }"
        svc.save(cfg)

        # Reload
        svc2 = ScriptingService(path=cfg_path)
        cfg2 = svc2.get_config()
        assert cfg2["enabled"] is True
        assert "file.name.toLowerCase()" in cfg2["rename_script"]


def test_evaluate_rename():
    with tempfile.TemporaryDirectory() as tmp_dir:
        svc = ScriptingService(path=Path(tmp_dir) / "scripts.json")
        file_meta = {
            "name": "summer_vacation",
            "stem": "summer_vacation",
            "resolution": "4K",
            "date": "2026-09-18",
        }

        # 1. Standard default function
        code = "function formatOutputName(file) { return `[${file.resolution}]_${file.name.toUpperCase()}_${file.date}`; }"
        ok, res, err = svc.evaluate_rename(file_meta, script=code)
        assert ok is True
        assert res == "[4K]_SUMMER_VACATION_2026-09-18"
        assert err is None

        # 2. Inline expression without function keyword
        inline_code = "`web_${file.name}_${file.resolution}`"
        ok, res, err = svc.evaluate_rename(file_meta, script=inline_code)
        assert ok is True
        assert res == "web_summer_vacation_4K"
        assert err is None

        # 3. Syntax error handling
        bad_code = "function formatOutputName(file) { return ;;;; bad syntax {{; }"
        ok, res, err = svc.evaluate_rename(file_meta, script=bad_code)
        assert ok is False
        assert res == "summer_vacation"  # fallback to original
        assert err is not None


def test_evaluate_route():
    with tempfile.TemporaryDirectory() as tmp_dir:
        svc = ScriptingService(path=Path(tmp_dir) / "scripts.json")

        meta_4k = {"width": 3840, "fps": 30, "duration": 120}
        meta_high_fps = {"width": 1920, "fps": 60, "duration": 45}
        meta_normal = {"width": 1280, "fps": 24, "duration": 300}

        script = (
            "function routeOutputFolder(file) {\n"
            '    if (file.width >= 3840) return "UHD_4K";\n'
            '    if (file.fps >= 50) return "60FPS";\n'
            '    return "Standard";\n'
            "}"
        )

        ok, folder_4k, _ = svc.evaluate_route(meta_4k, script=script)
        assert ok is True and folder_4k == "UHD_4K"

        ok, folder_fps, _ = svc.evaluate_route(meta_high_fps, script=script)
        assert ok is True and folder_fps == "60FPS"

        ok, folder_norm, _ = svc.evaluate_route(meta_normal, script=script)
        assert ok is True and folder_norm == "Standard"

        # Traversal protection test
        traversal_script = 'function routeOutputFolder(file) { return "../../secret/sub"; }'
        ok, safe_folder, _ = svc.evaluate_route(meta_normal, script=traversal_script)
        assert ".." not in safe_folder
        assert safe_folder == "secret/sub"


def test_evaluate_filter():
    with tempfile.TemporaryDirectory() as tmp_dir:
        svc = ScriptingService(path=Path(tmp_dir) / "scripts.json")

        meta = {"width": 3840, "fps": 60}
        settings = {"fps": 30}

        # 1. Array return
        script_array = (
            "function buildVideoFilter(file, settings) {\n"
            "    let f = [];\n"
            '    if (file.width > 1920) f.push("scale=1920:-2");\n'
            "    if (file.fps > 30) f.push(`fps=${settings.fps}`);\n"
            "    return f;\n"
            "}"
        )
        ok, vf, err = svc.evaluate_filter(meta, settings, script=script_array)
        assert ok is True
        assert vf == "scale=1920:-2,fps=30"
        assert err is None

        # 2. String return with unsharp
        script_str = 'function buildVideoFilter(file, settings) { return "unsharp=5:5:0.8"; }'
        ok, vf, err = svc.evaluate_filter(meta, settings, script=script_str)
        assert ok is True
        assert vf == "unsharp=5:5:0.8"

        # 3. Shell injection protection
        injection_script = 'function buildVideoFilter(file, settings) { return "scale=1280:720; rm -rf / | echo"; }'
        ok, vf, err = svc.evaluate_filter(meta, settings, script=injection_script)
        assert ok is True
        assert ";" not in vf
        assert "|" not in vf


def test_test_script_reporting_and_snippets():
    with tempfile.TemporaryDirectory() as tmp_dir:
        svc = ScriptingService(path=Path(tmp_dir) / "scripts.json")

        # Rename test report
        rep = svc.test_script("rename", "function formatOutputName(file) { return `TEST_${file.name}`; }")
        assert rep["success"] is True
        assert "TEST_DJI_0042" in rep["result"]

        # Bad script report
        rep_err = svc.test_script("rename", "function formatOutputName(file) { throw new Error('Boom'); }")
        assert rep_err["success"] is False
        assert "Boom" in rep_err["error"]

        # Snippets catalog
        snips = svc.get_snippets("rename")
        assert len(snips) >= 3
        assert any("res" in s["id"] for s in snips)

        snips_filter = svc.get_snippets("filter")
        assert len(snips_filter) >= 3

        # Default script reset
        def_rename = svc.reset_script("rename")
        assert "formatOutputName" in def_rename

