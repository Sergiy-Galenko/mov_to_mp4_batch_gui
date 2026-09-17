"""Smart Vertical Reframe (Auto-Crop 16:9 -> 9:16) Service.

Automatically detects faces and moving points of interest in landscape videos,
calculates an EMA-smoothed camera pan trajectory, and crops the video to vertical
format (9:16 for TikTok, Reels, Shorts) keeping the subject centered.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KeyframeFocus:
    timestamp: float
    center_x: float  # Normalized [0.0, 1.0]
    center_y: float  # Normalized [0.0, 1.0]
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReframeResult:
    aspect_ratio: str = "9:16"
    crop_w: int = 608
    crop_h: int = 1080
    keyframes: list[KeyframeFocus] = field(default_factory=list)
    average_x: int = 656
    filter_expr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "aspect_ratio": self.aspect_ratio,
            "crop_w": self.crop_w,
            "crop_h": self.crop_h,
            "average_x": self.average_x,
            "keyframes": [k.to_dict() for k in self.keyframes],
            "filter_expr": self.filter_expr,
        }


class SmartReframeService:
    """Detects primary subjects and calculates smooth vertical crop parameters."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.ffprobe_path = ffprobe_path or "ffprobe"

    def probe_dimensions(self, video_path: Path | str) -> tuple[int, int, float]:
        """Return (width, height, duration) of the video."""
        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(Path(video_path).resolve()),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                fmt = data.get("format", {})
                duration = float(fmt.get("duration", 10.0) or 10.0)
                for s in data.get("streams", []):
                    if s.get("codec_type") == "video":
                        w = int(s.get("width", 1920) or 1920)
                        h = int(s.get("height", 1080) or 1080)
                        return w, h, duration
        except Exception as exc:
            logger.warning("Failed to probe video dimensions for reframe: %s", exc)
        return 1920, 1080, 10.0

    def _extract_sample_frames(self, video_path: Path, tmp_dir: Path, interval_sec: float = 1.0) -> list[tuple[float, Path]]:
        """Extract lightweight JPEG thumbnails at periodic intervals."""
        pattern = tmp_dir / "frame_%04d.jpg"
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps=1/{interval_sec:.2f},scale=320:-1",
            "-q:v",
            "4",
            str(pattern),
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception as exc:
            logger.debug("Failed to extract frames with ffmpeg: %s", exc)
        frames = sorted(tmp_dir.glob("frame_*.jpg"))
        return [(i * interval_sec, f) for i, f in enumerate(frames)]

    def _detect_subject_center(self, image_path: Path) -> float:
        """Find the normalized horizontal center (0.0 - 1.0) of the primary face/subject in the frame."""
        # 1. Try OpenCV Haar Cascade if installed
        try:
            import cv2  # type: ignore

            img = cv2.imread(str(image_path))
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # Load default frontal face cascade if available
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                face_cascade = cv2.CascadeClassifier(cascade_path)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))
                if len(faces) > 0:
                    # Choose largest detected face
                    largest = max(faces, key=lambda b: b[2] * b[3])
                    fx, _fy, fw, _fh = largest
                    face_center_x = (fx + fw / 2.0) / img.shape[1]
                    return float(face_center_x)
        except Exception:
            pass

        # 2. PIL-based Luminance & Edge Saliency Fallback
        try:
            from PIL import Image

            with Image.open(image_path) as im:
                im_small = im.convert("L").resize((64, 36))
                pixels = im_small.load()
                # Focus primarily on upper-middle portion (where heads/faces typically are)
                w, h = im_small.size
                total_weight = 0.0
                weighted_x = 0.0
                for y in range(int(h * 0.1), int(h * 0.7)):
                    for x in range(w):
                        val = pixels[x, y]
                        # Contrast from average background
                        weight = abs(val - 128) + 10
                        weighted_x += x * weight
                        total_weight += weight
                if total_weight > 0:
                    return float(round((weighted_x / total_weight) / w, 3))
        except Exception:
            pass

        return 0.5

    def analyze_reframe(
        self,
        video_path: Path | str,
        target_aspect: str = "9:16",
        sample_interval: float = 1.0,
        smoothing_factor: float = 0.25,
        deadband: float = 0.04,
    ) -> ReframeResult:
        """Analyze video and compute smooth vertical crop window coordinates."""
        v_path = Path(video_path).resolve()
        orig_w, orig_h, _ = self.probe_dimensions(v_path)

        # Calculate crop dimensions
        if target_aspect == "9:16":
            crop_h = orig_h
            crop_w = round(crop_h * 9.0 / 16.0)
            if crop_w % 2 != 0:
                crop_w += 1
            if crop_w > orig_w:
                crop_w = orig_w
                crop_h = round(crop_w * 16.0 / 9.0)
                if crop_h % 2 != 0:
                    crop_h += 1
        elif target_aspect == "1:1":
            crop_dim = min(orig_w, orig_h)
            crop_w = crop_dim - (crop_dim % 2)
            crop_h = crop_w
        elif target_aspect == "4:5":
            crop_h = orig_h
            crop_w = round(crop_h * 4.0 / 5.0)
            if crop_w % 2 != 0:
                crop_w += 1
        else:
            crop_w, crop_h = orig_w, orig_h

        max_x = max(0, orig_w - crop_w)

        with tempfile.TemporaryDirectory() as tmp:
            samples = self._extract_sample_frames(v_path, Path(tmp), interval_sec=sample_interval)
            keyframes: list[KeyframeFocus] = []

            current_smooth_center = 0.5
            for t, fpath in samples:
                detected_center = self._detect_subject_center(fpath)
                # Apply deadband: ignore tiny shifts
                if abs(detected_center - current_smooth_center) > deadband:
                    # Exponential Moving Average (EMA)
                    current_smooth_center = smoothing_factor * detected_center + (1.0 - smoothing_factor) * current_smooth_center
                keyframes.append(KeyframeFocus(timestamp=t, center_x=round(current_smooth_center, 3), center_y=0.5))

        if keyframes:
            avg_norm_x = sum(k.center_x for k in keyframes) / len(keyframes)
        else:
            avg_norm_x = 0.5

        # Map normalized center to pixel X position
        target_center_px = avg_norm_x * orig_w
        optimal_x = round(target_center_px - crop_w / 2.0)
        optimal_x = max(0, min(max_x, optimal_x))
        # Ensure even alignment
        if optimal_x % 2 != 0:
            optimal_x += 1

        filter_expr = f"crop={crop_w}:{crop_h}:{optimal_x}:0"

        return ReframeResult(
            aspect_ratio=target_aspect,
            crop_w=crop_w,
            crop_h=crop_h,
            keyframes=keyframes,
            average_x=optimal_x,
            filter_expr=filter_expr,
        )

    def render_reframe(
        self,
        video_path: Path | str,
        output_path: Path | str,
        target_aspect: str = "9:16",
        progress_cb: Callable[[float], None] | None = None,
    ) -> bool:
        """Render a vertically reframed video file."""
        result = self.analyze_reframe(video_path, target_aspect=target_aspect)
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(Path(video_path).resolve()),
            "-vf",
            result.filter_expr,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
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
        logger.error("Failed to render smart reframe: %s", (res.stderr or "")[-500:])
        return False
