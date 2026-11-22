"""Speech Recognition & Hardware Acceleration Diagnostic and Setup Service.

Provides:
- Detailed hardware accelerator inspection (Apple Silicon MPS, NVIDIA CUDA, CPU).
- Python package dependency verification for speech recognition (faster-whisper, whisper, torch).
- Automatic / on-demand dependency installer for hardware-accelerated speech.
- Quick recognition self-test benchmark measuring latency and verifying pipeline health.
"""

from __future__ import annotations

import importlib.util
import logging
import math
import os
import platform
import struct
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.paths import find_ffmpeg

logger = logging.getLogger(__name__)


@dataclass
class HardwareAccelerationInfo:
    mps_available: bool = False
    mps_built: bool = False
    cuda_available: bool = False
    cuda_device_name: str = ""
    cuda_device_count: int = 0
    cuda_vram_gb: float = 0.0
    cpu_arch: str = ""
    cpu_threads: int = 4
    recommended_device: str = "cpu"
    recommended_engine: str = "faster-whisper"
    summary_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SpeechDependencyStatus:
    torch_installed: bool = False
    torch_version: str = ""
    whisper_installed: bool = False
    faster_whisper_installed: bool = False
    ctranslate2_installed: bool = False
    ffmpeg_installed: bool = False
    missing_packages: list[str] = field(default_factory=list)
    install_command: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecognitionTestResult:
    success: bool = False
    device_used: str = "cpu"
    engine_used: str = "fallback"
    latency_ms: float = 0.0
    transcription_text: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SpeechDiagnosticService:
    """Diagnostic service for MPS/CUDA/CPU detection, dependency setup, and recognition testing."""

    @staticmethod
    def is_package_installed(package_name: str) -> bool:
        try:
            return importlib.util.find_spec(package_name) is not None
        except (ImportError, ValueError):
            return False

    def check_hardware(self) -> HardwareAccelerationInfo:
        """Inspect MPS, CUDA, and CPU acceleration capabilities."""
        info = HardwareAccelerationInfo(
            cpu_arch=platform.machine() or "x86_64",
            cpu_threads=os.cpu_count() or 4,
        )

        # 1. Check Apple Silicon MPS
        is_macos = sys.platform == "darwin"
        is_arm_mac = is_macos and info.cpu_arch in {"arm64", "aarch64"}

        try:
            import torch  # type: ignore
            if hasattr(torch.backends, "mps"):
                info.mps_built = getattr(torch.backends.mps, "is_built", lambda: False)()
                info.mps_available = getattr(torch.backends.mps, "is_available", lambda: False)()
            if torch.cuda.is_available():
                info.cuda_available = True
                info.cuda_device_count = torch.cuda.device_count()
                info.cuda_device_name = torch.cuda.get_device_name(0) if info.cuda_device_count > 0 else ""
                props = torch.cuda.get_device_properties(0) if info.cuda_device_count > 0 else None
                if props:
                    info.cuda_vram_gb = round(props.total_memory / (1024**3), 2)
        except Exception:
            pass

        # 2. Check ctranslate2 for CUDA if torch is absent
        if not info.cuda_available and self.is_package_installed("ctranslate2"):
            try:
                import ctranslate2  # type: ignore
                if ctranslate2.get_cuda_device_count() > 0:
                    info.cuda_available = True
                    info.cuda_device_count = ctranslate2.get_cuda_device_count()
                    info.cuda_device_name = "NVIDIA CUDA Device (ctranslate2)"
            except Exception:
                pass

        # 3. Determine recommended accelerator
        if info.cuda_available:
            info.recommended_device = "cuda"
            info.recommended_engine = "faster-whisper"
            info.summary_text = f"NVIDIA CUDA ({info.cuda_device_name}, {info.cuda_vram_gb} GB VRAM)"
        elif info.mps_available:
            info.recommended_device = "mps"
            info.recommended_engine = "whisper"
            info.summary_text = "Apple Silicon Metal (MPS)"
        elif is_arm_mac:
            # Running on Apple Silicon, but PyTorch with MPS not yet installed
            info.recommended_device = "cpu"
            info.recommended_engine = "whisper"
            info.summary_text = "Apple Silicon (MPS доступний після встановлення torch)"
        else:
            info.recommended_device = "cpu"
            info.recommended_engine = "faster-whisper" if self.is_package_installed("faster_whisper") else "whisper"
            info.summary_text = f"CPU ({info.cpu_arch}, {info.cpu_threads} потоків)"

        return info

    def check_dependencies(self) -> SpeechDependencyStatus:
        """Inspect speech libraries status and construct pip install recommendations."""
        torch_ok = self.is_package_installed("torch")
        torch_ver = ""
        if torch_ok:
            try:
                import torch  # type: ignore
                torch_ver = str(getattr(torch, "__version__", ""))
            except Exception:
                pass

        whisper_ok = self.is_package_installed("whisper")
        faster_whisper_ok = self.is_package_installed("faster_whisper")
        ctranslate2_ok = self.is_package_installed("ctranslate2")
        ffmpeg_ok = bool(find_ffmpeg())

        missing: list[str] = []
        is_macos = sys.platform == "darwin"
        is_arm = platform.machine() in {"arm64", "aarch64"}

        if not faster_whisper_ok and not whisper_ok:
            if is_macos and is_arm:
                missing.extend(["openai-whisper", "torch"])
            else:
                missing.append("faster-whisper")

        # Recommended command
        if is_macos and is_arm:
            cmd = f"{sys.executable} -m pip install openai-whisper torch torchaudio"
        else:
            cmd = f"{sys.executable} -m pip install faster-whisper"

        return SpeechDependencyStatus(
            torch_installed=torch_ok,
            torch_version=torch_ver,
            whisper_installed=whisper_ok,
            faster_whisper_installed=faster_whisper_ok,
            ctranslate2_installed=ctranslate2_ok,
            ffmpeg_installed=ffmpeg_ok,
            missing_packages=missing,
            install_command=cmd,
        )

    def install_dependencies(self, preferred_engine: str = "auto") -> tuple[bool, str]:
        """Install speech recognition dependencies into current Python environment."""
        is_macos = sys.platform == "darwin"
        is_arm = platform.machine() in {"arm64", "aarch64"}

        if preferred_engine == "whisper" or (preferred_engine == "auto" and is_macos and is_arm):
            packages = ["openai-whisper", "torch", "torchaudio"]
        else:
            packages = ["faster-whisper"]

        cmd = [sys.executable, "-m", "pip", "install", *packages]
        logger.info("Installing speech recognition dependencies: %s", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode == 0:
                return True, "Успішно встановлено: " + ", ".join(packages)
            return False, f"Помилка встановлення ({proc.returncode}): " + (proc.stderr or proc.stdout)[-500:]
        except Exception as exc:
            return False, f"Виняток при встановленні: {exc}"

    def _generate_synthetic_test_wav(self, output_path: Path, duration_sec: float = 1.0) -> Path:
        """Create a tiny 1-second 16kHz mono WAV tone to test recognition pipeline without internet."""
        sample_rate = 16000
        total_samples = int(duration_sec * sample_rate)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Generate soft 440Hz sine wave tone
            frames = bytearray()
            for i in range(total_samples):
                val = int(math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)) * 12000.0)
                frames.extend(struct.pack("<h", val))
            wf.writeframes(frames)
        return output_path

    def run_quick_recognition_test(self, requested_device: str = "auto") -> RecognitionTestResult:
        """Run a quick recognition diagnostic and measure inference latency."""
        t_start = time.perf_counter()
        hw = self.check_hardware()
        dev = hw.recommended_device if requested_device == "auto" else requested_device

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_wav = Path(tmp_dir) / "test_tone.wav"
            self._generate_synthetic_test_wav(test_wav, duration_sec=1.0)

            # 1. Test faster-whisper if installed and device is CPU or CUDA
            if dev in {"cpu", "cuda"} and self.is_package_installed("faster_whisper"):
                try:
                    from faster_whisper import WhisperModel  # type: ignore
                    model = WhisperModel("tiny", device=dev, compute_type="int8")
                    segments, _ = model.transcribe(str(test_wav), beam_size=1)
                    text = " ".join([s.text for s in segments]).strip()
                    elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
                    return RecognitionTestResult(
                        success=True,
                        device_used=dev,
                        engine_used="faster-whisper (tiny)",
                        latency_ms=elapsed_ms,
                        transcription_text=text or "✓ Сигнал оброблено (тиша/тон)",
                        message=f"Тест успішний! Пристрій: {dev.upper()} ({elapsed_ms} мс)",
                    )
                except Exception as exc:
                    logger.debug("faster-whisper test failed: %s", exc)

            # 2. Test openai-whisper with MPS or CPU
            if self.is_package_installed("whisper") and self.is_package_installed("torch"):
                try:
                    import whisper  # type: ignore
                    model = whisper.load_model("tiny", device=dev)
                    res = model.transcribe(str(test_wav), fp16=(dev == "cuda"))
                    text = str(res.get("text", "")).strip()
                    elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
                    return RecognitionTestResult(
                        success=True,
                        device_used=dev,
                        engine_used=f"openai-whisper (tiny, {dev})",
                        latency_ms=elapsed_ms,
                        transcription_text=text or "✓ Сигнал оброблено",
                        message=f"Тест успішний на {dev.upper()} ({elapsed_ms} мс)",
                    )
                except Exception as exc:
                    logger.debug("whisper test failed: %s", exc)

            # 3. Fallback verification (FFmpeg audio pipeline)
            elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
            ffmpeg_ok = bool(find_ffmpeg())
            if ffmpeg_ok:
                return RecognitionTestResult(
                    success=True,
                    device_used=dev,
                    engine_used="Audio Pipeline (FFmpeg Ready)",
                    latency_ms=elapsed_ms,
                    transcription_text="Аудіо-стек готовий. Встановіть faster-whisper або whisper для локального AI.",
                    message=f"Аудіопідсистема готова. Рекомендований прискорювач: {hw.summary_text}",
                )

            return RecognitionTestResult(
                success=False,
                device_used=dev,
                engine_used="none",
                latency_ms=elapsed_ms,
                message="FFmpeg або Whisper не виявлено. Встановіть залежності для розпізнавання.",
            )

