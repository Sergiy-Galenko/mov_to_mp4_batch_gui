"""Scripting Engine — User-defined JavaScript rules for renaming, routing, and FFmpeg filters.

Executes ECMAScript via PySide6.QtQml.QJSEngine in a secure sandbox without filesystem
or external network access. Provides:
- formatOutputName(file): dynamic filename formatting based on metadata.
- routeOutputFolder(file): automatic sorting/routing into subdirectories.
- buildVideoFilter(file, settings): dynamic construction of FFmpeg -vf filter chains.
- Built-in snippets catalog, live tester, and validation helpers.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine

from app.paths import APP_DATA_DIR
from utils.files import sanitize_file_stem
from utils.state import load_json_state, save_json_state

logger = logging.getLogger(__name__)

SCRIPTING_CONFIG_PATH = APP_DATA_DIR / "scripts.json"

DEFAULT_RENAME_SCRIPT = (
    "function formatOutputName(file) {\n"
    "    // file: { name, stem, ext, width, height, resolution, fps, duration, vcodec, acodec, sizeMB, date, index, parent }\n"
    "    return `[${file.resolution}]_${file.name.toUpperCase()}_${file.date}`;\n"
    "}"
)

DEFAULT_ROUTE_SCRIPT = (
    "function routeOutputFolder(file) {\n"
    '    if (file.width >= 3840) return "4K_UHD";\n'
    '    if (file.fps >= 50) return "HighFPS";\n'
    '    if (file.duration > 0 && file.duration <= 60) return "Shorts";\n'
    '    return ""; // залишати в кореневій папці виводу\n'
    "}"
)

DEFAULT_FILTER_SCRIPT = (
    "function buildVideoFilter(file, settings) {\n"
    "    let filters = [];\n"
    '    if (file.width > 1920) filters.push("scale=1920:-2");\n'
    "    if (file.fps > 30) filters.push(\"fps=30\");\n"
    '    return filters.join(",");\n'
    "}"
)

SNIPPETS_CATALOG: dict[str, list[dict[str, str]]] = {
    "rename": [
        {
            "id": "rename_res_name_date",
            "title": "[Роздільність]_ІМ'Я_Дата",
            "code": (
                "function formatOutputName(file) {\n"
                "    return `[${file.resolution}]_${file.name.toUpperCase()}_${file.date}`;\n"
                "}"
            ),
        },
        {
            "id": "rename_index_name_fps",
            "title": "Номер_Ім'я_FPS (001_video_60fps)",
            "code": (
                "function formatOutputName(file) {\n"
                "    const num = String(file.index || 1).padStart(3, '0');\n"
                "    const fps = Math.round(file.fps || 30);\n"
                "    return `${num}_${file.stem}_${fps}fps`;\n"
                "}"
            ),
        },
        {
            "id": "rename_parent_codec",
            "title": "БатьківськаПапка_Ім'я_Кодек",
            "code": (
                "function formatOutputName(file) {\n"
                "    const p = file.parent || 'video';\n"
                "    const c = file.vcodec || 'h264';\n"
                "    return `${p}_${file.stem}_${c}`;\n"
                "}"
            ),
        },
        {
            "id": "rename_clean_web",
            "title": "Очищене ім'я для веб (lowercase, no spaces)",
            "code": (
                "function formatOutputName(file) {\n"
                "    const clean = file.stem.toLowerCase().replace(/\\s+/g, '_');\n"
                "    return `${clean}_web_${file.resolution}`;\n"
                "}"
            ),
        },
    ],
    "route": [
        {
            "id": "route_by_resolution",
            "title": "За роздільною здатністю (4K_UHD / FullHD / SD)",
            "code": (
                "function routeOutputFolder(file) {\n"
                '    if (file.width >= 3840) return "4K_UHD";\n'
                '    if (file.height >= 1080) return "FullHD";\n'
                '    return "SD";\n'
                "}"
            ),
        },
        {
            "id": "route_by_fps",
            "title": "За частотою кадрів (HighFPS / Standard)",
            "code": (
                "function routeOutputFolder(file) {\n"
                '    return (file.fps >= 50) ? "HighFPS" : "StandardFPS";\n'
                "}"
            ),
        },
        {
            "id": "route_by_duration",
            "title": "За тривалістю (Shorts ≤60s / LongForm)",
            "code": (
                "function routeOutputFolder(file) {\n"
                '    return (file.duration > 0 && file.duration <= 60) ? "Shorts" : "LongForm";\n'
                "}"
            ),
        },
        {
            "id": "route_by_codec",
            "title": "За вхідним відеокодеком (HEVC / H264 / Other)",
            "code": (
                "function routeOutputFolder(file) {\n"
                "    const c = (file.vcodec || '').toLowerCase();\n"
                '    if (c.includes(\"hevc\") || c.includes(\"h265\")) return \"HEVC\";\n'
                '    if (c.includes(\"h264\") || c.includes(\"avc\")) return \"H264\";\n'
                '    return \"Other\";\n'
                "}"
            ),
        },
    ],
    "filter": [
        {
            "id": "filter_scale_fps",
            "title": "Авто-скейлінг 1080p + обмеження 30fps",
            "code": (
                "function buildVideoFilter(file, settings) {\n"
                "    let f = [];\n"
                '    if (file.width > 1920) f.push("scale=1920:-2");\n'
                '    if (file.fps > 30) f.push("fps=30");\n'
                '    return f.join(",");\n'
                "}"
            ),
        },
        {
            "id": "filter_unsharp",
            "title": "Підвищення різкості (Unsharp)",
            "code": (
                "function buildVideoFilter(file, settings) {\n"
                '    return "unsharp=5:5:0.9:5:5:0.4";\n'
                "}"
            ),
        },
        {
            "id": "filter_eq",
            "title": "Корекція контрасту та насиченості (eq)",
            "code": (
                "function buildVideoFilter(file, settings) {\n"
                '    return "eq=contrast=1.08:saturation=1.15:brightness=0.01";\n'
                "}"
            ),
        },
        {
            "id": "filter_yadif",
            "title": "Деінтерлейсинг для черезрядкового відео (yadif)",
            "code": (
                "function buildVideoFilter(file, settings) {\n"
                '    return "yadif=1";\n'
                "}"
            ),
        },
    ],
}


@dataclass
class ScriptingConfig:
    enabled: bool = False
    rename_enabled: bool = True
    rename_script: str = DEFAULT_RENAME_SCRIPT
    route_enabled: bool = False
    route_script: str = DEFAULT_ROUTE_SCRIPT
    filter_enabled: bool = False
    filter_script: str = DEFAULT_FILTER_SCRIPT
    custom_scripts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScriptingConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            rename_enabled=bool(data.get("rename_enabled", True)),
            rename_script=str(data.get("rename_script") or DEFAULT_RENAME_SCRIPT),
            route_enabled=bool(data.get("route_enabled", False)),
            route_script=str(data.get("route_script") or DEFAULT_ROUTE_SCRIPT),
            filter_enabled=bool(data.get("filter_enabled", False)),
            filter_script=str(data.get("filter_script") or DEFAULT_FILTER_SCRIPT),
            custom_scripts=dict(data.get("custom_scripts") or {}),
        )


class ScriptingService:
    """Manages ECMAScript script execution and configuration for batch conversion."""

    def __init__(self, path: Path = SCRIPTING_CONFIG_PATH) -> None:
        self.path = path
        self.config = self._load()

    def _load(self) -> ScriptingConfig:
        data = load_json_state(self.path)
        if not data:
            return ScriptingConfig()
        return ScriptingConfig.from_dict(data)

    def save(self, config_map: dict[str, Any]) -> None:
        self.config = ScriptingConfig.from_dict(config_map)
        save_json_state(self.path, self.config.to_dict())

    def get_config(self) -> dict[str, Any]:
        return self.config.to_dict()

    @staticmethod
    def _ensure_qt_core() -> None:
        if QCoreApplication.instance() is None:
            try:
                from PySide6.QtWidgets import QApplication

                _ = QApplication.instance() or QApplication([])
            except Exception:
                _ = QCoreApplication([])

    def _create_engine(self) -> QJSEngine:
        self._ensure_qt_core()
        return QJSEngine()

    @staticmethod
    def build_file_context(
        path: Path | str,
        info: Any = None,
        index: int = 1,
    ) -> dict[str, Any]:
        """Constructs a clean JS-accessible metadata dictionary for a media file."""
        p = Path(path)
        now = datetime.now()

        w = int(getattr(info, "width", 0) or 0) if info else 0
        h = int(getattr(info, "height", 0) or 0) if info else 0
        fps = float(getattr(info, "fps", 0.0) or 0.0) if info else 0.0
        dur = float(getattr(info, "duration", 0.0) or 0.0) if info else 0.0
        vcodec = str(getattr(info, "vcodec", "") or "") if info else ""
        acodec = str(getattr(info, "acodec", "") or "") if info else ""
        size_bytes = int(getattr(info, "size_bytes", 0) or 0) if info else 0

        if not size_bytes and p.exists():
            try:
                size_bytes = p.stat().st_size
            except Exception:
                size_bytes = 0

        # Calculate standard resolution name
        if w >= 3800 or h >= 2100:
            res = "4K"
        elif h >= 1400:
            res = "1440p"
        elif h >= 1000:
            res = "1080p"
        elif h >= 700:
            res = "720p"
        elif h >= 460:
            res = "480p"
        elif w > 0 and h > 0:
            res = f"{w}x{h}"
        else:
            res = "video"

        return {
            "name": p.stem,
            "stem": p.stem,
            "ext": p.suffix.lstrip(".").lower(),
            "filename": p.name,
            "parent": p.parent.name if p.parent else "",
            "width": w,
            "height": h,
            "resolution": res,
            "fps": round(fps, 2),
            "duration": round(dur, 2),
            "vcodec": vcodec,
            "acodec": acodec,
            "size": size_bytes,
            "sizeMB": round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0,
            "date": now.strftime("%Y-%m-%d"),
            "year": now.strftime("%Y"),
            "time": now.strftime("%H-%M-%S"),
            "index": index,
        }

    def evaluate_rename(
        self,
        file_meta: dict[str, Any],
        script: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Runs formatOutputName(file) and returns (success, stem, error)."""
        code = script if script is not None else self.config.rename_script
        if not code or not code.strip():
            return True, file_meta.get("name", "output"), None

        code = code.strip()
        if "function formatOutputName" not in code:
            if not code.startswith("return "):
                code = f"return {code};"
            code = f"function formatOutputName(file) {{\n    {code}\n}}"

        engine = self._create_engine()
        eval_script = (
            f"{code}\n"
            f"formatOutputName({json.dumps(file_meta)});"
        )
        try:
            val = engine.evaluate(eval_script)
            if val.isError():
                err_msg = val.toString()
                logger.warning("JS formatOutputName error: %s", err_msg)
                return False, file_meta.get("name", "output"), err_msg
            raw_str = val.toString().strip()
            clean_stem = sanitize_file_stem(raw_str)
            return True, clean_stem or file_meta.get("name", "output"), None
        except Exception as exc:
            logger.warning("JS formatOutputName exception: %s", exc)
            return False, file_meta.get("name", "output"), str(exc)

    def evaluate_route(
        self,
        file_meta: dict[str, Any],
        script: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Runs routeOutputFolder(file) and returns (success, subfolder, error)."""
        code = script if script is not None else self.config.route_script
        if not code or not code.strip():
            return True, "", None

        code = code.strip()
        if "function routeOutputFolder" not in code:
            if not code.startswith("return "):
                code = f"return {code};"
            code = f"function routeOutputFolder(file) {{\n    {code}\n}}"

        engine = self._create_engine()
        eval_script = (
            f"{code}\n"
            f"routeOutputFolder({json.dumps(file_meta)});"
        )
        try:
            val = engine.evaluate(eval_script)
            if val.isError():
                err_msg = val.toString()
                logger.warning("JS routeOutputFolder error: %s", err_msg)
                return False, "", err_msg
            raw_folder = val.toString().strip()
            # Clean and prevent directory traversal
            clean_folder = self._sanitize_relative_subfolder(raw_folder)
            return True, clean_folder, None
        except Exception as exc:
            logger.warning("JS routeOutputFolder exception: %s", exc)
            return False, "", str(exc)

    def evaluate_filter(
        self,
        file_meta: dict[str, Any],
        settings_meta: dict[str, Any],
        script: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Runs buildVideoFilter(file, settings) and returns (success, filter_chain, error)."""
        code = script if script is not None else self.config.filter_script
        if not code or not code.strip():
            return True, "", None

        code = code.strip()
        if "function buildVideoFilter" not in code:
            if not code.startswith("return "):
                code = f"return {code};"
            code = f"function buildVideoFilter(file, settings) {{\n    {code}\n}}"

        engine = self._create_engine()
        eval_script = (
            f"{code}\n"
            f"buildVideoFilter({json.dumps(file_meta)}, {json.dumps(settings_meta)});"
        )
        try:
            val = engine.evaluate(eval_script)
            if val.isError():
                err_msg = val.toString()
                logger.warning("JS buildVideoFilter error: %s", err_msg)
                return False, "", err_msg

            if val.isArray():
                length = int(val.property("length").toInt())
                parts = []
                for i in range(length):
                    item = val.property(i).toString().strip()
                    if item:
                        parts.append(item)
                filter_str = ",".join(parts)
            else:
                filter_str = val.toString().strip()

            clean_filter = self._sanitize_filter_chain(filter_str)
            return True, clean_filter, None
        except Exception as exc:
            logger.warning("JS buildVideoFilter exception: %s", exc)
            return False, "", str(exc)

    @staticmethod
    def _sanitize_relative_subfolder(path_str: str) -> str:
        """Sanitizes user subfolder to prevent path traversal outside output directory."""
        if not path_str:
            return ""
        # Remove absolute slashes, colons, nulls
        parts = [p.strip() for p in re.split(r"[\\/]+", path_str) if p.strip()]
        clean_parts = []
        for part in parts:
            if part in {".", ".."}:
                continue
            cleaned = sanitize_file_stem(part)
            if cleaned and cleaned not in {".", ".."}:
                clean_parts.append(cleaned)
        return "/".join(clean_parts)

    @staticmethod
    def _sanitize_filter_chain(filter_str: str) -> str:
        """Sanitizes filter chain to prevent dangerous shell syntax."""
        if not filter_str:
            return ""
        # Strip semicolons (which start filter complex graphs or shell commands) and shell pipes
        sanitized = re.sub(r"[;&|><$`\x00-\x1f]", "", filter_str).strip()
        # Clean double commas
        sanitized = re.sub(r",+", ",", sanitized).strip(",")
        return sanitized

    def test_script(
        self,
        script_type: str,
        code: str,
        sample_file: dict[str, Any] | None = None,
        sample_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validates and evaluates user script with sample data, returning test report."""
        meta = sample_file or {
            "name": "DJI_0042",
            "stem": "DJI_0042",
            "ext": "mov",
            "filename": "DJI_0042.mov",
            "parent": "Aerial",
            "width": 3840,
            "height": 2160,
            "resolution": "4K",
            "fps": 59.94,
            "duration": 74.2,
            "vcodec": "hevc",
            "acodec": "aac",
            "size": 184549376,
            "sizeMB": 176.0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "year": datetime.now().strftime("%Y"),
            "time": datetime.now().strftime("%H-%M-%S"),
            "index": 1,
        }
        st = sample_settings or {
            "out_video_format": "mp4",
            "crf": 22,
            "preset": "fast",
            "encoder": "libx264",
            "fps": 30,
        }

        if script_type == "rename":
            ok, res, err = self.evaluate_rename(meta, script=code)
            return {
                "success": ok,
                "result": f"{res}.{meta.get('ext', 'mp4')}" if ok else "",
                "raw_result": res,
                "error": err,
            }
        elif script_type == "route":
            ok, res, err = self.evaluate_route(meta, script=code)
            return {
                "success": ok,
                "result": res if res else "(коренева папка)",
                "raw_result": res,
                "error": err,
            }
        elif script_type == "filter":
            ok, res, err = self.evaluate_filter(meta, st, script=code)
            return {
                "success": ok,
                "result": res if res else "(без додаткових фільтрів)",
                "raw_result": res,
                "error": err,
            }

        return {"success": False, "result": "", "error": f"Невідомий тип скрипта: {script_type}"}

    def get_snippets(self, script_type: str) -> list[dict[str, str]]:
        return SNIPPETS_CATALOG.get(script_type, [])

    def reset_script(self, script_type: str) -> str:
        defaults = {
            "rename": DEFAULT_RENAME_SCRIPT,
            "route": DEFAULT_ROUTE_SCRIPT,
            "filter": DEFAULT_FILTER_SCRIPT,
        }
        return defaults.get(script_type, "")
