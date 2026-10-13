"""Repeatable CPU-loop and optional frame-stream measurements (JSON on stdout)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.frame_stream import sample_frames
from services.native_acceleration import native
from services.text_conversion_service import _to_rtf_python, _unescape_pdf_literal_python


def measure(function, value, repeats):
    function(value)  # warm caches/imports
    times = []
    for _ in range(repeats):
        started = time.perf_counter()
        function(value)
        times.append(time.perf_counter() - started)
    tracemalloc.start()
    function(value)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"median_seconds": statistics.median(times), "python_peak_bytes": peak}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    text = "Українська English 🦀 {\\}\n" * 20000
    literal = b"text\\n\\050example\\051\\123\\\\" * 20000
    results = {
        "native_available": native is not None,
        "rtf_python": measure(_to_rtf_python, text, args.repeats),
        "pdf_python": measure(_unescape_pdf_literal_python, literal, args.repeats),
    }
    if native is not None:
        assert native.to_rtf(text) == _to_rtf_python(text)
        assert native.unescape_pdf_literal(literal) == _unescape_pdf_literal_python(literal)
        results["rtf_native"] = measure(native.to_rtf, text, args.repeats)
        results["pdf_native"] = measure(native.unescape_pdf_literal, literal, args.repeats)
    if args.video:

        def consume(path):
            return sum(1 for _ in sample_frames(args.ffmpeg, path, 0.5, width=320))

        results["frame_count"] = consume(args.video)
        results["frame_stream"] = measure(consume, args.video, args.repeats)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
