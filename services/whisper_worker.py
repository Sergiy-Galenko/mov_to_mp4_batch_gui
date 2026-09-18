"""Runs without Qt in the selected Python interpreter, including packaged builds."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def diagnose() -> dict:
    from services.whisper_runtime import package_available

    engines = {}
    for name, module in (("whisper", "whisper"), ("faster-whisper", "faster_whisper")):
        data = {"installed": False, "devices": [], "errors": [], "version": ""}
        engines[name] = data
        if not package_available(module):
            continue
        try:
            if name == "whisper":
                import torch
                import whisper

                data["version"] = str(getattr(whisper, "__version__", ""))
                for device in ("cpu", "cuda", "mps"):
                    if device == "cuda" and not torch.cuda.is_available():
                        continue
                    if device == "mps" and not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
                        continue
                    try:
                        tensor = torch.ones((8, 8), device=device)
                        (tensor @ tensor).sum().item()
                        data["devices"].append(device)
                    except Exception as exc:
                        data["errors"].append(f"{device.upper()}: {exc}")
            else:
                import ctranslate2
                import faster_whisper

                data["version"] = str(getattr(faster_whisper, "__version__", ""))
                if ctranslate2.get_supported_compute_types("cpu"):
                    data["devices"].append("cpu")
                try:
                    if ctranslate2.get_cuda_device_count() and ctranslate2.get_supported_compute_types("cuda"):
                        data["devices"].append("cuda")
                except Exception as exc:
                    data["errors"].append(f"CUDA: {exc}")
            data["installed"] = "cpu" in data["devices"]
        except Exception as exc:
            data["errors"].append(str(exc))
    return {"engines": engines, "python": sys.executable, "python_version": sys.version.split()[0]}


def recognition_test(source: str, output: str, model: str, engine: str, device: str) -> dict:
    from app.models import ConversionSettings
    from services.transcription_service import TranscriptionService
    from services.whisper_model_manager import WhisperModelManager, normalize_model
    from services.whisper_runtime import engine_for, resolve_device

    selected = engine_for(device, engine)
    manager = WhisperModelManager()
    try:
        if not manager.is_model_downloaded(normalize_model(model), selected):
            raise RuntimeError("Download the selected model in the model manager before testing.")
    finally:
        manager.shutdown()
    resolved = resolve_device(device, selected)
    settings = ConversionSettings(subtitle_model=model, subtitle_engine=selected, subtitle_device=resolved, out_subtitle_format="txt")
    started = time.monotonic()
    TranscriptionService().generate(Path(source), Path(output), settings)
    text = Path(output).read_text(encoding="utf-8").strip()
    return {"text": text, "seconds": round(time.monotonic() - started, 2), "device": resolved, "engine": selected, "model": model}


def main(argv=None) -> int:
    os.environ["MEDIA_CONVERTER_WHISPER_WORKER"] = "1"
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["diagnose"]:
            result = diagnose()
        elif len(args) == 6 and args[0] == "test":
            result = recognition_test(*args[1:])
        elif args[:1] == ["transcribe"]:
            from services.transcription_service import run_transcription_worker

            return run_transcription_worker(args[1:])
        else:
            raise ValueError("Unsupported Whisper worker action")
        print("WHISPER_RESULT=" + json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
