"""Proxy Video Generation and Management Service for Montage Editor.

Provides fast, lightweight proxies (e.g. 720p/540p H.264 with short keyframe intervals)
for smooth seeking and playback during editing.
Provides seamless replacement of proxies with full-resolution originals upon final export.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

from app.paths import APP_DATA_DIR
from services.timeline_service import TimelineClip, TimelineProject

logger = logging.getLogger(__name__)

DEFAULT_PROXY_DIR = APP_DATA_DIR / "proxies"


class ProxyService:
    """Manages lightweight video proxy creation, caching, and master-swap mapping."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", proxy_dir: Path = DEFAULT_PROXY_DIR) -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.proxy_dir = Path(proxy_dir)
        self.proxy_dir.mkdir(parents=True, exist_ok=True)
        self._master_to_proxy: dict[str, str] = {}
        self._proxy_to_master: dict[str, str] = {}

    def _generate_cache_key(self, source_path: Path | str, target_height: int = 720) -> str:
        p = Path(source_path).resolve()
        stat = p.stat() if p.exists() else None
        mtime = str(stat.st_mtime) if stat else "0"
        size = str(stat.st_size) if stat else "0"
        raw = f"{p}_{mtime}_{size}_{target_height}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def get_proxy_path(self, source_path: Path | str, target_height: int = 720) -> Path:
        """Return the destination path where the proxy for the given source is cached."""
        key = self._generate_cache_key(source_path, target_height)
        stem = Path(source_path).stem
        return self.proxy_dir / f"proxy_{stem}_{target_height}p_{key}.mp4"

    def is_proxy_ready(self, source_path: Path | str, target_height: int = 720) -> bool:
        """Check if a valid proxy file already exists on disk."""
        target = self.get_proxy_path(source_path, target_height)
        return target.exists() and target.stat().st_size > 1024

    def generate_proxy(
        self,
        source_path: Path | str,
        target_height: int = 720,
        progress_cb: Callable[[float], None] | None = None,
    ) -> Path | None:
        """Transcode a fast lightweight proxy with small GOP for smooth scrubbing."""
        src = Path(source_path).resolve()
        if not src.exists():
            logger.warning("Source file does not exist: %s", src)
            return None

        out = self.get_proxy_path(src, target_height)
        if self.is_proxy_ready(src, target_height):
            self._register_pair(str(src), str(out))
            if progress_cb:
                progress_cb(1.0)
            return out

        out.parent.mkdir(parents=True, exist_ok=True)
        # Fast encoding: ultrafast preset, 720p/540p max height, GOP size 15 for instant seek
        scale_filter = f"scale=-2:'min({target_height},ih)':force_original_aspect_ratio=decrease"
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(src),
            "-vf",
            scale_filter,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "fastdecode",
            "-crf",
            "28",
            "-g",
            "15",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(out),
        ]

        logger.info("Generating proxy for %s: %s", src.name, out.name)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode == 0 and out.exists() and out.stat().st_size > 1024:
                self._register_pair(str(src), str(out))
                if progress_cb:
                    progress_cb(1.0)
                return out
            logger.warning("Failed to generate proxy: %s", (res.stderr or "")[-500:])
            return None
        except Exception as exc:
            logger.error("Exception generating proxy for %s: %s", src, exc)
            return None

    def _register_pair(self, master_path: str, proxy_path: str) -> None:
        m_norm = str(Path(master_path).resolve())
        p_norm = str(Path(proxy_path).resolve())
        self._master_to_proxy[m_norm] = p_norm
        self._proxy_to_master[p_norm] = m_norm

    def resolve_source(self, path: Path | str, prefer_proxy: bool = False, target_height: int = 720) -> Path:
        """Return the proxy path if requested and ready, else the original path."""
        src = Path(path).resolve()
        if not prefer_proxy:
            # If the given path is a proxy, map it back to master
            master = self._proxy_to_master.get(str(src))
            return Path(master) if master and Path(master).exists() else src

        if self.is_proxy_ready(src, target_height):
            return self.get_proxy_path(src, target_height)
        return src

    def swap_proxies_for_masters(self, project: TimelineProject) -> TimelineProject:
        """Replace all proxy clip paths with original master files for final export."""
        swapped_clips: list[TimelineClip] = []
        for clip in project.clips:
            resolved_src = clip.source_path
            p_norm = str(Path(clip.source_path).resolve())
            if p_norm in self._proxy_to_master:
                resolved_src = self._proxy_to_master[p_norm]
            else:
                # Check if the filename itself is in proxy format
                stem = Path(clip.source_path).stem
                if stem.startswith("proxy_"):
                    for m_path, prx_path in self._master_to_proxy.items():
                        if Path(prx_path).name == Path(clip.source_path).name:
                            resolved_src = m_path
                            break
            swapped_clips.append(
                TimelineClip(
                    source_path=resolved_src,
                    in_point=clip.in_point,
                    out_point=clip.out_point,
                    clip_id=clip.clip_id,
                    duration=clip.duration,
                    transition_to_next=clip.transition_to_next,
                    transition_duration=clip.transition_duration,
                )
            )

        return TimelineProject(
            project_id=project.project_id,
            title=project.title,
            clips=swapped_clips,
            audio_tracks=project.audio_tracks,
            output_format=project.output_format,
            width=project.width,
            height=project.height,
            fps=project.fps,
        )
