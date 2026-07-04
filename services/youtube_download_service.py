from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any, Callable, Dict, Iterable, List, Optional

from app.constants import AUDIO_EXTS, VIDEO_EXTS
from utils.formatting import format_bytes, format_time


ProgressCallback = Callable[["DownloadProgress"], None]


class YouTubeDownloadError(RuntimeError):
    pass


class YouTubeDownloadCancelled(YouTubeDownloadError):
    pass


@dataclass(frozen=True)
class DownloadProgress:
    status: str
    percent: Optional[float]
    downloaded_bytes: Optional[int]
    total_bytes: Optional[int]
    speed: Optional[float]
    eta: Optional[float]
    filename: str
    message: str


class YouTubeDownloadService:
    AUDIO_FORMATS = {"mp3", "m4a", "opus", "wav", "flac", "aac"}
    QUALITY_OPTIONS = {"best", "1080p", "720p", "audio_only"}

    def __init__(self, ffmpeg_path: Optional[str] = None) -> None:
        self.ffmpeg_path = str(ffmpeg_path or "").strip()

    @staticmethod
    def is_available() -> bool:
        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            return False
        return True

    def download(
        self,
        url: str,
        output_dir: Path,
        *,
        mode: str = "video",
        audio_format: str = "mp3",
        quality: str = "best",
        playlist: bool = False,
        subtitles: bool = False,
        cookies_file: str = "",
        cancel_event: Optional[Event] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Path:
        outputs = self.download_many(
            url,
            output_dir,
            mode=mode,
            audio_format=audio_format,
            quality=quality,
            playlist=playlist,
            subtitles=subtitles,
            cookies_file=cookies_file,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
        if not outputs:
            raise YouTubeDownloadError("Download finished, but output file was not found.")
        return outputs[0]

    def download_many(
        self,
        url: str,
        output_dir: Path,
        *,
        mode: str = "video",
        audio_format: str = "mp3",
        quality: str = "best",
        playlist: bool = False,
        subtitles: bool = False,
        cookies_file: str = "",
        cancel_event: Optional[Event] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[Path]:
        clean_url = str(url or "").strip()
        if not clean_url:
            raise YouTubeDownloadError("YouTube URL is empty.")

        clean_quality = self._normalize_quality(quality)
        clean_mode = "audio" if str(mode or "").lower() == "audio" or clean_quality == "audio_only" else "video"
        clean_audio_format = self._normalize_audio_format(audio_format)
        clean_cookies_file = str(cookies_file or "").strip()
        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        before = self._snapshot_files(output_dir)

        YoutubeDL = self._youtube_dl_class()
        opts = self._options(
            output_dir,
            clean_mode,
            clean_audio_format,
            clean_quality,
            playlist,
            subtitles,
            clean_cookies_file,
            cancel_event,
            progress_callback,
        )
        prepared_path: Optional[Path] = None
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                try:
                    prepared_path = Path(ydl.prepare_filename(info)).expanduser()
                except Exception:
                    prepared_path = None
        except YouTubeDownloadCancelled:
            raise
        except YouTubeDownloadError:
            raise
        except Exception as exc:
            raise YouTubeDownloadError(str(exc) or exc.__class__.__name__) from exc

        candidates = self._candidate_paths(info, prepared_path, clean_mode, clean_audio_format)
        output_paths = self._find_output_files(output_dir, before, candidates, clean_mode)
        if not output_paths:
            raise YouTubeDownloadError("Download finished, but output file was not found.")
        return output_paths

    def _youtube_dl_class(self) -> Any:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise YouTubeDownloadError("yt-dlp is not installed. Run: pip install -r requirements.txt") from exc
        return YoutubeDL

    def _options(
        self,
        output_dir: Path,
        mode: str,
        audio_format: str,
        quality: str,
        playlist: bool,
        subtitles: bool,
        cookies_file: str,
        cancel_event: Optional[Event],
        progress_callback: Optional[ProgressCallback],
    ) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "paths": {"home": str(output_dir)},
            "outtmpl": "%(title).200B [%(id)s].%(ext)s",
            "noplaylist": not playlist,
            "continuedl": True,
            "overwrites": False,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "windowsfilenames": True,
            "progress_hooks": [self._progress_hook(progress_callback, cancel_event)],
        }
        if self.ffmpeg_path:
            opts["ffmpeg_location"] = self.ffmpeg_path
        if cookies_file:
            opts["cookiefile"] = cookies_file
        if subtitles:
            opts.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["all"],
                    "subtitlesformat": "best",
                }
            )

        if mode == "audio":
            opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": audio_format,
                            "preferredquality": "192",
                        }
                    ],
                }
            )
        else:
            opts.update(
                {
                    "format": self._format_selector(quality),
                    "merge_output_format": "mp4",
                }
            )
        return opts

    def _progress_hook(
        self,
        callback: Optional[ProgressCallback],
        cancel_event: Optional[Event],
    ) -> Callable[[Dict[str, Any]], None]:
        def hook(payload: Dict[str, Any]) -> None:
            if cancel_event and cancel_event.is_set():
                raise YouTubeDownloadCancelled("Download cancelled.")
            if not callback:
                return
            callback(self._progress_from_payload(payload))

        return hook

    def _progress_from_payload(self, payload: Dict[str, Any]) -> DownloadProgress:
        status = str(payload.get("status") or "")
        downloaded = self._optional_int(payload.get("downloaded_bytes"))
        total = self._optional_int(payload.get("total_bytes") or payload.get("total_bytes_estimate"))
        speed = self._optional_float(payload.get("speed"))
        eta = self._optional_float(payload.get("eta"))
        filename = str(payload.get("filename") or payload.get("tmpfilename") or "")
        percent = downloaded / total if downloaded is not None and total else None

        if status == "finished":
            percent = 1.0
            message = f"Finished: {Path(filename).name}" if filename else "Finished."
        elif percent is not None:
            message = f"{percent * 100:.1f}%"
            if total:
                message += f" of {format_bytes(total)}"
            if speed:
                message += f" at {format_bytes(int(speed))}/s"
            if eta is not None:
                message += f", ETA {format_time(eta)}"
        else:
            message = status or "Downloading..."

        return DownloadProgress(
            status=status,
            percent=percent,
            downloaded_bytes=downloaded,
            total_bytes=total,
            speed=speed,
            eta=eta,
            filename=filename,
            message=message,
        )

    def _candidate_paths(
        self,
        info: Any,
        prepared_path: Optional[Path],
        mode: str,
        audio_format: str,
    ) -> List[Path]:
        candidates: List[Path] = []
        if prepared_path:
            candidates.append(prepared_path)

        for value in self._path_values_from_info(info):
            candidates.append(Path(value).expanduser())

        if mode == "audio":
            audio_candidates: List[Path] = []
            for path in candidates:
                audio_candidates.append(path.with_suffix(f".{audio_format}"))
            candidates = audio_candidates + candidates

        unique: List[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path)
            if key not in seen:
                unique.append(path)
                seen.add(key)
        return unique

    def _path_values_from_info(self, info: Any) -> Iterable[str]:
        if not isinstance(info, dict):
            return []
        values: List[str] = []
        for key in ("filepath", "_filename", "filename"):
            value = info.get(key)
            if value:
                values.append(str(value))
        requested = info.get("requested_downloads")
        if isinstance(requested, list):
            for item in requested:
                if not isinstance(item, dict):
                    continue
                for key in ("filepath", "_filename", "filename"):
                    value = item.get(key)
                    if value:
                        values.append(str(value))
        entries = info.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                values.extend(self._path_values_from_info(entry))
        return values

    def _find_output_files(
        self,
        output_dir: Path,
        before: set[Path],
        candidates: Iterable[Path],
        mode: str,
    ) -> List[Path]:
        allowed_exts = AUDIO_EXTS if mode == "audio" else VIDEO_EXTS
        output_paths: List[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                key = str(candidate.resolve())
                if key not in seen:
                    output_paths.append(candidate)
                    seen.add(key)

        new_files: List[Path] = []
        for path in output_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in allowed_exts:
                continue
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            if resolved not in before:
                new_files.append(path)
        for path in sorted(new_files, key=lambda item: item.stat().st_mtime):
            key = str(path.resolve())
            if key not in seen:
                output_paths.append(path)
                seen.add(key)
        return output_paths

    def _snapshot_files(self, folder: Path) -> set[Path]:
        files: set[Path] = set()
        if not folder.exists():
            return files
        for path in folder.iterdir():
            if not path.is_file():
                continue
            try:
                files.add(path.resolve())
            except Exception:
                files.add(path)
        return files

    def _normalize_audio_format(self, value: str) -> str:
        normalized = str(value or "mp3").strip().lower()
        return normalized if normalized in self.AUDIO_FORMATS else "mp3"

    def _normalize_quality(self, value: str) -> str:
        normalized = str(value or "best").strip().lower()
        return normalized if normalized in self.QUALITY_OPTIONS else "best"

    def _format_selector(self, quality: str) -> str:
        if quality == "1080p":
            return "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/best[height<=1080]/best"
        if quality == "720p":
            return "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/best[height<=720]/best"
        return "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/best"

    def _optional_int(self, value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _optional_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
