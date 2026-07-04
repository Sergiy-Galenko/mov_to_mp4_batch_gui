import sys
from threading import Event
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from services.youtube_download_service import (
    DownloadProgress,
    YouTubeDownloadCancelled,
    YouTubeDownloadError,
    YouTubeDownloadService,
)


class FakeVideoYoutubeDL:
    instances = []

    def __init__(self, opts):
        self.opts = opts
        self.url = ""
        self.download = False
        self.output_path = Path(self.opts["paths"]["home"]) / "clip.mp4"
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def extract_info(self, url, download):
        self.url = url
        self.download = download
        self.output_path.write_bytes(b"video")
        for hook in self.opts["progress_hooks"]:
            hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 5,
                    "total_bytes": 10,
                    "filename": str(self.output_path),
                }
            )
            hook({"status": "finished", "filename": str(self.output_path)})
        return {"filepath": str(self.output_path)}

    def prepare_filename(self, _info):
        return str(self.output_path)


class FakeAudioYoutubeDL(FakeVideoYoutubeDL):
    instances = []

    def __init__(self, opts):
        super().__init__(opts)
        self.output_path = Path(self.opts["paths"]["home"]) / "song.mp3"

    def extract_info(self, url, download):
        self.url = url
        self.download = download
        self.output_path.write_bytes(b"audio")
        return {"filepath": str(self.output_path.with_suffix(".webm"))}

    def prepare_filename(self, _info):
        return str(self.output_path.with_suffix(".webm"))


class FakePlaylistYoutubeDL(FakeVideoYoutubeDL):
    instances = []

    def extract_info(self, url, download):
        self.url = url
        self.download = download
        first = Path(self.opts["paths"]["home"]) / "one.mp4"
        second = Path(self.opts["paths"]["home"]) / "two.mp4"
        first.write_bytes(b"one")
        second.write_bytes(b"two")
        return {
            "entries": [
                {"filepath": str(first)},
                {"requested_downloads": [{"filepath": str(second)}]},
            ]
        }

    def prepare_filename(self, _info):
        return str(Path(self.opts["paths"]["home"]) / "playlist.mp4")


def fake_module(youtube_dl_class):
    module = types.ModuleType("yt_dlp")
    module.YoutubeDL = youtube_dl_class
    return module


def test_video_download_uses_ytdlp_options_and_progress(tmp_path):
    FakeVideoYoutubeDL.instances.clear()
    progress_events: list[DownloadProgress] = []

    with patch.dict(sys.modules, {"yt_dlp": fake_module(FakeVideoYoutubeDL)}):
        service = YouTubeDownloadService(ffmpeg_path="C:/tools/ffmpeg.exe")
        output = service.download(
            "https://youtu.be/example",
            tmp_path,
            mode="video",
            progress_callback=progress_events.append,
        )

    assert output == tmp_path / "clip.mp4"
    assert output.read_bytes() == b"video"
    instance = FakeVideoYoutubeDL.instances[0]
    assert instance.url == "https://youtu.be/example"
    assert instance.download is True
    assert instance.opts["format"].startswith("bv*")
    assert instance.opts["merge_output_format"] == "mp4"
    assert instance.opts["ffmpeg_location"] == "C:/tools/ffmpeg.exe"
    assert progress_events[-1].percent == 1.0


def test_audio_download_returns_postprocessed_file(tmp_path):
    FakeAudioYoutubeDL.instances.clear()

    with patch.dict(sys.modules, {"yt_dlp": fake_module(FakeAudioYoutubeDL)}):
        service = YouTubeDownloadService()
        output = service.download(
            "https://youtu.be/example",
            tmp_path,
            mode="audio",
            audio_format="mp3",
        )

    assert output == tmp_path / "song.mp3"
    assert output.read_bytes() == b"audio"
    opts = FakeAudioYoutubeDL.instances[0].opts
    assert opts["format"] == "bestaudio/best"
    assert opts["postprocessors"][0]["preferredcodec"] == "mp3"


def test_missing_ytdlp_dependency_has_actionable_error(tmp_path):
    with patch.dict(sys.modules, {"yt_dlp": None}):
        service = YouTubeDownloadService()
        with pytest.raises(YouTubeDownloadError, match="pip install -r requirements.txt"):
            service.download("https://youtu.be/example", tmp_path)


def test_advanced_download_options_support_playlist_subtitles_and_cookies(tmp_path):
    FakePlaylistYoutubeDL.instances.clear()
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    with patch.dict(sys.modules, {"yt_dlp": fake_module(FakePlaylistYoutubeDL)}):
        service = YouTubeDownloadService()
        outputs = service.download_many(
            "https://youtu.be/playlist",
            tmp_path,
            quality="720p",
            playlist=True,
            subtitles=True,
            cookies_file=str(cookies),
        )

    assert outputs == [tmp_path / "one.mp4", tmp_path / "two.mp4"]
    opts = FakePlaylistYoutubeDL.instances[0].opts
    assert opts["noplaylist"] is False
    assert "height<=720" in opts["format"]
    assert opts["writesubtitles"] is True
    assert opts["writeautomaticsub"] is True
    assert opts["cookiefile"] == str(cookies)


def test_cancel_event_stops_download(tmp_path):
    cancel_event = Event()
    cancel_event.set()

    with patch.dict(sys.modules, {"yt_dlp": fake_module(FakeVideoYoutubeDL)}):
        service = YouTubeDownloadService()
        with pytest.raises(YouTubeDownloadCancelled):
            service.download(
                "https://youtu.be/example",
                tmp_path,
                cancel_event=cancel_event,
            )
