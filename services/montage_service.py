"""Montage Editor Service and Session Store.

Manages video & audio montage sessions, metadata extraction,
waveform caching, In/Out trimming bounds, and crop specifications.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.paths import APP_DATA_DIR
from services.media_preview_service import MediaPreviewService

logger = logging.getLogger(__name__)

MONTAGE_STORE_PATH = APP_DATA_DIR / "montage_sessions.json"


@dataclass
class MontageSession:
    file_path: str
    in_point: float = 0.0
    out_point: float = 0.0
    crop_x: int | None = None
    crop_y: int | None = None
    crop_w: int | None = None
    crop_h: int | None = None
    crop_aspect: str = "free"
    audio_enabled: bool = True
    output_format: str = "mp4"
    zoom_level: float = 1.0
    playhead_pos: float = 0.0
    last_modified: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MontageSession:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class MontageSessionStore:
    """Persistent store for montage sessions indexed by absolute canonical file path."""

    def __init__(self, store_path: Path = MONTAGE_STORE_PATH) -> None:
        self.store_path = store_path
        self._sessions: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            self._sessions = {}
            return
        try:
            self._sessions = json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load montage sessions store: %s", exc)
            self._sessions = {}

    def _save(self) -> None:
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self.store_path.write_text(json.dumps(self._sessions, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save montage sessions store: %s", exc)

    def get_session(self, file_path: str | Path) -> dict[str, Any] | None:
        key = str(Path(file_path).resolve())
        return self._sessions.get(key)

    def save_session(self, file_path: str | Path, session_data: dict[str, Any]) -> None:
        key = str(Path(file_path).resolve())
        data = dict(session_data)
        data["file_path"] = key
        data["last_modified"] = time.time()
        self._sessions[key] = data
        self._save()

    def delete_session(self, file_path: str | Path) -> bool:
        key = str(Path(file_path).resolve())
        if key in self._sessions:
            del self._sessions[key]
            self._save()
            return True
        return False


class MontageService:
    """Service providing media probing, waveform generation, and session manipulation for Montage Editor."""

    def __init__(self, ffmpeg_path: str = "", ffprobe_path: str = "", store_path: Path = MONTAGE_STORE_PATH) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.preview_service = MediaPreviewService(ffmpeg_path, ffprobe_path)
        self.session_store = MontageSessionStore(store_path)

    def get_media_metadata(self, file_path: str | Path) -> dict[str, Any]:
        """Probe media file for precise duration, resolution, fps, and stream layout."""
        path = Path(file_path).resolve()
        result: dict[str, Any] = {
            "path": str(path),
            "file_name": path.name,
            "duration": 0.0,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "has_video": True,
            "has_audio": False,
            "vcodec": "",
            "acodec": "",
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        if not path.exists() or not self.ffprobe_path:
            return result

        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                fmt = data.get("format", {})
                duration_str = fmt.get("duration")
                if duration_str:
                    result["duration"] = float(duration_str)

                for stream in data.get("streams", []):
                    codec_type = stream.get("codec_type")
                    if codec_type == "video" and not result["vcodec"]:
                        result["vcodec"] = stream.get("codec_name", "")
                        result["width"] = int(stream.get("width", 1920) or 1920)
                        result["height"] = int(stream.get("height", 1080) or 1080)
                        fps_str = stream.get("r_frame_rate", "") or stream.get("avg_frame_rate", "")
                        if "/" in fps_str:
                            num, den = fps_str.split("/", 1)
                            den_val = float(den) if den else 1.0
                            if den_val > 0:
                                result["fps"] = round(float(num) / den_val, 3)
                        elif fps_str:
                            result["fps"] = float(fps_str)
                    elif codec_type == "audio":
                        result["has_audio"] = True
                        if not result["acodec"]:
                            result["acodec"] = stream.get("codec_name", "")
        except Exception as exc:
            logger.warning("Error probing media for montage: %s", exc)

        return result

    def get_audio_waveform(self, file_path: str | Path, width: int = 1200, height: int = 100) -> str:
        """Return cached path or generate waveform PNG for audio."""
        path = Path(file_path).resolve()
        waveform = self.preview_service.audio_waveform(path, width=width, height=height)
        return waveform or ""

    def get_session(self, file_path: str | Path, existing_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Retrieve stored session or initialize one from existing task overrides and media metadata."""
        stored = self.session_store.get_session(file_path)
        meta = self.get_media_metadata(file_path)
        duration = float(meta.get("duration", 0.0) or 0.0)

        if stored:
            session = dict(stored)
            if session.get("out_point", 0.0) <= 0.0 or session.get("out_point", 0.0) > duration:
                session["out_point"] = duration
            session["metadata"] = meta
            return session

        overrides = existing_overrides or {}
        trim_start = float(overrides.get("trim_start") or 0.0)
        trim_end = float(overrides.get("trim_end") or duration)
        if trim_end <= 0.0 or trim_end > duration:
            trim_end = duration

        session_obj = MontageSession(
            file_path=str(Path(file_path).resolve()),
            in_point=max(0.0, trim_start),
            out_point=max(trim_start, trim_end),
            crop_x=overrides.get("crop_x"),
            crop_y=overrides.get("crop_y"),
            crop_w=overrides.get("crop_w"),
            crop_h=overrides.get("crop_h"),
            crop_aspect="free",
            audio_enabled=not bool(overrides.get("remove_audio", False)),
            output_format=overrides.get("out_video_format", "mp4"),
            zoom_level=1.0,
            playhead_pos=max(0.0, trim_start),
        )
        res = session_obj.to_dict()
        res["metadata"] = meta
        return res

    def save_session(self, file_path: str | Path, session_data: dict[str, Any]) -> None:
        """Persist session data."""
        self.session_store.save_session(file_path, session_data)

