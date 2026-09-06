import shutil
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.models import ConversionSettings


def _try_import_whisper() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        pass
    try:
        import whisper  # noqa: F401
        return True
    except Exception:
        return False


def is_whisper_available() -> bool:
    return shutil.which("whisper") is not None or _try_import_whisper()


class TranscriptionService:
    def generate_managed(self, inp: Path, outp: Path, settings: ConversionSettings, run) -> int:
        """Keep model loading and transcription in a cancellable child process."""
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "settings.json"
            config.write_text(json.dumps(asdict(settings)), encoding="utf-8")
            entry = [] if getattr(sys, "frozen", False) else [str(Path(__file__).resolve().parents[1] / "main.py")]
            cmd = [sys.executable, *entry, "--transcribe-worker", str(inp), str(outp), str(config)]
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

        model_name = settings.subtitle_model.strip() or "base"
        language = settings.subtitle_language.strip() or "auto"
        lang_arg = None if language == "auto" else language
        try:
            model = WhisperModel(model_name, device="auto", compute_type="default")
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
                        f.write(f"{int(start_h):02d}:{int(start_m):02d}:{start_s:06.3f} --> {int(end_h):02d}:{int(end_m):02d}:{end_s:06.3f}\n")
                        f.write(f"{seg.text.strip()}\n\n")
                else:
                    for i, seg in enumerate(segments, start=1):
                        start_h, start_rem = divmod(seg.start, 3600)
                        start_m, start_s = divmod(start_rem, 60)
                        end_h, end_rem = divmod(seg.end, 3600)
                        end_m, end_s = divmod(end_rem, 60)
                        f.write(f"{i}\n")
                        f.write(f"{int(start_h):02d}:{int(start_m):02d}:{int(start_s):02d},{int((start_s % 1) * 1000):03d} --> {int(end_h):02d}:{int(end_m):02d}:{int(end_s):02d},{int((end_s % 1) * 1000):03d}\n")
                        f.write(f"{seg.text.strip()}\n\n")
            return outp.exists()
        except Exception:
            return False

    def _generate_with_python(self, inp: Path, outp: Path, settings: ConversionSettings) -> bool:
        if self._generate_with_faster_whisper(inp, outp, settings):
            return True
        try:
            import whisper  # type: ignore
            from whisper.utils import get_writer  # type: ignore
        except Exception:
            return False

        model_name = settings.subtitle_model.strip() or "base"
        language = settings.subtitle_language.strip() or "auto"
        try:
            model = whisper.load_model(model_name)
            result = model.transcribe(str(inp), language=None if language == "auto" else language, verbose=False)
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
        except Exception:
            return False

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
                settings.subtitle_model.strip() or "base",
                "--output_format",
                out_format,
                "--output_dir",
                str(tmp_dir),
                "--verbose",
                "False",
            ]
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
