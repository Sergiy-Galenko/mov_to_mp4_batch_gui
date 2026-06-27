"""GPU / hardware encoder auto-detection service."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class HardwareCapabilities:
    nvidia_available: bool = False
    nvidia_encoders: List[str] = field(default_factory=list)
    intel_qsv_available: bool = False
    qsv_encoders: List[str] = field(default_factory=list)
    amd_amf_available: bool = False
    amf_encoders: List[str] = field(default_factory=list)
    all_encoders: Set[str] = field(default_factory=set)
    detection_error: str = ""

    @property
    def has_gpu(self) -> bool:
        return self.nvidia_available or self.intel_qsv_available or self.amd_amf_available

    @property
    def best_vendor(self) -> str:
        if self.nvidia_available:
            return "nvidia"
        if self.intel_qsv_available:
            return "intel"
        if self.amd_amf_available:
            return "amd"
        return "cpu"

    def summary(self) -> str:
        parts: List[str] = []
        if self.nvidia_available:
            parts.append(f"NVIDIA NVENC ({len(self.nvidia_encoders)} enc)")
        if self.intel_qsv_available:
            parts.append(f"Intel QSV ({len(self.qsv_encoders)} enc)")
        if self.amd_amf_available:
            parts.append(f"AMD AMF ({len(self.amf_encoders)} enc)")
        if not parts:
            parts.append("CPU only")
        return " | ".join(parts)


_NVIDIA_ENCODERS = {"h264_nvenc", "hevc_nvenc", "av1_nvenc"}
_QSV_ENCODERS = {"h264_qsv", "hevc_qsv", "av1_qsv", "vp9_qsv"}
_AMF_ENCODERS = {"h264_amf", "hevc_amf", "av1_amf"}


class HardwareService:
    def __init__(self, ffmpeg_path: Optional[str] = None) -> None:
        self.ffmpeg_path = ffmpeg_path or ""
        self._cache: Optional[HardwareCapabilities] = None

    def detect(self, ffmpeg_path: Optional[str] = None) -> HardwareCapabilities:
        if ffmpeg_path:
            self.ffmpeg_path = ffmpeg_path
            self._cache = None
        if self._cache is not None:
            return self._cache

        caps = HardwareCapabilities()
        if not self.ffmpeg_path:
            caps.detection_error = "FFmpeg path not set"
            self._cache = caps
            return caps

        try:
            all_encoders = self._list_encoders()
            caps.all_encoders = all_encoders
            caps.nvidia_encoders = sorted(_NVIDIA_ENCODERS & all_encoders)
            caps.nvidia_available = bool(caps.nvidia_encoders)
            caps.qsv_encoders = sorted(_QSV_ENCODERS & all_encoders)
            caps.intel_qsv_available = bool(caps.qsv_encoders)
            caps.amf_encoders = sorted(_AMF_ENCODERS & all_encoders)
            caps.amd_amf_available = bool(caps.amf_encoders)
        except FileNotFoundError:
            caps.detection_error = "FFmpeg not found"
        except subprocess.TimeoutExpired:
            caps.detection_error = "FFmpeg timeout during detection"
        except Exception as exc:
            caps.detection_error = str(exc)

        self._cache = caps
        return caps

    def _list_encoders(self) -> Set[str]:
        result = subprocess.run(
            [self.ffmpeg_path, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=15,
        )
        encoders: Set[str] = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("Encoders:"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[1]
                if parts[0].startswith("V") or name in (_NVIDIA_ENCODERS | _QSV_ENCODERS | _AMF_ENCODERS):
                    encoders.add(name)
        return encoders

    def invalidate_cache(self) -> None:
        self._cache = None

    @property
    def cached(self) -> Optional[HardwareCapabilities]:
        return self._cache
