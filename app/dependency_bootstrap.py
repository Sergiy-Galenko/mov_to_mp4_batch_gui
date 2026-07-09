from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REQUIREMENT_IMPORTS = {
    "PySide6": "PySide6",
    "psutil": "psutil",
    "pypdf": "pypdf",
    "reportlab": "reportlab",
    "yt-dlp": "yt_dlp",
}


class DependencyBootstrapError(RuntimeError):
    pass


def missing_runtime_dependencies(requirements_path: Path) -> list[str]:
    missing: list[str] = []
    for package in _requirement_names(requirements_path):
        module_name = REQUIREMENT_IMPORTS.get(package, package.replace("-", "_"))
        if importlib.util.find_spec(module_name) is None:
            missing.append(package)
    return missing


def ensure_runtime_dependencies(requirements_path: Path, *, stdout=None, stderr=None) -> list[str]:
    if os.environ.get("MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP", "").strip() in {"1", "true", "yes"}:
        return []
    requirements_path = requirements_path.expanduser().resolve()
    missing = missing_runtime_dependencies(requirements_path)
    if not missing:
        return []
    if not requirements_path.exists():
        raise DependencyBootstrapError(f"requirements.txt not found: {requirements_path}")
    if os.environ.get("MEDIA_CONVERTER_AUTO_INSTALL_DEPS", "").strip().lower() not in {"1", "true", "yes"}:
        raise DependencyBootstrapError(
            "Missing Python libraries: "
            + ", ".join(missing)
            + f". Install them with: {sys.executable} -m pip install -r {requirements_path}"
        )
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
    result = subprocess.run(cmd, stdout=stdout, stderr=stderr, text=True)
    if result.returncode != 0:
        raise DependencyBootstrapError(
            "Failed to install missing Python libraries: "
            + ", ".join(missing)
            + f". Command failed: {' '.join(cmd)}"
        )
    still_missing = missing_runtime_dependencies(requirements_path)
    if still_missing:
        raise DependencyBootstrapError("Python libraries are still missing after install: " + ", ".join(still_missing))
    return missing


def _requirement_names(requirements_path: Path) -> Sequence[str]:
    if not requirements_path.exists():
        return []
    result: list[str] = []
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        name = _requirement_name(raw_line)
        if name:
            result.append(name)
    return result


def _requirement_name(line: str) -> str:
    text = line.split("#", 1)[0].strip()
    if not text or text.startswith(("-", "git+", "http://", "https://")):
        return ""
    for marker in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";"):
        if marker in text:
            text = text.split(marker, 1)[0].strip()
    return text
