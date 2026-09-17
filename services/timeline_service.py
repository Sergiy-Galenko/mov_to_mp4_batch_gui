"""Multi-clip Timeline Service for Montage Editor.

Supports:
- Multi-clip arrangement on a shared timeline.
- Configurable transitions between clips (fade, wipeleft, wiperight, dissolve, slideup, slidedown, circlecrop, cut).
- Separate background audio/music track with volume, looping, and mixing.
- Building complex FFmpeg filter graphs (xfade, acrossfade, amix) and rendering timeline projects.
"""

from __future__ import annotations

import json
import logging
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

SUPPORTED_TRANSITIONS = {
    "none": "Direct cut",
    "fade": "Crossfade / Fade",
    "wipeleft": "Wipe Left",
    "wiperight": "Wipe Right",
    "dissolve": "Dissolve",
    "slideup": "Slide Up",
    "slidedown": "Slide Down",
    "circlecrop": "Circle Crop",
}


@dataclass
class TimelineClip:
    source_path: str
    in_point: float = 0.0
    out_point: float = 0.0
    clip_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    duration: float = 0.0
    transition_to_next: str = "none"
    transition_duration: float = 1.0

    def __post_init__(self) -> None:
        if self.duration <= 0.0 and self.out_point > self.in_point:
            self.duration = round(self.out_point - self.in_point, 3)

    def effective_duration(self) -> float:
        if self.out_point > self.in_point:
            return round(self.out_point - self.in_point, 3)
        return max(0.0, self.duration)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineClip:
        valid = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class TimelineAudioTrack:
    audio_path: str
    volume: float = 1.0
    loop: bool = False
    offset: float = 0.0
    track_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineAudioTrack:
        valid = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class TimelineProject:
    project_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "Montage Project"
    clips: list[TimelineClip] = field(default_factory=list)
    audio_tracks: list[TimelineAudioTrack] = field(default_factory=list)
    output_format: str = "mp4"
    width: int = 1920
    height: int = 1080
    fps: float = 30.0

    def total_duration(self) -> float:
        """Calculate total timeline duration taking transitions into account."""
        if not self.clips:
            return 0.0
        total = 0.0
        for i, clip in enumerate(self.clips):
            dur = clip.effective_duration()
            if i > 0 and self.clips[i - 1].transition_to_next != "none":
                trans_dur = min(self.clips[i - 1].transition_duration, dur / 2.0)
                total += max(0.0, dur - trans_dur)
            else:
                total += dur
        return round(total, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "clips": [c.to_dict() for c in self.clips],
            "audio_tracks": [a.to_dict() for a in self.audio_tracks],
            "output_format": self.output_format,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "total_duration": self.total_duration(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineProject:
        clips = [TimelineClip.from_dict(c) for c in data.get("clips", [])]
        audio_tracks = [TimelineAudioTrack.from_dict(a) for a in data.get("audio_tracks", [])]
        return cls(
            project_id=data.get("project_id", str(uuid.uuid4())[:8]),
            title=data.get("title", "Montage Project"),
            clips=clips,
            audio_tracks=audio_tracks,
            output_format=data.get("output_format", "mp4"),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            fps=float(data.get("fps", 30.0)),
        )


class TimelineService:
    """Service for building and executing multi-clip timeline rendering commands."""

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"

    def build_render_command(
        self,
        project: TimelineProject,
        output_path: Path | str,
        hwaccel: str = "auto",
    ) -> list[str]:
        """Build FFmpeg command line to render the complete timeline project."""
        if not project.clips:
            raise ValueError("Timeline project has no video clips to render.")

        out_file = Path(output_path).resolve()
        inputs: list[str] = []
        filter_chains: list[str] = []

        # 1. Inputs: add all clips
        for clip in project.clips:
            inputs.extend(["-i", str(Path(clip.source_path).resolve())])

        # Add background audio tracks
        audio_input_start_idx = len(project.clips)
        for audio in project.audio_tracks:
            if audio.loop:
                inputs.extend(["-stream_loop", "-1"])
            inputs.extend(["-i", str(Path(audio.audio_path).resolve())])

        n_clips = len(project.clips)

        # 2. Trim and standardize scale/fps for each video clip
        for i, clip in enumerate(project.clips):
            in_pt = max(0.0, clip.in_point)
            dur = clip.effective_duration()
            # Standardize video resolution, aspect ratio (letterbox/pad), and framerate
            v_filter = (
                f"[{i}:v]trim=start={in_pt:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS,"
                f"scale={project.width}:{project.height}:force_original_aspect_ratio=decrease,"
                f"pad={project.width}:{project.height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,fps={project.fps}[v{i}]"
            )
            filter_chains.append(v_filter)

            # Standardize audio stream
            a_filter = (
                f"[{i}:a]atrim=start={in_pt:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS,"
                f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]"
            )
            filter_chains.append(a_filter)

        # 3. Transitions between clips
        if n_clips == 1:
            last_v = "[v0]"
            last_a = "[a0]"
        else:
            current_v = "[v0]"
            current_a = "[a0]"
            cumulative_offset = project.clips[0].effective_duration()

            for i in range(1, n_clips):
                prev_clip = project.clips[i - 1]
                curr_clip = project.clips[i]
                trans = prev_clip.transition_to_next
                curr_dur = curr_clip.effective_duration()

                if trans and trans != "none" and trans in SUPPORTED_TRANSITIONS:
                    trans_dur = min(prev_clip.transition_duration, curr_dur / 2.0, 5.0)
                    offset = max(0.0, cumulative_offset - trans_dur)
                    next_v = f"[vx{i}]"
                    filter_chains.append(
                        f"{current_v}[v{i}]xfade=transition={trans}:duration={trans_dur:.3f}:offset={offset:.3f}{next_v}"
                    )
                    next_a = f"[ax{i}]"
                    filter_chains.append(
                        f"{current_a}[a{i}]acrossfade=d={trans_dur:.3f}:c1=tri:c2=tri{next_a}"
                    )
                    current_v = next_v
                    current_a = next_a
                    cumulative_offset = offset + curr_dur
                else:
                    # Concat transition
                    next_v = f"[vc{i}]"
                    next_a = f"[ac{i}]"
                    filter_chains.append(
                        f"{current_v}{current_a}[v{i}][a{i}]concat=n=2:v=1:a=1{next_v}{next_a}"
                    )
                    current_v = next_v
                    current_a = next_a
                    cumulative_offset += curr_dur

            last_v = current_v
            last_a = current_a

        # 4. Background audio tracks mixing
        if project.audio_tracks:
            bg_audio_labels: list[str] = []
            for j, audio in enumerate(project.audio_tracks):
                track_input_idx = audio_input_start_idx + j
                label = f"[bga{j}]"
                vol = max(0.0, min(audio.volume, 2.0))
                filter_chains.append(
                    f"[{track_input_idx}:a]volume={vol:.2f},"
                    f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo{label}"
                )
                bg_audio_labels.append(label)

            # Mix primary clip audio with background music
            all_audios = f"{last_a}" + "".join(bg_audio_labels)
            total_tracks = 1 + len(bg_audio_labels)
            filter_chains.append(
                f"{all_audios}amix=inputs={total_tracks}:duration=first:dropout_transition=2[a_final]"
            )
            final_a = "[a_final]"
        else:
            final_a = last_a

        cmd = [self.ffmpeg_path, "-y"]
        cmd.extend(inputs)
        cmd.extend(["-filter_complex", ";".join(filter_chains)])
        cmd.extend(["-map", last_v, "-map", final_a])

        # Codec & container flags
        fmt = project.output_format.lower()
        if fmt in {"mp4", "mov", "m4v"}:
            cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"])
        elif fmt in {"webm"}:
            cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus", "-b:a", "128k"])
        else:
            cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k"])

        cmd.append(str(out_file))
        return cmd

    def render(
        self,
        project: TimelineProject,
        output_path: Path | str,
        progress_cb: Callable[[float], None] | None = None,
    ) -> bool:
        """Execute FFmpeg render pipeline for the timeline project."""
        cmd = self.build_render_command(project, output_path)
        logger.info("Executing timeline render: %s", " ".join(cmd[:10]))
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _, stderr = proc.communicate()
            if proc.returncode != 0:
                logger.error("Timeline render failed with code %d: %s", proc.returncode, stderr[-1000:])
                return False
            if progress_cb:
                progress_cb(1.0)
            return Path(output_path).exists()
        except Exception as exc:
            logger.error("Error during timeline render: %s", exc)
            return False

