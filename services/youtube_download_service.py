from __future__ import annotations

import http.cookiejar
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
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
    DIRECT_MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS
    DIRECT_CONTENT_TYPE_EXTS = {
        "audio/aac": ".aac",
        "audio/flac": ".flac",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "audio/x-aiff": ".aiff",
        "audio/x-flac": ".flac",
        "audio/x-m4a": ".m4a",
        "audio/x-ms-wma": ".wma",
        "audio/x-wav": ".wav",
        "video/avi": ".avi",
        "video/mp2t": ".m2ts",
        "video/mp4": ".mp4",
        "video/mpeg": ".mpg",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "video/x-flv": ".flv",
        "video/x-m4v": ".m4v",
        "video/x-matroska": ".mkv",
        "video/x-ms-wmv": ".wmv",
        "video/x-msvideo": ".avi",
        "application/mp4": ".mp4",
        "application/ogg": ".ogg",
    }

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
        rate_limit: Optional[int] = None,
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
            rate_limit=rate_limit,
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
        rate_limit: Optional[int] = None,
        cancel_event: Optional[Event] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[Path]:
        clean_url = str(url or "").strip()
        if not clean_url:
            raise YouTubeDownloadError("Video/source URL is empty.")

        clean_quality = self._normalize_quality(quality)
        clean_mode = "audio" if str(mode or "").lower() == "audio" or clean_quality == "audio_only" else "video"
        clean_audio_format = self._normalize_audio_format(audio_format)
        clean_cookies_file = str(cookies_file or "").strip()
        clean_rate_limit = self._normalize_rate_limit(rate_limit)
        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        before = self._snapshot_files(output_dir)

        ytdlp_error: Optional[YouTubeDownloadError] = None
        prepared_path: Optional[Path] = None
        try:
            YoutubeDL = self._youtube_dl_class()
            opts = self._options(
                output_dir,
                clean_mode,
                clean_audio_format,
                clean_quality,
                playlist,
                subtitles,
                clean_cookies_file,
                clean_rate_limit,
                cancel_event,
                progress_callback,
            )
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                try:
                    prepared_path = Path(ydl.prepare_filename(info)).expanduser()
                except Exception:
                    prepared_path = None
        except YouTubeDownloadCancelled:
            raise
        except YouTubeDownloadError as exc:
            ytdlp_error = exc
        except Exception as exc:
            ytdlp_error = YouTubeDownloadError(str(exc) or exc.__class__.__name__)
        else:
            candidates = self._candidate_paths(info, prepared_path, clean_mode, clean_audio_format)
            output_paths = self._find_output_files(output_dir, before, candidates, clean_mode)
            if output_paths:
                return output_paths
            ytdlp_error = YouTubeDownloadError("Download finished, but output file was not found.")

        if self._can_try_direct_download(clean_url, clean_mode, playlist, subtitles):
            try:
                return [
                    self._download_direct_media(
                        clean_url,
                        output_dir,
                        clean_mode,
                        clean_audio_format,
                        clean_cookies_file,
                        clean_rate_limit,
                        cancel_event,
                        progress_callback,
                    )
                ]
            except YouTubeDownloadCancelled:
                raise
            except YouTubeDownloadError as direct_exc:
                if ytdlp_error:
                    raise YouTubeDownloadError(
                        f"{ytdlp_error} Direct media fallback failed: {direct_exc}"
                    ) from direct_exc
                raise

        if ytdlp_error:
            raise ytdlp_error
        raise YouTubeDownloadError("Download failed.")

    def preview(
        self,
        url: str,
        *,
        playlist: bool = False,
        cookies_file: str = "",
    ) -> Dict[str, Any]:
        clean_url = str(url or "").strip()
        if not clean_url:
            raise YouTubeDownloadError("Video/source URL is empty.")

        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist" if playlist else False,
            "noplaylist": not playlist,
        }
        clean_cookies_file = str(cookies_file or "").strip()
        if clean_cookies_file:
            opts["cookiefile"] = clean_cookies_file
        try:
            YoutubeDL = self._youtube_dl_class()
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
        except Exception as exc:
            direct_preview = self._direct_preview(clean_url)
            if direct_preview:
                return direct_preview
            raise YouTubeDownloadError(str(exc) or exc.__class__.__name__) from exc

        entries = info.get("entries") if isinstance(info, dict) else None
        if isinstance(entries, list):
            count = len([entry for entry in entries if entry])
        elif isinstance(info, dict):
            count = int(info.get("playlist_count") or info.get("n_entries") or 1)
        else:
            count = 1
        title = str(info.get("title") or info.get("playlist_title") or "") if isinstance(info, dict) else ""
        preview_item = self._preview_item(info)
        duration = self._optional_float(preview_item.get("duration") if preview_item else info.get("duration") if isinstance(info, dict) else None)
        thumbnail = str(preview_item.get("thumbnail") or info.get("thumbnail") or "") if isinstance(info, dict) else ""
        formats = preview_item.get("formats") if isinstance(preview_item, dict) else None
        media_kind = self._detect_media_kind(preview_item or info)
        source_type = "playlist" if isinstance(entries, list) or count > 1 else media_kind
        return {
            "url": clean_url,
            "title": title,
            "count": max(0, count),
            "is_playlist": bool(isinstance(entries, list) or count > 1),
            "source_type": source_type,
            "media_kind": media_kind,
            "duration": duration,
            "duration_text": format_time(duration) if duration is not None else "--:--",
            "quality_summary": self._quality_summary(formats),
            "thumbnail": thumbnail,
            "extractor": str(info.get("extractor") or info.get("extractor_key") or "") if isinstance(info, dict) else "",
        }

    def _youtube_dl_class(self) -> Any:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise YouTubeDownloadError("yt-dlp is not installed. Run: pip install -r requirements.txt") from exc
        return YoutubeDL

    def _can_try_direct_download(self, url: str, mode: str, playlist: bool, subtitles: bool) -> bool:
        return (
            not playlist
            and not subtitles
            and mode in {"audio", "video"}
            and self._is_http_url(url)
        )

    def _download_direct_media(
        self,
        url: str,
        output_dir: Path,
        mode: str,
        audio_format: str,
        cookies_file: str,
        rate_limit: Optional[int],
        cancel_event: Optional[Event],
        progress_callback: Optional[ProgressCallback],
    ) -> Path:
        tmp_path: Optional[Path] = None
        try:
            with self._open_direct_url(url, cookies_file) as response:
                headers = getattr(response, "headers", {})
                content_type = self._content_type(headers)
                if not self._direct_response_is_supported(url, headers, content_type, mode):
                    raise YouTubeDownloadError(
                        "URL does not point to a supported downloadable media file for this mode."
                    )

                filename = self._direct_filename(url, headers, content_type, mode, audio_format)
                output_path = self._unique_output_path(output_dir / filename)
                tmp_path = output_path.with_suffix(output_path.suffix + ".part")
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

                total = self._optional_int(self._header_value(headers, "Content-Length"))
                downloaded = 0
                started = time.monotonic()
                self._emit_direct_progress(
                    progress_callback,
                    "downloading",
                    downloaded,
                    total,
                    None,
                    None,
                    str(output_path),
                )

                with tmp_path.open("wb") as file:
                    while True:
                        if cancel_event and cancel_event.is_set():
                            raise YouTubeDownloadCancelled("Download cancelled.")
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        file.write(chunk)
                        downloaded += len(chunk)
                        self._throttle_direct_download(downloaded, started, rate_limit)
                        elapsed = max(time.monotonic() - started, 0.001)
                        speed = downloaded / elapsed
                        eta = (total - downloaded) / speed if total and speed else None
                        self._emit_direct_progress(
                            progress_callback,
                            "downloading",
                            downloaded,
                            total,
                            speed,
                            eta,
                            str(output_path),
                        )

                tmp_path.replace(output_path)
                self._emit_direct_progress(
                    progress_callback,
                    "finished",
                    downloaded,
                    total or downloaded,
                    None,
                    None,
                    str(output_path),
                )
                return output_path
        except YouTubeDownloadCancelled:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
        except urllib.error.HTTPError as exc:
            raise YouTubeDownloadError(f"HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise YouTubeDownloadError(str(reason) or exc.__class__.__name__) from exc
        except OSError as exc:
            raise YouTubeDownloadError(str(exc) or exc.__class__.__name__) from exc

    def _open_direct_url(self, url: str, cookies_file: str) -> Any:
        parsed = urllib.parse.urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else url
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Accept": "video/*,audio/*,*/*;q=0.8",
                "Referer": origin,
            },
        )
        opener = self._direct_opener(cookies_file)
        return opener.open(request, timeout=60)

    def _direct_opener(self, cookies_file: str) -> Any:
        clean_cookies_file = str(cookies_file or "").strip()
        if not clean_cookies_file:
            return urllib.request.build_opener()

        cookie_path = Path(clean_cookies_file).expanduser()
        if not cookie_path.is_file():
            raise YouTubeDownloadError(f"Cookies file was not found: {cookie_path}")

        jar = http.cookiejar.MozillaCookieJar(str(cookie_path))
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception as exc:
            raise YouTubeDownloadError(f"Could not load cookies file: {exc}") from exc
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def _direct_preview(self, url: str) -> Optional[Dict[str, Any]]:
        if not self._is_http_url(url):
            return None
        name = self._filename_from_url(url)
        suffix = Path(name).suffix.lower()
        if suffix not in self.DIRECT_MEDIA_EXTS:
            return None
        return {
            "url": url,
            "title": Path(name).stem or "Direct media URL",
            "count": 1,
            "is_playlist": False,
            "source_type": "direct_file",
            "media_kind": "audio" if suffix in AUDIO_EXTS else "video",
            "duration": None,
            "duration_text": "--:--",
            "quality_summary": suffix.lstrip(".").upper() if suffix else "Direct file",
            "thumbnail": "",
            "extractor": "direct",
        }

    def _preview_item(self, info: Any) -> Dict[str, Any]:
        if not isinstance(info, dict):
            return {}
        entries = info.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    return entry
            return {}
        return info

    def _detect_media_kind(self, info: Any) -> str:
        if not isinstance(info, dict):
            return "video"
        ext = str(info.get("ext") or "").lower()
        if f".{ext}" in AUDIO_EXTS:
            return "audio"
        if f".{ext}" in VIDEO_EXTS:
            return "video"
        formats = info.get("formats")
        has_video = False
        has_audio = False
        if isinstance(formats, list):
            for item in formats:
                if not isinstance(item, dict):
                    continue
                vcodec = str(item.get("vcodec") or "none").lower()
                acodec = str(item.get("acodec") or "none").lower()
                has_video = has_video or vcodec not in {"", "none"}
                has_audio = has_audio or acodec not in {"", "none"}
        if has_video:
            return "video"
        if has_audio:
            return "audio"
        vcodec = str(info.get("vcodec") or "none").lower()
        acodec = str(info.get("acodec") or "none").lower()
        if vcodec not in {"", "none"}:
            return "video"
        if acodec not in {"", "none"}:
            return "audio"
        return "video"

    def _quality_summary(self, formats: Any) -> str:
        if not isinstance(formats, list):
            return "Best available"
        heights: set[int] = set()
        audio_exts: set[str] = set()
        for item in formats:
            if not isinstance(item, dict):
                continue
            height = self._optional_int(item.get("height"))
            if height:
                heights.add(height)
            vcodec = str(item.get("vcodec") or "none").lower()
            acodec = str(item.get("acodec") or "none").lower()
            ext = str(item.get("ext") or "").lower()
            if vcodec in {"", "none"} and acodec not in {"", "none"} and ext:
                audio_exts.add(ext)
        parts: List[str] = []
        if heights:
            top = sorted(heights)[-3:]
            parts.append(", ".join(f"{height}p" for height in top))
        if audio_exts:
            parts.append("audio: " + ", ".join(sorted(audio_exts)[:4]))
        return " | ".join(parts) or "Best available"

    def _direct_response_is_supported(
        self,
        url: str,
        headers: Any,
        content_type: str,
        mode: str,
    ) -> bool:
        allowed_exts = AUDIO_EXTS if mode == "audio" else VIDEO_EXTS
        content_ext = self._extension_for_content_type(content_type)
        header_name = self._filename_from_content_disposition(headers)
        header_ext = Path(header_name).suffix.lower() if header_name else ""
        url_ext = self._url_suffix(url)

        if content_type.startswith("text/") or content_type in {
            "application/json",
            "application/xml",
            "text/html",
        }:
            return False
        if content_type.startswith("video/"):
            return mode == "video"
        if content_type.startswith("audio/"):
            return mode == "audio"
        if header_ext in allowed_exts:
            return True
        if url_ext in allowed_exts and not content_type:
            return True
        if url_ext in allowed_exts and content_type in {"application/octet-stream", "binary/octet-stream"}:
            return True
        if content_ext:
            return content_ext in allowed_exts
        return False

    def _direct_filename(
        self,
        url: str,
        headers: Any,
        content_type: str,
        mode: str,
        audio_format: str,
    ) -> str:
        raw_name = self._filename_from_content_disposition(headers) or self._filename_from_url(url)
        filename = self._sanitize_filename(raw_name)
        ext = Path(filename).suffix.lower()
        allowed_exts = AUDIO_EXTS if mode == "audio" else VIDEO_EXTS
        guessed_ext = self._extension_for_content_type(content_type)
        if ext not in allowed_exts:
            stem = Path(filename).stem or ("audio" if mode == "audio" else "video")
            fallback_ext = guessed_ext if guessed_ext in allowed_exts else f".{audio_format}" if mode == "audio" else ".mp4"
            filename = self._sanitize_filename(f"{stem}{fallback_ext}")
        return filename

    def _filename_from_content_disposition(self, headers: Any) -> str:
        value = self._header_value(headers, "Content-Disposition")
        if not value:
            return ""
        filename = ""
        encoded_filename = ""
        for part in value.split(";")[1:]:
            key, separator, raw_part_value = part.strip().partition("=")
            if not separator:
                continue
            key = key.strip().lower()
            part_value = raw_part_value.strip().strip('"')
            if key == "filename*":
                encoded_filename = part_value
            elif key == "filename":
                filename = part_value

        if encoded_filename:
            charset, separator, encoded_value = encoded_filename.partition("''")
            if separator:
                try:
                    return self._last_path_segment(
                        urllib.parse.unquote(encoded_value, encoding=charset or "utf-8")
                    )
                except LookupError:
                    return self._last_path_segment(urllib.parse.unquote(encoded_value))
            return self._last_path_segment(urllib.parse.unquote(encoded_filename))
        return self._last_path_segment(filename)

    def _filename_from_url(self, url: str) -> str:
        path = urllib.parse.urlparse(url).path
        name = self._last_path_segment(urllib.parse.unquote(path))
        return name or "downloaded-media"

    def _last_path_segment(self, value: str) -> str:
        normalized = str(value or "").replace("\\", "/")
        return normalized.rsplit("/", 1)[-1].strip()

    def _sanitize_filename(self, value: str) -> str:
        name = self._last_path_segment(value)
        invalid = '<>:"/\\|?*'
        cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in name)
        cleaned = cleaned.strip().strip(".")
        if not cleaned:
            cleaned = "downloaded-media"
        if len(cleaned) > 180:
            path = Path(cleaned)
            suffix = path.suffix
            cleaned = f"{path.stem[: max(1, 180 - len(suffix))]}{suffix}"
        return cleaned

    def _unique_output_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        for index in range(1, 10000):
            candidate = path.with_name(f"{stem} ({index}){suffix}")
            if not candidate.exists():
                return candidate
        raise YouTubeDownloadError(f"Could not find a free output filename for {path.name}.")

    def _extension_for_content_type(self, content_type: str) -> str:
        normalized = str(content_type or "").split(";", 1)[0].strip().lower()
        if not normalized:
            return ""
        mapped = self.DIRECT_CONTENT_TYPE_EXTS.get(normalized)
        if mapped:
            return mapped
        guessed = mimetypes.guess_extension(normalized) or ""
        return guessed.lower()

    def _content_type(self, headers: Any) -> str:
        return str(self._header_value(headers, "Content-Type") or "").split(";", 1)[0].strip().lower()

    def _header_value(self, headers: Any, name: str) -> str:
        try:
            return str(headers.get(name) or headers.get(name.lower()) or "")
        except AttributeError:
            return ""

    def _url_suffix(self, url: str) -> str:
        return Path(urllib.parse.urlparse(url).path).suffix.lower()

    def _is_http_url(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(str(url or "").strip())
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)

    def _emit_direct_progress(
        self,
        callback: Optional[ProgressCallback],
        status: str,
        downloaded: int,
        total: Optional[int],
        speed: Optional[float],
        eta: Optional[float],
        filename: str,
    ) -> None:
        if not callback:
            return
        percent = downloaded / total if total else None
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
            message = "Downloading direct media..."
        callback(
            DownloadProgress(
                status=status,
                percent=percent,
                downloaded_bytes=downloaded,
                total_bytes=total,
                speed=speed,
                eta=eta,
                filename=filename,
                message=message,
            )
        )

    def _options(
        self,
        output_dir: Path,
        mode: str,
        audio_format: str,
        quality: str,
        playlist: bool,
        subtitles: bool,
        cookies_file: str,
        rate_limit: Optional[int],
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
        if rate_limit:
            opts["ratelimit"] = int(rate_limit)
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

    def _throttle_direct_download(self, downloaded: int, started: float, rate_limit: Optional[int]) -> None:
        if not rate_limit or rate_limit <= 0:
            return
        target_elapsed = downloaded / float(rate_limit)
        actual_elapsed = time.monotonic() - started
        delay = target_elapsed - actual_elapsed
        if delay > 0:
            time.sleep(min(delay, 1.0))

    def _normalize_rate_limit(self, value: Optional[int]) -> Optional[int]:
        try:
            normalized = int(value or 0)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None

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
