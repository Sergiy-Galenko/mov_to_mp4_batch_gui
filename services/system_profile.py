"""Startup inventory and conservative workload recommendations (never quality presets)."""
from __future__ import annotations

import json
import os
import platform

import psutil

from services.background_job import BackgroundJob

GIB = 1024 ** 3
HARDWARE_ENCODERS = {
    "h264_videotoolbox": "VideoToolbox H.264", "hevc_videotoolbox": "VideoToolbox HEVC",
    "prores_videotoolbox": "VideoToolbox ProRes", "h264_nvenc": "NVENC H.264",
    "hevc_nvenc": "NVENC HEVC", "h264_qsv": "QSV H.264", "hevc_qsv": "QSV HEVC",
    "h264_amf": "AMF H.264", "hevc_amf": "AMF HEVC",
}


def recommend_workload(logical_cpus: int, total_gib: float, available_gib: float) -> dict:
    # Reserve memory for the desktop and allow ~3 GiB per simultaneous video job.
    memory_slots = max(1, int(max(0, min(total_gib - 3, available_gib - 2)) // 3))
    workers = max(1, min(4, logical_cpus // 4, memory_slots))
    return {
        "concurrency_limit": workers,
        "cpu_load_limit": 75 if total_gib < 12 else 85,
        "gpu_load_limit": 90,
        "low_resource_mode": total_gib < 12 or available_gib < 4 or logical_cpus <= 4,
    }


def scan_system(context, ffmpeg_path: str) -> dict:
    context.progress("system", 10)
    system = platform.system()
    logical = psutil.cpu_count() or os.cpu_count() or 1
    memory = psutil.virtual_memory()
    report = {
        "os": "macOS" if system == "Darwin" else system,
        "version": platform.mac_ver()[0] if system == "Darwin" else platform.release(),
        "architecture": platform.machine(), "cpu": platform.processor() or platform.machine(),
        "logical_cpus": logical, "physical_cpus": psutil.cpu_count(logical=False) or logical,
        "ram_gib": round(memory.total / GIB, 1), "available_gib": round(memory.available / GIB, 1),
        "gpu": [], "encoders": [], "encoding_checked": False, "warnings": [],
    }
    context.progress("hardware", 30)
    try:
        if system == "Darwin":
            cpu = context.run(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"], timeout=5)
            if cpu.returncode == 0:
                report["cpu"] = cpu.stdout.strip()
            gpu = context.run(["/usr/sbin/system_profiler", "SPDisplaysDataType", "-json"], timeout=10)
            if gpu.returncode == 0:
                report["gpu"] = [x.get("sppci_model", x.get("_name", "")) for x in json.loads(gpu.stdout).get("SPDisplaysDataType", [])]
        elif system == "Windows":
            query = "@{cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name); gpu=@(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name)} | ConvertTo-Json -Compress"
            hardware = context.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", query], timeout=15)
            if hardware.returncode == 0:
                data = json.loads(hardware.stdout)
                report["cpu"] = data.get("cpu") or report["cpu"]
                report["gpu"] = data.get("gpu") or []
    except (OSError, TimeoutError, ValueError) as exc:
        report["warnings"].append(str(exc))
    context.check()
    context.progress("encoders", 50)
    if ffmpeg_path:
        try:
            listing = context.run([ffmpeg_path, "-hide_banner", "-encoders"], timeout=15)
            if listing.returncode:
                raise RuntimeError(listing.stderr.strip())
            report["encoding_checked"] = True
            advertised = {line.split()[1] for line in listing.stdout.splitlines() if len(line.split()) > 1}
            candidates = sorted(HARDWARE_ENCODERS.keys() & advertised)
            for index, encoder in enumerate(candidates):
                context.check()
                context.progress("encoders", 50 + int(35 * index / len(candidates)))
                pixel = "ayuv64le" if encoder == "prores_videotoolbox" else "yuv420p"
                command = [ffmpeg_path, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                           "color=size=256x256:rate=1", "-frames:v", "1", "-an", "-c:v", encoder, "-pix_fmt", pixel]
                if encoder.endswith("_videotoolbox"):
                    command += ["-allow_sw", "0"]
                try:
                    if context.run([*command, "-f", "null", "-"], timeout=6).returncode == 0:
                        report["encoders"].append(HARDWARE_ENCODERS[encoder])
                except TimeoutError:
                    report["warnings"].append(encoder + ": timeout")
        except (OSError, RuntimeError, TimeoutError) as exc:
            report["warnings"].append(str(exc))
    else:
        report["warnings"].append("FFmpeg is unavailable; encoder checks were skipped.")
    context.progress("tuning", 90)
    report["recommendation"] = recommend_workload(logical, memory.total / GIB, memory.available / GIB)
    return report


class SystemProfile(BackgroundJob):
    def scan(self, ffmpeg_path):
        return self.start_job(lambda context: scan_system(context, ffmpeg_path))
