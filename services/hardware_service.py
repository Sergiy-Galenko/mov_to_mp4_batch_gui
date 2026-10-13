"""GPU / hardware encoder auto-detection service."""

from __future__ import annotations

import glob
import subprocess
import sys
from dataclasses import dataclass, field


@dataclass
class HardwareCapabilities:
    apple_available: bool = False
    videotoolbox_encoders: list[str] = field(default_factory=list)
    nvidia_available: bool = False
    nvidia_encoders: list[str] = field(default_factory=list)
    intel_qsv_available: bool = False
    qsv_encoders: list[str] = field(default_factory=list)
    amd_amf_available: bool = False
    amf_encoders: list[str] = field(default_factory=list)
    all_encoders: set[str] = field(default_factory=set)
    detection_error: str = ""
    vaapi_encoders: list[str] = field(default_factory=list)

    @property
    def has_gpu(self) -> bool:
        return self.apple_available or self.nvidia_available or self.intel_qsv_available or self.amd_amf_available or bool(self.vaapi_encoders)

    @property
    def best_vendor(self) -> str:
        if self.apple_available:
            return "apple"
        if self.nvidia_available:
            return "nvidia"
        if self.intel_qsv_available:
            return "intel"
        if self.amd_amf_available:
            return "amd"
        if self.vaapi_encoders:
            return "vaapi"
        return "cpu"

    def summary(self) -> str:
        parts: list[str] = []
        if self.apple_available:
            parts.append(f"Apple VideoToolbox ({len(self.videotoolbox_encoders)} enc)")
        if self.nvidia_available:
            parts.append(f"NVIDIA NVENC ({len(self.nvidia_encoders)} enc)")
        if self.intel_qsv_available:
            parts.append(f"Intel QSV ({len(self.qsv_encoders)} enc)")
        if self.amd_amf_available:
            parts.append(f"AMD AMF ({len(self.amf_encoders)} enc)")
        if self.vaapi_encoders:
            parts.append(f"VA-API ({len(self.vaapi_encoders)} enc)")
        if not parts:
            parts.append("CPU only")
        return " | ".join(parts)


_VIDEOTOOLBOX_ENCODERS = {"h264_videotoolbox", "hevc_videotoolbox", "prores_videotoolbox"}
_NVIDIA_ENCODERS = {"h264_nvenc", "hevc_nvenc", "av1_nvenc"}
_QSV_ENCODERS = {"h264_qsv", "hevc_qsv", "av1_qsv", "vp9_qsv"}
_AMF_ENCODERS = {"h264_amf", "hevc_amf", "av1_amf"}


def usable_videotoolbox_encoders(ffmpeg_path: str, encoders: set[str]) -> set[str]:
    """Probe real hardware sessions; an encoder listed by FFmpeg may be unusable.

    In particular the original M1 has no ProRes media engine. Never silently
    count Apple's software encoder as hardware acceleration.
    """
    usable = set(encoders) - _VIDEOTOOLBOX_ENCODERS
    if sys.platform != "darwin":
        return usable
    for encoder in sorted(encoders & _VIDEOTOOLBOX_ENCODERS):
        pixel_format = "ayuv64le" if encoder == "prores_videotoolbox" else "yuv420p"
        try:
            result = subprocess.run(
                [
                    ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=size=64x64:rate=1",
                    "-frames:v",
                    "1",
                    "-an",
                    "-c:v",
                    encoder,
                    "-pix_fmt",
                    pixel_format,
                    "-allow_sw",
                    "0",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                usable.add(encoder)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return usable


HARDWARE_ENCODERS = {
    **{name: "apple" for name in _VIDEOTOOLBOX_ENCODERS},
    **{name: "nvidia" for name in _NVIDIA_ENCODERS},
    **{name: "intel" for name in _QSV_ENCODERS},
    **{name: "amd" for name in _AMF_ENCODERS},
    "h264_vaapi": "vaapi", "hevc_vaapi": "vaapi", "av1_vaapi": "vaapi", "vp9_vaapi": "vaapi",
}


def discover_encoders(ffmpeg_path: str, *, run=None, checkpoint=None) -> set[str]:
    """List software encoders and verify hardware with the production pixel format.

    A supplied runner keeps system inventory cancellable. Failed probes never
    advertise usable hardware; runtime conversion still retains CPU fallback.
    VA-API is inventoried separately until rendering supports device uploads.
    """
    if run is None:
        def run(command, *, timeout):
            return subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    listing = run([ffmpeg_path, "-hide_banner", "-encoders"], timeout=15)
    if listing.returncode:
        raise RuntimeError(listing.stderr.strip() or "FFmpeg encoder detection failed")
    advertised = {parts[1] for line in listing.stdout.splitlines()
                  if len(parts := line.split()) >= 2 and 5 <= len(parts[0]) <= 6
                  and parts[0][0] in "VAS" and set(parts[0]) <= set("VASFDXBT.S")}
    usable = advertised - HARDWARE_ENCODERS.keys()
    for encoder in sorted(advertised & HARDWARE_ENCODERS.keys()):
        if checkpoint:
            checkpoint()
        vendor = HARDWARE_ENCODERS[encoder]
        if vendor == "apple" and sys.platform != "darwin":
            continue
        pixel = "ayuv64le" if encoder == "prores_videotoolbox" else "yuv420p"
        command = [ffmpeg_path, "-hide_banner", "-loglevel", "error"]
        if vendor == "vaapi":
            devices = sorted(glob.glob("/dev/dri/renderD*")) if sys.platform.startswith("linux") else []
            if not devices:
                continue
            command += ["-vaapi_device", devices[0]]
        command += ["-f", "lavfi", "-i", "color=size=256x256:rate=1", "-frames:v", "1", "-an"]
        if vendor == "vaapi":
            command += ["-vf", "format=nv12,hwupload"]
        else:
            command += ["-pix_fmt", pixel]
        command += ["-c:v", encoder]
        if vendor == "apple":
            command += ["-allow_sw", "0"]
        try:
            if run([*command, "-f", "null", "-"], timeout=6).returncode == 0:
                usable.add(encoder)
        except (OSError, TimeoutError, subprocess.TimeoutExpired):
            continue
    return usable


class HardwareService:
    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path or ""
        self._cache: HardwareCapabilities | None = None

    def detect(self, ffmpeg_path: str | None = None) -> HardwareCapabilities:
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
            caps.vaapi_encoders = sorted(e for e in all_encoders if e.endswith("_vaapi"))
            caps.videotoolbox_encoders = sorted(_VIDEOTOOLBOX_ENCODERS & all_encoders)
            caps.apple_available = bool(caps.videotoolbox_encoders)
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

    def _list_encoders(self) -> set[str]:
        return discover_encoders(self.ffmpeg_path)

    def invalidate_cache(self) -> None:
        self._cache = None

    @property
    def cached(self) -> HardwareCapabilities | None:
        return self._cache
