"""Compare a PR's head report with its base revision on the same CI runner."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.performance_suite import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--head-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("regression.json"))
    parser.add_argument("--max-regression", type=float, default=1.5)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-fA-F0-9]{40}", args.base_sha):
        parser.error("A complete base commit SHA is required")
    subprocess.run(["git", "fetch", "origin", args.base_sha, "--depth=1"], check=True, capture_output=True)
    available = subprocess.run(["git", "cat-file", "-e", f"{args.base_sha}:scripts/performance_suite.py"], capture_output=True)
    report = {"base_sha": args.base_sha, "status": "baseline_unavailable", "regressions": []}
    if available.returncode == 0:
        with tempfile.TemporaryDirectory(prefix="media-converter-base-") as temporary:
            root = Path(temporary) / "checkout"
            baseline = Path(temporary) / "performance.json"
            subprocess.run(["git", "worktree", "add", "--detach", str(root), args.base_sha], check=True, capture_output=True)
            try:
                head = json.loads(args.head_report.read_text())
                subprocess.run(
                    [
                        sys.executable,
                        str(root / "scripts" / "performance_suite.py"),
                        "--ffmpeg",
                        args.ffmpeg,
                        "--report",
                        str(baseline),
                        "--repeats",
                        str(head["repeats"]),
                    ],
                    cwd=root,
                    check=True,
                    timeout=600,
                )
                try:
                    report["regressions"] = compare(head, json.loads(baseline.read_text()), args.max_regression)
                    report["status"] = "compared"
                except ValueError:
                    report["status"] = "baseline_incompatible"
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(root)], check=True, capture_output=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if report["regressions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
