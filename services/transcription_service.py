import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.models import ConversionSettings
from services.whisper_environment import managed_runtime, worker_command, worker_environment
from services.whisper_model_manager import WhisperModelManager, normalize_model
from services.whisper_runtime import cache_root, engine_for, package_available, resolve_device


def is_whisper_available() -> bool:
    return shutil.which("whisper") is not None or package_available("whisper") or package_available("faster_whisper")


class TranscriptionService:
    def generate_managed(self, inp: Path, outp: Path, settings: ConversionSettings, run, ffmpeg_path: str | None = None) -> int:
        """Keep model loading and transcription in a cancellable child process."""
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "settings.json"
            config.write_text(json.dumps(asdict(settings)), encoding="utf-8")
            entry = [] if getattr(sys, "frozen", False) else [str(Path(__file__).resolve().parents[1] / "main.py")]
            cmd = [sys.executable, *entry, "--transcribe-worker", str(inp), str(outp), str(config)]
            if managed_runtime():
                cmd = worker_command("transcribe", str(inp), str(outp), str(config))
                result = run(cmd, env=worker_environment(ffmpeg_path or ""))
            elif ffmpeg_path:
                worker_env = dict(os.environ)
                worker_env["MEDIA_CONVERTER_FFMPEG"] = str(ffmpeg_path)
                worker_env["PATH"] = str(Path(ffmpeg_path).parent) + os.pathsep + worker_env.get("PATH", "")
                result = run(cmd, env=worker_env)
            else:
                result = run(cmd)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout or "Transcription failed").strip()[-2000:])
            return result.returncode

    def _resolve_format(self, settings: ConversionSettings, outp: Path) -> str:
        requested = outp.suffix.lower().lstrip(".") or settings.out_subtitle_format or "srt"
        if requested in {"srt", "vtt"}:
            return requested
        return "srt"

    def _resolve_cli(self, settings: ConversionSettings) -> str | None:
        engine = settings.subtitle_engine.strip().lower()
        if engine in {"", "auto", "whisper", "openai-whisper"}:
            return shutil.which("whisper")
        return shutil.which(engine)

    def _generate_with_faster_whisper(self, inp: Path, outp: Path, settings: ConversionSettings) -> bool:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception:
            return False

        model_name = normalize_model(settings.subtitle_model.strip() or "base")
        language = settings.subtitle_language.strip() or "auto"
        lang_arg = None if language == "auto" else language
        try:
            device = resolve_device(settings.subtitle_device, "faster-whisper")
            manager = WhisperModelManager()
            try:
                cached = manager.model_path(model_name, "faster-whisper")
                model = WhisperModel(
                    str(cached) if cached else model_name,
                    device=device,
                    compute_type="float16" if device == "cuda" else "int8",
                    download_root=str(manager.hub_dir),
                )
            finally:
                manager.shutdown()
            segments, _info = model.transcribe(str(inp), language=lang_arg, beam_size=5)
            out_format = self._resolve_format(settings, outp)
            outp.parent.mkdir(parents=True, exist_ok=True)
            with open(outp, "w", encoding="utf-8") as f:
                if out_format == "vtt":
                    f.write("WEBVTT\n\n")
                    for seg in segments:
                        start_h, start_rem = divmod(seg.start, 3600)
                        start_m, start_s = divmod(start_rem, 60)
                        end_h, end_rem = divmod(seg.end, 3600)
                        end_m, end_s = divmod(end_rem, 60)
                        f.write(
                            f"{int(start_h):02d}:{int(start_m):02d}:{start_s:06.3f} --> {int(end_h):02d}:{int(end_m):02d}:{end_s:06.3f}\n"
                        )
                        f.write(f"{seg.text.strip()}\n\n")
                else:
                    for i, seg in enumerate(segments, start=1):
                        start_h, start_rem = divmod(seg.start, 3600)
                        start_m, start_s = divmod(start_rem, 60)
                        end_h, end_rem = divmod(seg.end, 3600)
                        end_m, end_s = divmod(end_rem, 60)
                        f.write(f"{i}\n")
                        f.write(
                            f"{int(start_h):02d}:{int(start_m):02d}:{int(start_s):02d},{int((start_s % 1) * 1000):03d} --> {int(end_h):02d}:{int(end_m):02d}:{int(end_s):02d},{int((end_s % 1) * 1000):03d}\n"
                        )
                        f.write(f"{seg.text.strip()}\n\n")
            return outp.exists()
        except Exception as exc:
            raise RuntimeError(f"faster-whisper ({settings.subtitle_device}): {exc}") from exc

    def _whisper_audio(self, inp: Path):
        from app.paths import find_ffmpeg

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return str(inp)
        import numpy as np

        # Use the app's selected executable, including binaries not named ffmpeg
        # or installed on PATH. Match Whisper's 16 kHz mono float32 input.
        result = subprocess.run(
            [ffmpeg, "-nostdin", "-v", "error", "-i", str(inp), "-vn", "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
            capture_output=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip() or "Audio decoding failed")
        return np.frombuffer(result.stdout, np.int16).astype(np.float32) / 32768.0

    def _generate_with_python(self, inp: Path, outp: Path, settings: ConversionSettings) -> bool:
        engine = engine_for(settings.subtitle_device, settings.subtitle_engine)
        if engine == "faster-whisper":
            return self._generate_with_faster_whisper(inp, outp, settings)
        try:
            import whisper  # type: ignore
            from whisper.utils import get_writer  # type: ignore
        except Exception:
            return False

        model_name = normalize_model(settings.subtitle_model.strip() or "base")
        language = settings.subtitle_language.strip() or "auto"
        try:
            device = resolve_device(settings.subtitle_device, "whisper")
            # Whisper registers a sparse alignment buffer, unsupported by MPS.
            # Segment subtitles do not use word alignment, so move a dense buffer.
            model = whisper.load_model(model_name, device="cpu" if device == "mps" else device, download_root=str(cache_root() / "whisper"))
            if device == "mps":
                model.register_buffer("alignment_heads", model.alignment_heads.to_dense(), persistent=False)
                model = model.to("mps")
            result = model.transcribe(
                self._whisper_audio(inp),
                language=None if language == "auto" else language,
                verbose=False,
                fp16=device == "cuda",
                word_timestamps=False,
            )
            out_format = self._resolve_format(settings, outp)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_dir = Path(tmpdir)
                writer = get_writer(out_format, str(tmp_dir))
                writer(result, str(inp))
                generated = tmp_dir / f"{inp.stem}.{out_format}"
                if not generated.exists():
                    return False
                outp.parent.mkdir(parents=True, exist_ok=True)
                outp.write_text(generated.read_text(encoding="utf-8"), encoding="utf-8")
            return outp.exists()
        except Exception as exc:
            raise RuntimeError(f"Whisper ({settings.subtitle_device}): {exc}") from exc

    def generate(self, inp: Path, outp: Path, settings: ConversionSettings, log_cb=None) -> int:
        if outp.suffix.lower() == ".ass":
            from app.paths import find_ffmpeg

            ffmpeg = find_ffmpeg()
            if not ffmpeg:
                raise RuntimeError("FFmpeg is required for ASS subtitles.")
            with tempfile.TemporaryDirectory() as tmp:
                srt = Path(tmp) / "transcript.srt"
                self.generate(inp, srt, settings, log_cb=log_cb)
                result = subprocess.run([ffmpeg, "-y", "-i", str(srt), "-c:s", "ass", str(outp)], capture_output=True, text=True)
                if result.returncode:
                    raise RuntimeError(result.stderr.strip())
            return 0
        if self._generate_with_python(inp, outp, settings):
            return 0

        engine = engine_for(settings.subtitle_device, settings.subtitle_engine)
        if engine == "faster-whisper":
            raise RuntimeError("Install faster-whisper to use the selected transcription engine.")
        if settings.subtitle_device == "mps":
            raise RuntimeError("MPS transcription requires openai-whisper and an MPS-enabled PyTorch in this Python environment.")
        whisper_cli = self._resolve_cli(settings)
        if not whisper_cli:
            raise RuntimeError("Whisper не знайдено. Встанови openai-whisper або CLI whisper.")

        out_format = self._resolve_format(settings, outp)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            cmd = [
                whisper_cli,
                str(inp),
                "--task",
                "transcribe",
                "--model",
                normalize_model(settings.subtitle_model.strip() or "base"),
                "--model_dir",
                str(cache_root() / "whisper"),
                "--output_format",
                out_format,
                "--output_dir",
                str(tmp_dir),
                "--verbose",
                "False",
            ]
            device = settings.subtitle_device
            if device == "auto" and package_available("torch"):
                device = resolve_device("auto", "whisper")
            if device != "auto":
                cmd += ["--device", device, "--fp16", "True" if device == "cuda" else "False"]
            language = settings.subtitle_language.strip() or "auto"
            if language != "auto":
                cmd += ["--language", language]
            if log_cb:
                log_cb("INFO", f"Whisper: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError as exc:
                raise RuntimeError("Whisper не знайдено. Встанови openai-whisper або CLI whisper.") from exc
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Whisper завершився з помилкою")

            generated = tmp_dir / f"{inp.stem}.{out_format}"
            if not generated.exists():
                raise RuntimeError("Whisper не створив файл субтитрів")
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_text(generated.read_text(encoding="utf-8"), encoding="utf-8")
        return 0


def run_transcription_worker(args: list[str]) -> int:
    try:
        source, output, config = args
        settings = ConversionSettings(**json.loads(Path(config).read_text(encoding="utf-8")))
        return TranscriptionService().generate(Path(source), Path(output), settings)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
