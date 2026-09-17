from pathlib import Path
import tempfile
from services.proxy_service import ProxyService
from services.timeline_service import TimelineClip, TimelineProject


def test_proxy_service_path_and_cache_key():
    with tempfile.TemporaryDirectory() as tmp_dir:
        proxy_dir = Path(tmp_dir) / "proxies"
        service = ProxyService(ffmpeg_path="ffmpeg", proxy_dir=proxy_dir)

        dummy_src = Path(tmp_dir) / "video_large.mp4"
        dummy_src.write_bytes(b"0" * 2048)

        proxy_path = service.get_proxy_path(dummy_src, target_height=720)
        assert proxy_path.parent == proxy_dir
        assert "proxy_video_large_720p_" in proxy_path.name

        assert service.is_proxy_ready(dummy_src, 720) is False

        # Create dummy proxy file
        proxy_path.write_bytes(b"1" * 2048)
        assert service.is_proxy_ready(dummy_src, 720) is True


def test_proxy_service_swap_proxies_for_masters():
    with tempfile.TemporaryDirectory() as tmp_dir:
        proxy_dir = Path(tmp_dir) / "proxies"
        service = ProxyService(ffmpeg_path="ffmpeg", proxy_dir=proxy_dir)

        master_path = str(Path(tmp_dir) / "huge_master.mov")
        proxy_path = str(Path(tmp_dir) / "proxies" / "proxy_huge_master_720p_abc.mp4")
        service._register_pair(master_path, proxy_path)

        # Timeline was constructed using the lightweight proxy
        clip = TimelineClip(source_path=proxy_path, in_point=1.0, out_point=5.0)
        proj = TimelineProject(clips=[clip])

        # Prior to final export, proxies must be swapped for master originals
        swapped = service.swap_proxies_for_masters(proj)
        assert Path(swapped.clips[0].source_path).resolve() == Path(master_path).resolve()
