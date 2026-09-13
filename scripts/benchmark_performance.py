"""Repeatable kernel/queue benchmarks; timings are informational, not test limits."""

import json
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def measure(function, value, repeats=5):
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        result = function(value)
        samples.append(perf_counter() - start)
    return median(samples), result


def main():
    from app.models import TaskItem
    from services.native_acceleration import native
    from services.text_conversion_service import _to_rtf_python, _unescape_pdf_literal_python
    from ui.models import QueueModel

    results = {}
    if native is not None:
        cases = [
            ("rtf", "Відео 🦀 {test} \\ рядок\n" * 50000, _to_rtf_python, native.to_rtf),
            ("pdf_literal", b"Hello\\nworld\\040\\(test\\)\\777 " * 100000, _unescape_pdf_literal_python, native.unescape_pdf_literal),
        ]
        for name, value, python, rust in cases:
            python_time, expected = measure(python, value)
            rust_time, actual = measure(rust, value)
            assert actual == expected, f"{name}: native output differs"
            results[name] = {
                "input_units": len(value),
                "python_ms": round(python_time * 1000, 3),
                "rust_ms": round(rust_time * 1000, 3),
                "speedup": round(python_time / rust_time, 2),
            }
    else:
        results["native"] = "Not installed; build native/ with maturin for Rust benchmarks."

    for count in (100, 10000):
        model = QueueModel()
        items = [TaskItem(Path(f"/benchmark/{i}.mp4"), "video") for i in range(count)]
        model.add_items(items)
        path = items[-1].path

        def update(_unused, model=model, path=path):
            for index in range(1000):
                model.set_task_progress(path, (index % 100) / 100)

        elapsed, _ = measure(update, None)
        results[f"queue_{count}_rows"] = {"updates": 1000, "median_ms": round(elapsed * 1000, 3)}
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
