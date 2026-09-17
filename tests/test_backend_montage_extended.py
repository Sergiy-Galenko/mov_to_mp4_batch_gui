import tempfile
from pathlib import Path

from services.montage_service import MontageService
from ui.backend import Backend


def test_montage_service_extended_features():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store_path = Path(tmp_dir) / "montage.json"
        service = MontageService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe", store_path=store_path)

        dummy_vid = Path(tmp_dir) / "clip1.mp4"
        dummy_vid.write_bytes(b"0" * 2048)

        # 1. Timeline project
        proj = service.get_timeline_project(dummy_vid)
        assert "clips" in proj
        assert len(proj["clips"]) == 1

        # 2. Proxy methods
        proxy_path = service.get_proxy_path(dummy_vid, 720)
        assert "720p" in proxy_path
        assert service.is_proxy_ready(dummy_vid, 720) is False

        # 3. Styled Subtitles
        segs = [{"start": 0.0, "end": 2.0, "text": "Тестовий текст"}]
        script = service.generate_styled_subtitles(segs, template="tiktok_pop")
        assert "[Script Info]" in script

        # 4. Translation
        trans = service.translate_subtitles(segs, target_languages=["en"], source_lang="uk")
        assert "en" in trans["translations"]


def test_backend_montage_slots(monkeypatch):
    backend = Backend()
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "sample.mp4"
        test_file.write_bytes(b"0" * 1024)

        # Test proxy slots
        p_path = backend.getMontageProxyPath(str(test_file), 720)
        assert "720p" in p_path
        assert backend.isMontageProxyReady(str(test_file), 720) is False

        # Test timeline slots
        proj = backend.getTimelineProject(str(test_file))
        assert "clips" in proj

        # Test styled subtitles slot
        segs = [{"start": 1.0, "end": 3.0, "text": "Hello world"}]
        ass_script = backend.generateStyledSubtitles(segs, "reels_modern", "", 1080, 1920)
        assert "[Script Info]" in ass_script

        # Test translation slot
        t_res = backend.translateSubtitles(segs, ["uk"], "en")
        assert "uk" in t_res["translations"]
