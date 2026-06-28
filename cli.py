from __future__ import annotations

import argparse
import json
import queue
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.paths import find_ffmpeg, find_ffprobe
from app.localization import normalize_language, translate
from app.models import ConversionSettings
from app.performance_profiles import PROFILE_NAMES
from app.settings import settings_map_to_model
from services.converter_service import ConverterService
from services.ffmpeg_service import FfmpegService
from services.preset_manager import PresetManager
from services.queue_manager import QueueManager
from utils.state import load_json_file


def _flatten_inputs(values: Iterable[Any]) -> List[Path]:
    paths: List[Path] = []
    for value in values:
        if isinstance(value, (list, tuple)):
            paths.extend(_flatten_inputs(value))
        else:
            text = str(value or "").strip()
            if text:
                paths.append(Path(text).expanduser())
    return paths


def _print_event(event: tuple, language: str) -> None:
    etype = event[0]
    if etype == "log":
        _, level, message = event
        print(f"[{level}] {message}")
    elif etype == "status":
        _, message = event
        print(message)
    elif etype == "task_state":
        _, path, status, message, output = event
        suffix = f" -> {output}" if output else ""
        details = f" | {message}" if message else ""
        print(f"{Path(path).name}: {status}{suffix}{details}")
    elif etype == "progress":
        if len(event) >= 8:
            _, file_pct, _out_time, _duration, _file_eta, total_pct, _total_eta, _speed = event
        else:
            _, file_pct, _out_time, _duration, _file_eta, total_pct, _total_eta = event
        if total_pct is not None:
            print(f"progress total={total_pct * 100:.1f}% file={(file_pct or 0.0) * 100:.1f}%")
    elif etype == "task_progress":
        _, path, file_pct, _file_eta, _speed, total_pct, _total_eta = event
        print(f"progress {Path(path).name}: {(file_pct or 0.0) * 100:.1f}% total={total_pct * 100:.1f}%")
    elif etype == "run_summary":
        _, summary = event
        failed = sum(1 for item in summary.get("results", []) if item.get("status") == "failed")
        print(f"summary files={summary.get('total_files', 0)} failed={failed}")
    elif etype == "done":
        _, stopped = event
        print(translate("backend.stopped" if stopped else "backend.ready", language))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Media Converter CLI")
    parser.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-i", "--input", action="append", nargs="+", required=True, help="Input file paths")
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    parser.add_argument("--preset", help="Preset name from the preset store")
    parser.add_argument("--settings-json", help="JSON file with GUI-compatible settings")
    parser.add_argument("--profile", choices=PROFILE_NAMES, help="Performance profile")
    parser.add_argument("--target-size-mb", type=float, help="Target output size per file in MB")
    parser.add_argument("--cpu-load-limit", type=int, help="Delay starting a task while CPU load is above this percent")
    parser.add_argument("--gpu-load-limit", type=int, help="Delay starting a task while GPU load is above this percent")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg executable")
    parser.add_argument("--ffprobe", help="Path to ffprobe executable")
    parser.add_argument("--language", default="uk", choices=["uk", "en", "pl", "de"], help="CLI message language")
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    language = normalize_language(args.language)
    settings_map: Dict[str, Any] = {}

    if args.preset:
        preset = PresetManager().get(args.preset)
        if not preset:
            print(f"Preset not found: {args.preset}", file=sys.stderr)
            return 2
        settings_map.update(preset)

    if args.settings_json:
        data = load_json_file(Path(args.settings_json).expanduser())
        if not isinstance(data, dict):
            print(f"Invalid settings JSON: {args.settings_json}", file=sys.stderr)
            return 2
        settings_map.update(data)

    if args.profile:
        settings_map["performance_profile"] = args.profile
    if args.target_size_mb:
        settings_map["target_size_mb"] = args.target_size_mb
    if args.cpu_load_limit:
        settings_map["cpu_load_limit"] = args.cpu_load_limit
    if args.gpu_load_limit:
        settings_map["gpu_load_limit"] = args.gpu_load_limit

    input_paths = _flatten_inputs(args.input or [])
    queue_manager = QueueManager()
    tasks, duplicates, unsupported = queue_manager.build_items(input_paths, [])
    if duplicates:
        print(translate("backend.duplicates_skipped", language, count=duplicates))
    if unsupported:
        print(translate("backend.unsupported_skipped", language, count=unsupported))
    if not tasks:
        print(translate("backend.no_tasks", language), file=sys.stderr)
        return 2

    ffmpeg_path = args.ffmpeg or find_ffmpeg()
    ffprobe_path = args.ffprobe or find_ffprobe(ffmpeg_path)
    if not ffmpeg_path:
        print(translate("backend.ffmpeg_missing", language), file=sys.stderr)
        return 2

    ffmpeg = FfmpegService(ffmpeg_path, ffprobe_path)
    ffmpeg.encoder_caps = ffmpeg.detect_encoders()
    events: "queue.Queue[tuple]" = queue.Queue()
    converter = ConverterService(ffmpeg, events)
    settings = settings_map_to_model(settings_map, defaults=ConversionSettings())
    out_dir = Path(args.output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    converter.start(tasks, settings, out_dir)
    while converter.thread and converter.thread.is_alive():
        try:
            while True:
                _print_event(events.get_nowait(), language)
        except queue.Empty:
            time.sleep(0.1)

    if converter.thread:
        converter.thread.join(timeout=0.1)

    failed = 0
    try:
        while True:
            event = events.get_nowait()
            if event[0] == "run_summary" and isinstance(event[1], dict):
                failed = sum(1 for item in event[1].get("results", []) if item.get("status") == "failed")
            _print_event(event, language)
    except queue.Empty:
        pass

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
