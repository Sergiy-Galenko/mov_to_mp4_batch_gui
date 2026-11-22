"""Repeatable application workloads and optional matched-environment regression gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def compare(current: dict, baseline: dict, ratio: float) -> list[str]:
    if current.get("environment_id") != baseline.get("environment_id") or current.get("schema_version") != baseline.get("schema_version"):
        raise ValueError("Benchmark baseline must match the machine, tools, workload and schema")
    failures = []
    for key, value in baseline["metrics"].items():
        actual = current["metrics"].get(key)
        if actual is None or not isinstance(actual, (int, float)):
            failures.append(f"{key}: missing metric")
        elif value > 0 and actual > value * ratio:
            failures.append(f"{key}: {actual / value:.2f}x baseline")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--report", type=Path, default=Path("performance.json"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--write-baseline", type=Path)
    parser.add_argument("--max-regression", type=float, default=1.5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--speech-audio", type=Path)
    parser.add_argument("--speech-model", default="tiny")
    args = parser.parse_args()
    if args.repeats < 1 or args.max_regression <= 1:
        parser.error("Positive repeats and --max-regression > 1 are required")
    runtime = {}
    if args.speech_audio:
        # Read the installed runtime in a separate process before isolation;
        # imported application paths in this process must remain disposable.
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json; from services.whisper_environment import managed_runtime; print(json.dumps(managed_runtime()))",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if probe.returncode == 0:
            runtime = json.loads(probe.stdout)
    with tempfile.TemporaryDirectory(prefix="media-converter-benchmark-") as temporary:
        root = Path(temporary)
        # Import paths only after isolation: benchmarking never changes user cache/history.
        os.environ["MEDIA_CONVERTER_PORTABLE_DIR"] = str(root / "data")
        if runtime:
            manifest = root / "data" / "data" / "whisper-runtime.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(runtime), encoding="utf-8")
        from app.models import ConversionSettings, TaskItem
        from services.cache_manager import CacheManager
        from services.media_preview_service import MediaPreviewService
        from services.workload_history import ProcessMemorySampler
        from ui.models import QueueModel
        from utils.state import save_json_file

        metrics = {}

        def measure(function):
            return statistics.median(_timed(function) for _ in range(args.repeats))

        def launch(arguments):
            process = subprocess.Popen(
                [args.ffmpeg, "-hide_banner", "-loglevel", "error", *arguments], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            sampler = ProcessMemorySampler(process.pid)
            try:
                if process.wait(timeout=120):
                    raise RuntimeError("Benchmark FFmpeg workload failed")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                sampler.close()
            return sampler.peak_rss

        source = root / "4k.mp4"
        launch(
            [
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=3840x2160:rate=5",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-threads",
                "2",
                "-c:a",
                "aac",
                str(source),
            ]
        )
        peak = []
        metrics["encode_4k_seconds"] = measure(
            lambda: peak.append(
                launch(
                    [
                        "-y",
                        "-threads",
                        "2",
                        "-i",
                        str(source),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-threads",
                        "2",
                        str(root / "encoded.mp4"),
                    ]
                )
            )
        )
        metrics["encode_4k_peak_rss_bytes"] = max(peak)
        model = QueueModel()
        tasks = [TaskItem(root / f"queue-{i}.mp4", "video") for i in range(10000)]
        metrics["queue_10000_import_seconds"] = _timed(lambda: model.add_items(tasks))
        metrics["queue_1000_updates_seconds"] = measure(
            lambda: [model.set_task_progress(tasks[-1].path, (i % 100) / 100) for i in range(1000)]
        )
        cache = CacheManager(root / "cache")
        preview = MediaPreviewService(args.ffmpeg, cache=cache)

        def cold():
            cache.cleanup(clear=True)
            paths = preview.thumbnail_strip(source, count=4, duration=1)
            if len(paths) != 4:
                raise RuntimeError("Preview benchmark failed")

        metrics["preview_cold_seconds"] = measure(cold)
        metrics["preview_warm_seconds"] = measure(lambda: preview.thumbnail_strip(source, count=4, duration=1))
        waveform = preview.audio_waveform(source)
        if waveform is None:
            raise RuntimeError("Waveform benchmark failed")
        metrics["waveform_warm_seconds"] = measure(lambda: preview.audio_waveform(source))
        startup = []
        for index in range(args.repeats):
            report = root / f"startup-{index}.json"
            process = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "main.py"), "--self-test", "--allow-missing-ffprobe", "--report", str(report)],
                env=dict(os.environ, MEDIA_CONVERTER_FFMPEG=args.ffmpeg, QT_QPA_PLATFORM="offscreen"),
                capture_output=True,
                timeout=120,
            )
            data = json.loads(report.read_text()) if report.exists() else {}
            if process.returncode or not data.get("ok"):
                raise RuntimeError("Startup benchmark failed")
            startup.append(data["timings"]["startup_seconds"])
        metrics["qml_startup_seconds"] = statistics.median(startup)
        skipped = {"transcription": "Provide --speech-audio with an already installed Whisper model/runtime"}
        if args.speech_audio:
            from services.transcription_service import TranscriptionService
            from services.whisper_model_manager import WhisperModelManager
            from services.whisper_runtime import engine_for

            settings = ConversionSettings(operation="auto_subtitle", subtitle_model=args.speech_model)
            manager = WhisperModelManager()
            try:
                if not manager.is_model_downloaded(args.speech_model, engine_for(settings.subtitle_device, settings.subtitle_engine)):
                    raise RuntimeError("Speech benchmark requires an already downloaded model")
                converter = TranscriptionService()

                def speech():
                    def run(command, **kwargs):
                        return subprocess.run(command, capture_output=True, timeout=600, **kwargs)

                    if converter.generate_managed(args.speech_audio, root / "speech.srt", settings, run, args.ffmpeg):
                        raise RuntimeError("Speech benchmark failed")

                metrics["transcription_seconds"] = measure(speech)
                skipped = {}
            finally:
                manager.shutdown()
        version = subprocess.run([args.ffmpeg, "-version"], capture_output=True, text=True, timeout=5).stdout.splitlines()[0]
        import psutil
        import PySide6

        environment = [
            platform.node(),
            psutil.virtual_memory().total,
            PySide6.__version__,
            platform.system(),
            platform.machine(),
            platform.processor(),
            os.cpu_count(),
            sys.version,
            version,
            args.speech_model if args.speech_audio else None,
            hashlib.sha256(args.speech_audio.read_bytes()).hexdigest() if args.speech_audio else None,
        ]
        report = {
            "schema_version": 1,
            "environment_id": hashlib.sha256(json.dumps(environment).encode()).hexdigest(),
            "repeats": args.repeats,
            "metrics": metrics,
            "skipped": skipped,
        }
        failures = compare(report, json.loads(args.baseline.read_text()), args.max_regression) if args.baseline else []
        report["regressions"] = failures
        save_json_file(args.report, report)
        if args.write_baseline:
            save_json_file(args.write_baseline, report)
        print(json.dumps(report, indent=2))
        return 1 if failures else 0


def _timed(function):
    start = time.perf_counter()
    function()
    return time.perf_counter() - start


if __name__ == "__main__":
    raise SystemExit(main())
