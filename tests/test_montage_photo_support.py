from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.constants import MONTAGE_MEDIA_EXTS, MONTAGE_MEDIA_FILTER
from services.montage_service import MontageService, detect_media_type
from services.proxy_service import ProxyService
from services.timeline_service import TimelineClip, TimelineProject, TimelineService


def test_timeline_image_clip_defaults():
    clip = TimelineClip(source_path="/photos/image1.jpg", media_type="image", still_duration=4.5)
    assert clip.media_type == "image"
    assert clip.still_duration == 4.5
    assert clip.effective_duration() == 4.5
    assert clip.has_audio is False
    assert clip.in_point == 0.0
    assert clip.out_point == 4.5


def test_timeline_render_command_for_image_clip():
    service = TimelineService(ffmpeg_path="ffmpeg")
    img_clip = TimelineClip(
        source_path="/photos/nature.jpg",
        media_type="image",
        still_duration=5.0,
    )
    proj = TimelineProject(clips=[img_clip], width=1920, height=1080, fps=30.0)
    cmd = service.build_render_command(proj, "/tmp/render_img.mp4")
    cmd_str = " ".join(cmd)

    # Must contain -loop 1 for still image looping
    assert "-loop 1" in cmd_str
    # Must specify still duration
    assert "-t 5.000" in cmd_str
    # Must generate null audio since image has no audio track
    assert "anullsrc=" in cmd_str


def test_timeline_render_command_mixed_video_and_image():
    service = TimelineService(ffmpeg_path="ffmpeg")
    video_clip = TimelineClip(
        source_path="/videos/clip1.mp4",
        in_point=0.0,
        out_point=4.0,
        transition_to_next="fade",
        transition_duration=1.0,
        media_type="video",
    )
    img_clip = TimelineClip(
        source_path="/photos/still.png",
        media_type="image",
        still_duration=3.0,
    )
    proj = TimelineProject(clips=[video_clip, img_clip], width=1280, height=720, fps=30.0)
    cmd = service.build_render_command(proj, "/tmp/render_mixed.mp4")
    cmd_str = " ".join(cmd)

    # Input 0 is video: -ss 0.000 -t 4.000
    assert "-ss 0.000 -t 4.000" in cmd_str
    # Input 1 is image: -loop 1 -t 3.000
    assert "-loop 1 -t 3.000" in cmd_str
    # Crossfade transition between video and photo
    assert "xfade=transition=fade" in cmd_str


def test_detect_media_type():
    assert detect_media_type("photo.JPG") == "image"
    assert detect_media_type("photo.png") == "image"
    assert detect_media_type("photo.heic") == "image"
    assert detect_media_type("photo.webp") == "image"
    assert detect_media_type("clip.mp4") == "video"
    assert detect_media_type("clip.MOV") == "video"
    assert detect_media_type("song.mp3") == "audio"


def test_montage_service_get_media_metadata_image(tmp_path):
    service = MontageService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
    fake_probe = {
        "format": {"duration": "0"},
        "streams": [
            {"codec_type": "video", "codec_name": "png", "width": 3840, "height": 2160}
        ],
    }
    sample_file = tmp_path / "sample_photo.png"
    sample_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        import json
        mock_proc.stdout = json.dumps(fake_probe)
        mock_run.return_value = mock_proc

        meta = service.get_media_metadata(sample_file)
        assert meta["media_type"] == "image"
        assert meta["has_audio"] is False
        assert meta["duration"] == 0.0
        assert meta["width"] == 3840
        assert meta["height"] == 2160


def test_montage_service_get_session_for_image():
    service = MontageService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
    with patch.object(service, "get_media_metadata") as mock_meta:
        mock_meta.return_value = {
            "path": "/tmp/picture.jpg",
            "file_name": "picture.jpg",
            "media_type": "image",
            "duration": 0.0,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "has_video": True,
            "has_audio": False,
        }
        session = service.get_session("/tmp/picture.jpg")
        assert session["is_image"] is True
        assert session["out_point"] == 5.0
        assert session["still_duration"] == 5.0


def test_proxy_service_skips_images(tmp_path):
    proxy_service = ProxyService(ffmpeg_path="ffmpeg", proxy_dir=tmp_path / "proxies")
    test_img = tmp_path / "photo.jpg"
    test_img.write_bytes(b"dummy image data")

    # generate_proxy for image should return the original image path without transcoding
    res = proxy_service.generate_proxy(test_img)
    assert res == test_img.resolve()


def test_montage_media_constants():
    assert ".jpg" in MONTAGE_MEDIA_EXTS
    assert ".png" in MONTAGE_MEDIA_EXTS
    assert ".heic" in MONTAGE_MEDIA_EXTS
    assert ".mp4" in MONTAGE_MEDIA_EXTS
    assert ".mov" in MONTAGE_MEDIA_EXTS
    assert "Media Files (" in MONTAGE_MEDIA_FILTER
