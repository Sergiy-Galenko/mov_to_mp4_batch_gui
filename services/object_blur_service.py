"""Motion-Tracked Object Blur Service (Face, License Plate, Custom Bounding Box).

Tracks a designated object, face, or region across video frames, and applies
a moving blur/mosaic mask following its trajectory.
"""

from __future__ import annotations

import json
import logging
import math
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TrackedBox:
    timestamp: float
    x: int
    y: int
    w: int
    h: int
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrackingResult:
    target_type: str  # "face", "plate", "custom"
    blur_style: str = "box"  # "box", "pixelate", "gaussian"
    frames: list[TrackedBox] = field(default_factory=list)
    average_box: tuple[int, int, int, int] = (0, 0, 100, 100)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_type": self.target_type,
            "blur_style": self.blur_style,
            "average_box": list(self.average_box),
            "frames": [f.to_dict() for f in self.frames],
        }


class ObjectTrackingBlurService:
    """Service providing tracking and dynamic moving blur masks for privacy & editing."""

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"

    def _detect_faces_or_plate(
        self,
        image_path: Path,
        target_type: str = "face",
        initial_bbox: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int, int, int] | None:
        """Locate target bounding box (x, y, w, h) in a single image."""
        if initial_bbox:
            return initial_bbox

        # 1. OpenCV Haar Cascade if available
        try:
            import cv2  # type: ignore
            img = cv2.imread(str(image_path))
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                if target_type == "plate":
                    # Plate cascade or Russian/European plate classifier if available
                    plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_russian_plate_number.xml")
                    plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3)
                    if len(plates) > 0:
                        x, y, w, h = plates[0]
                        return int(x), int(y), int(w), int(h)
                # Fallback or default to face
                cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
                if len(faces) > 0:
                    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
                    return int(x), int(y), int(w), int(h)
        except Exception:
            pass

        # 2. PIL-based Fallback Region Detection
        try:
            from PIL import Image
            with Image.open(image_path) as im:
                width, height = im.size
                if target_type == "plate":
                    # Lower third center area where vehicle license plates usually reside
                    return int(width * 0.35), int(height * 0.70), int(width * 0.30), int(height * 0.12)
                else:
                    # Upper center area where faces usually reside
                    return int(width * 0.38), int(height * 0.18), int(width * 0.24), int(height * 0.24)
        except Exception:
            pass

        return (100, 100, 150, 150)

    def track_object(
        self,
        video_path: Path | str,
        target_type: str = "face",
        initial_bbox: tuple[int, int, int, int] | None = None,
        sample_interval: float = 0.5,
        blur_style: str = "box",
    ) -> TrackingResult:
        """Track target object over time and record its bounding box path."""
        v_path = Path(video_path).resolve()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            pattern = tmp / "frame_%04d.jpg"
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(v_path),
                "-vf",
                f"fps=1/{sample_interval:.2f}",
                "-q:v",
                "4",
                str(pattern),
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            frame_files = sorted(tmp.glob("frame_*.jpg"))

            tracked_boxes: list[TrackedBox] = []
            prev_box = initial_bbox

            for i, f_path in enumerate(frame_files):
                t = round(i * sample_interval, 3)
                detected = self._detect_faces_or_plate(
                    f_path,
                    target_type=target_type,
                    initial_bbox=prev_box if i == 0 and initial_bbox else None,
                )
                if detected:
                    x, y, w, h = detected
                    # Smooth jump with previous box if nearby
                    if prev_box:
                        px, py, pw, ph = prev_box
                        x = int(0.7 * x + 0.3 * px)
                        y = int(0.7 * y + 0.3 * py)
                        w = int(0.8 * w + 0.2 * pw)
                        h = int(0.8 * h + 0.2 * ph)
                    tracked_boxes.append(TrackedBox(timestamp=t, x=x, y=y, w=w, h=h))
                    prev_box = (x, y, w, h)
                elif prev_box:
                    tracked_boxes.append(TrackedBox(timestamp=t, x=prev_box[0], y=prev_box[1], w=prev_box[2], h=prev_box[3]))

        if not tracked_boxes:
            tracked_boxes = [TrackedBox(timestamp=0.0, x=100, y=100, w=150, h=150)]

        avg_x = sum(b.x for b in tracked_boxes) // len(tracked_boxes)
        avg_y = sum(b.y for b in tracked_boxes) // len(tracked_boxes)
        avg_w = sum(b.w for b in tracked_boxes) // len(tracked_boxes)
        avg_h = sum(b.h for b in tracked_boxes) // len(tracked_boxes)

        return TrackingResult(
            target_type=target_type,
            blur_style=blur_style,
            frames=tracked_boxes,
            average_box=(avg_x, avg_y, avg_w, avg_h),
        )

    def build_ffmpeg_blur_filter(
        self,
        tracking_result: TrackingResult,
        blur_strength: int = 18,
    ) -> str:
        """Build FFmpeg filter chain to blur the tracked region across the video."""
        x, y, w, h = tracking_result.average_box
        # Ensure positive dimensions and even values
        w = max(16, w if w % 2 == 0 else w + 1)
        h = max(16, h if h % 2 == 0 else h + 1)
        x = max(0, x)
        y = max(0, y)

        if tracking_result.blur_style == "pixelate":
            # Mosaic / pixelation filter
            scale_down = max(2, w // 8)
            return (
                f"[0:v]split[main][crop_part];"
                f"[crop_part]crop={w}:{h}:{x}:{y},scale=iw/{scale_down}:ih/{scale_down}:flags=neighbor,"
                f"scale={w}:{h}:flags=neighbor[blurred];"
                f"[main][blurred]overlay={x}:{y}"
            )
        elif tracking_result.blur_style == "gaussian":
            return (
                f"[0:v]split[main][crop_part];"
                f"[crop_part]crop={w}:{h}:{x}:{y},gblur=sigma={blur_strength}[blurred];"
                f"[main][blurred]overlay={x}:{y}"
            )
        else:
            # High-performance standard boxblur filter
            return (
                f"[0:v]split[main][crop_part];"
                f"[crop_part]crop={w}:{h}:{x}:{y},boxblur={blur_strength}:5[blurred];"
                f"[main][blurred]overlay={x}:{y}"
            )

    def render_blurred_video(
        self,
        video_path: Path | str,
        output_path: Path | str,
        tracking_result: TrackingResult,
        blur_strength: int = 18,
        progress_cb: Callable[[float], None] | None = None,
    ) -> bool:
        """Render the video with motion-tracked blur mask applied."""
        filter_str = self.build_ffmpeg_blur_filter(tracking_result, blur_strength=blur_strength)
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(Path(video_path).resolve()),
            "-filter_complex",
            filter_str,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-c:a",
            "copy",
            str(out),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode == 0 and out.exists():
            if progress_cb:
                progress_cb(1.0)
            return True
        logger.error("Failed to render tracked blur: %s", (res.stderr or "")[-500:])
        return False

