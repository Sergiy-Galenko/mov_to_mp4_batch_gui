"""Bounded FFmpeg image pipe: one lossless RGB frame at a time, no disk spool."""

from __future__ import annotations

import contextlib
import io
import math
import subprocess
import threading
import time
from collections.abc import Iterator
from pathlib import Path

from PIL import Image

MAX_FRAME_BYTES = 64 * 1024 * 1024


def _read_exact(stream, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            raise RuntimeError("Truncated FFmpeg frame")
        chunks.extend(chunk)
    return bytes(chunks)


def read_ppm_frame(stream) -> Image.Image | None:
    magic = stream.readline(32)
    if not magic:
        return None
    if magic != b"P6\n":
        raise RuntimeError("Invalid FFmpeg frame header")
    dimensions = stream.readline(128)
    try:
        width, height = map(int, dimensions.split())
    except ValueError as exc:
        raise RuntimeError("Invalid FFmpeg frame dimensions") from exc
    if width <= 0 or height <= 0 or width * height * 3 > MAX_FRAME_BYTES:
        raise RuntimeError("FFmpeg frame exceeds memory limit")
    if stream.readline(32) != b"255\n":
        raise RuntimeError("Unsupported FFmpeg pixel depth")
    data = _read_exact(stream, width * height * 3)
    return Image.open(io.BytesIO(magic + dimensions + b"255\n" + data)).copy()


def sample_frames(
    ffmpeg_path: str, source: Path, interval: float, *, width: int | None = None, timeout: float = 40, cancel: threading.Event | None = None
) -> Iterator[tuple[float, Image.Image]]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Frame sample timeout must be positive and finite")
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("Frame sample interval must be positive and finite")
    filters = f"fps=1/{interval:.9g}"
    if width:
        filters += f",scale={width}:-1"
    command = [
        ffmpeg_path,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-threads",
        "1",
        "-i",
        str(source),
        "-an",
        "-sn",
        "-vf",
        filters,
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-c:v",
        "ppm",
        "-f",
        "image2pipe",
        "pipe:1",
    ]
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    ) as process:
        expired = threading.Event()

        finished = threading.Event()
        deadline = time.monotonic() + timeout

        def watchdog():
            while not finished.wait(0.1):
                timed_out = time.monotonic() >= deadline
                if timed_out or (cancel and cancel.is_set()):
                    if timed_out:
                        expired.set()
                    with contextlib.suppress(OSError):
                        process.kill()
                    return

        guard = threading.Thread(target=watchdog, name="frame-stream-watchdog", daemon=True)
        guard.start()
        try:
            index = 0
            while not (cancel and cancel.is_set()):
                frame = read_ppm_frame(process.stdout)
                if frame is None:
                    break
                yield round(index * interval, 6), frame
                index += 1
            if cancel and cancel.is_set():
                return
            if expired.is_set():
                raise TimeoutError("FFmpeg frame sampling timed out")
            if process.wait(timeout=2):
                raise RuntimeError("FFmpeg frame sampling failed")
        finally:
            finished.set()
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
            guard.join(timeout=0.2)


class FrameDetector:
    """Reuse OpenCV cascades across samples; accept in-memory PIL frames or paths."""

    def __init__(self):
        self._cascades = {}

    def detect(self, image, kind="face"):
        import cv2
        import numpy as np

        if isinstance(image, Image.Image):
            gray = np.asarray(image.convert("L"))
        else:
            gray = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return []
        if kind not in self._cascades:
            filename = "haarcascade_russian_plate_number.xml" if kind == "plate" else "haarcascade_frontalface_default.xml"
            self._cascades[kind] = cv2.CascadeClassifier(cv2.data.haarcascades + filename)
        return self._cascades[kind].detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3 if kind == "plate" else 4)


def open_frame(image):
    return image.copy() if isinstance(image, Image.Image) else Image.open(image)
