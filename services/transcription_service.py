import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from core.models import ConversionSettings


class TranscriptionService:
    def _resolve_format(self, settings: ConversionSettings, outp: Path) -> str:
        requested = outp.suffix.lower().lstrip(".") or settings.out_subtitle_format or "srt"
        if requested in {"srt", "vtt"}:
            return requested
        return "srt"

    def _resolve_cli(self, settings: ConversionSettings) -> Optional[str]:
        engine = settings.subtitle_engine.strip().lower()
        if engine in {"", "auto", "whisper", "openai-whisper"}:
            return shutil.which("whisper")
        return shutil.which(engine)

    def _generate_with_python(self, inp: Path, outp: Path, settings: ConversionSettings) -> bool:
        try:
            import whisper  # type: ignore
            from whisper.utils import get_writer  # type: ignore
        except Exception:
            return False

        model_name = settings.subtitle_model.strip() or "base"
        language = settings.subtitle_language.strip() or "auto"
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

    def generate(self, inp: Path, outp: Path, settings: ConversionSettings, log_cb=None) -> int:
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Whisper завершився з помилкою")

            generated = tmp_dir / f"{inp.stem}.{out_format}"
            if not generated.exists():
                raise RuntimeError("Whisper не створив файл субтитрів")
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_text(generated.read_text(encoding="utf-8"), encoding="utf-8")
        return 0
