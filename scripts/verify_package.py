"""Execute a built artifact's isolated self-test and verify its JSON result."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

REQUIRED_CHECKS = {"qml_startup", "queue_import", "conversion_decode", "pause", "resume", "cancel_cleanup", "ffprobe_metadata"}


def verify(executable: Path, report: Path, *, timeout=180):
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_CONTROLS_STYLE="Basic")
    for name in (
        "MEDIA_CONVERTER_FFMPEG",
        "MEDIA_CONVERTER_FFPROBE",
        "MEDIA_CONVERTER_FFMPEG_DIR",
        "MEDIA_CONVERTER_ALLOW_PATH_BINARIES",
        "MEDIA_CONVERTER_PORTABLE_DIR",
    ):
        environment.pop(name, None)
    report.unlink(missing_ok=True)
    process = subprocess.run(
        [str(executable.resolve()), "--self-test", "--report", str(report.resolve())], env=environment, capture_output=True, timeout=timeout
    )
    result = (
        json.loads(report.read_text(encoding="utf-8"))
        if report.is_file()
        else {"ok": False, "frozen": True, "failure_type": "startup_failure", "returncode": process.returncode, "checks": {}}
    )
    if not report.is_file():
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if process.returncode or not result.get("ok") or not result.get("frozen"):
        raise RuntimeError("Packaged application self-test failed; inspect the JSON report")
    if not {key for key, value in result.get("checks", {}).items() if value is True} >= REQUIRED_CHECKS:
        raise RuntimeError("Packaged application did not execute all required checks")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--report", type=Path, default=Path("package-smoke.json"))
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.report), indent=2))


if __name__ == "__main__":
    main()
