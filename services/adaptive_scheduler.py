"""Shared admission budgets for a conversion batch, independent of Qt and FFmpeg."""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass

import psutil

from app.constants import HW_ENCODER_MAP
from app.models import ConversionSettings, MediaInfo, TaskItem
from services.resource_monitor import ResourceMonitor

MIB = 1024**2


@dataclass(frozen=True)
class TaskCost:
    cpu_threads: int
    memory_bytes: int
    hardware_sessions: int = 0
    disk_slots: int = 1


class AdaptiveScheduler:
    def __init__(
        self,
        workers: int,
        monitor: ResourceMonitor | None = None,
        *,
        cpu_threads: int | None = None,
        memory_bytes: int | None = None,
        hardware_sessions: int = 2,
        disk_slots: int = 2,
    ):
        self.workers = max(1, workers)
        self.cpu_threads = max(1, cpu_threads or os.cpu_count() or 1)
        self.memory_bytes = max(
            256 * MIB, memory_bytes if memory_bytes is not None else int(max(256 * MIB, psutil.virtual_memory().available - 1024 * MIB))
        )
        self.hardware_sessions = max(1, hardware_sessions)
        self.disk_slots = max(1, disk_slots)
        self.monitor = monitor or ResourceMonitor()
        self._condition = threading.Condition()
        self._used = TaskCost(0, 0, 0, 0)
        self._active = 0

    def estimate(self, task: TaskItem, settings: ConversionSettings, info: MediaInfo | None, ffmpeg) -> TaskCost:
        pixels = (info.width or 1920) * (info.height or 1080) if info else 1920 * 1080
        lightweight = settings.operation in {"thumbnail", "subtitle_extract"} or task.media_type == "subtitle"
        hardware = False
        if (
            task.media_type == "video"
            and settings.operation in {"convert", "subtitle_burn"}
            and not settings.target_size_mb
            and hasattr(ffmpeg, "select_encoder")
        ):
            codec = ffmpeg.resolve_codec("." + settings.out_video_format.lstrip("."), settings.video_codec)
            _, hardware = ffmpeg.select_encoder(codec, HW_ENCODER_MAP.get(settings.hw_encoder, "auto"))
        threads = 1 if lightweight else max(1, self.cpu_threads // min(self.workers, self.disk_slots))
        memory = 128 * MIB if lightweight else max(256 * MIB, pixels * 96)
        if settings.operation == "auto_subtitle":
            memory = max(memory, 3 * 1024 * MIB)
        return TaskCost(min(self.cpu_threads, threads), min(self.memory_bytes, memory), int(hardware))

    def _fits(self, cost: TaskCost, settings: ConversionSettings) -> bool:
        used = self._used
        if (
            self._active >= self.workers
            or used.cpu_threads + cost.cpu_threads > self.cpu_threads
            or used.memory_bytes + cost.memory_bytes > self.memory_bytes
            or used.hardware_sessions + cost.hardware_sessions > self.hardware_sessions
            or used.disk_slots + cost.disk_slots > self.disk_slots
        ):
            return False
        sample = self.monitor.sample()
        cpu, gpu = sample.get("cpu"), sample.get("gpu")
        if cpu is not None and cpu >= max(1, min(100, settings.cpu_load_limit)):
            return False
        if cost.hardware_sessions and gpu is not None and gpu >= max(1, min(100, settings.gpu_load_limit)):
            return False
        available = sample.get("available_bytes")
        return available is None or cost.memory_bytes <= max(256 * MIB, available - 512 * MIB)

    @contextmanager
    def reserve(
        self,
        cost: TaskCost,
        settings: ConversionSettings,
        stop: threading.Event,
        pause: threading.Event,
        skip: threading.Event | None = None,
    ):
        acquired = False
        with self._condition:
            while not stop.is_set() and not (skip and skip.is_set()):
                if not pause.is_set() and self._fits(cost, settings):
                    u = self._used
                    self._used = TaskCost(
                        u.cpu_threads + cost.cpu_threads,
                        u.memory_bytes + cost.memory_bytes,
                        u.hardware_sessions + cost.hardware_sessions,
                        u.disk_slots + cost.disk_slots,
                    )
                    self._active += 1
                    acquired = True
                    break
                self._condition.wait(timeout=0.1)
        try:
            yield acquired
        finally:
            if acquired:
                with self._condition:
                    u = self._used
                    self._used = TaskCost(
                        u.cpu_threads - cost.cpu_threads,
                        u.memory_bytes - cost.memory_bytes,
                        u.hardware_sessions - cost.hardware_sessions,
                        u.disk_slots - cost.disk_slots,
                    )
                    self._active -= 1
                    self._condition.notify_all()


def bound_ffmpeg_threads(command: list[str], threads: int) -> list[str]:
    """Limit decoders, filters and encoders, including encoders with private pools."""
    budget = str(max(1, threads))
    result = [*command[:2], "-filter_threads", budget, "-filter_complex_threads", budget]
    for argument in command[2:-1]:
        if argument == "-i":
            result += ["-threads", budget]
        result.append(argument)
    result += ["-threads", budget]
    encoder = command[command.index("-c:v") + 1] if "-c:v" in command else ""
    if encoder == "libx265":
        option, value = "-x265-params", f"pools={budget}:frame-threads={budget}"
    elif encoder == "libsvtav1":
        option, value = "-svtav1-params", f"lp={budget}"
    else:
        option = None
    if option:
        if option in result:
            index = result.index(option) + 1
            result[index] += ":" + value
        else:
            result += [option, value]
    return [*result, command[-1]]
