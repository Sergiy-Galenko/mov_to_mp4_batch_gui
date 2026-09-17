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
from services.object_blur_service import ObjectTrackingBlurService
from services.proxy_service import ProxyService
from services.smart_reframe_service import SmartReframeService
from services.speaker_diarization_service import DiarizationResult, SpeakerDiarizationService
from services.subtitle_style_service import StyledSubtitleLine, SubtitleStyleService
from services.subtitle_translation_service import SubtitleTranslationService
from services.timeline_service import TimelineClip, TimelineProject, TimelineService

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
    use_proxy: bool = False
    timeline_project: dict[str, Any] = field(default_factory=dict)
    diarization_data: dict[str, Any] = field(default_factory=dict)
    subtitle_template: str = "tiktok_pop"
    reframe_aspect: str = "free"
    reframe_active: bool = False
    blur_target_type: str = "none"
    blur_tracking_data: dict[str, Any] = field(default_factory=dict)
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
        self.timeline_service = TimelineService(ffmpeg_path)
        self.proxy_service = ProxyService(ffmpeg_path)
        self.diarization_service = SpeakerDiarizationService(ffmpeg_path)
        self.subtitle_style_service = SubtitleStyleService()
        self.subtitle_translation_service = SubtitleTranslationService(ffmpeg_path)
        self.reframe_service = SmartReframeService(ffmpeg_path, ffprobe_path)
        self.blur_service = ObjectTrackingBlurService(ffmpeg_path)

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

    # 1. Proxy management
    def create_or_get_proxy(self, file_path: str | Path, target_height: int = 720) -> str:
        res = self.proxy_service.generate_proxy(file_path, target_height=target_height)
        return str(res) if res else ""

    def is_proxy_ready(self, file_path: str | Path, target_height: int = 720) -> bool:
        return self.proxy_service.is_proxy_ready(file_path, target_height=target_height)

    def get_proxy_path(self, file_path: str | Path, target_height: int = 720) -> str:
        return str(self.proxy_service.get_proxy_path(file_path, target_height=target_height))

    # 2. Timeline management
    def get_timeline_project(self, file_path: str | Path) -> dict[str, Any]:
        session = self.get_session(file_path)
        proj_dict = session.get("timeline_project")
        if proj_dict:
            return proj_dict

        # Create default single-clip project
        meta = session.get("metadata", {})
        clip = TimelineClip(
            source_path=str(Path(file_path).resolve()),
            in_point=float(session.get("in_point", 0.0) or 0.0),
            out_point=float(session.get("out_point", meta.get("duration", 0.0)) or meta.get("duration", 0.0)),
            duration=float(meta.get("duration", 0.0) or 0.0),
        )
        proj = TimelineProject(
            title=Path(file_path).name,
            clips=[clip],
            output_format=session.get("output_format", "mp4"),
            width=int(meta.get("width", 1920) or 1920),
            height=int(meta.get("height", 1080) or 1080),
            fps=float(meta.get("fps", 30.0) or 30.0),
        )
        return proj.to_dict()

    def save_timeline_project(self, file_path: str | Path, project_data: dict[str, Any]) -> None:
        session = self.get_session(file_path)
        session["timeline_project"] = project_data
        self.save_session(file_path, session)

    def render_timeline(self, project_data: dict[str, Any], output_path: str | Path, prefer_proxy: bool = False) -> bool:
        project = TimelineProject.from_dict(project_data)
        if not prefer_proxy:
            project = self.proxy_service.swap_proxies_for_masters(project)
        return self.timeline_service.render(project, output_path)

    # 3. Speaker diarization
    def diarize_media(
        self,
        file_path: str | Path,
        segments: list[dict[str, Any]],
        num_speakers: int = 2,
        language: str = "uk",
    ) -> dict[str, Any]:
        result = self.diarization_service.diarize_segments(file_path, segments, num_speakers=num_speakers, language=language)
        session = self.get_session(file_path)
        session["diarization_data"] = result.to_dict()
        self.save_session(file_path, session)
        return result.to_dict()

    def apply_speaker_aliases(self, diarization_dict: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
        res = DiarizationResult.from_dict(diarization_dict)
        updated = self.diarization_service.apply_aliases(res, aliases)
        return updated.to_dict()

    def export_diarized_subtitles(
        self,
        diarization_dict: dict[str, Any],
        output_path: str | Path,
        format_name: str = "srt",
    ) -> str:
        res = DiarizationResult.from_dict(diarization_dict)
        if format_name.lower() == "vtt":
            return self.diarization_service.export_vtt(res, output_path)
        return self.diarization_service.export_srt(res, output_path)

    # 4. Styled subtitles (Word highlights / Karaoke)
    def generate_styled_subtitles(
        self,
        segments: list[dict[str, Any]],
        template: str = "tiktok_pop",
        output_path: str | Path = "",
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> str:
        lines: list[StyledSubtitleLine] = []
        for s in segments:
            lines.append(
                StyledSubtitleLine(
                    start=float(s.get("start", 0.0)),
                    end=float(s.get("end", 0.0)),
                    text=str(s.get("text", "")).strip(),
                    speaker=str(s.get("speaker", "") or s.get("speaker_name", "")).strip(),
                )
            )
        if output_path:
            p = self.subtitle_style_service.export_ass_file(lines, output_path, template_name=template, res_x=res_x, res_y=res_y)
            return str(p)
        return self.subtitle_style_service.build_ass_script(lines, template_name=template, res_x=res_x, res_y=res_y)

    # 5. Subtitle translation
    def translate_subtitles(
        self,
        segments: list[dict[str, Any]],
        target_languages: list[str],
        source_lang: str = "auto",
    ) -> dict[str, Any]:
        res = self.subtitle_translation_service.translate_segments(segments, target_languages=target_languages, source_language=source_lang)
        return res.to_dict()

    # 6. Smart vertical reframe
    def calculate_smart_reframe(self, file_path: str | Path, aspect: str = "9:16") -> dict[str, Any]:
        result = self.reframe_service.analyze_reframe(file_path, target_aspect=aspect)
        session = self.get_session(file_path)
        session["reframe_aspect"] = aspect
        session["reframe_active"] = True
        session["crop_w"] = result.crop_w
        session["crop_h"] = result.crop_h
        session["crop_x"] = result.average_x
        session["crop_y"] = 0
        self.save_session(file_path, session)
        return result.to_dict()

    # 7. Motion-tracked object blur
    def track_and_blur(
        self,
        file_path: str | Path,
        target_type: str = "face",
        initial_bbox: list[int] | None = None,
        blur_style: str = "box",
    ) -> dict[str, Any]:
        bbox_tuple = tuple(initial_bbox) if (initial_bbox and len(initial_bbox) == 4) else None
        res = self.blur_service.track_object(file_path, target_type=target_type, initial_bbox=bbox_tuple, blur_style=blur_style)
        session = self.get_session(file_path)
        session["blur_target_type"] = target_type
        session["blur_tracking_data"] = res.to_dict()
        self.save_session(file_path, session)
        return res.to_dict()
