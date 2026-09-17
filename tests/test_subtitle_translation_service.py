import tempfile
from pathlib import Path

from services.subtitle_translation_service import (
    SubtitleTranslationService,
    TranslatedSubtitleSegment,
)


def test_translate_text_offline_and_speaker_preservation():
    service = SubtitleTranslationService()
    # Offline dictionary translation with speaker tag
    translated = service.translate_text("[Мовець 1] привіт", source_lang="uk", target_lang="en")
    assert "[Мовець 1]" in translated
    assert "Hello" in translated


def test_translate_segments_batch():
    service = SubtitleTranslationService()
    segments = [
        {"start": 0.0, "end": 2.0, "text": "привіт", "speaker": "Олексій"},
        {"start": 2.5, "end": 4.5, "text": "дякую", "speaker": "Марія"},
    ]
    res = service.translate_segments(segments, target_languages=["en", "uk"], source_language="uk")
    assert "en" in res.translations
    assert "uk" in res.translations
    assert len(res.translations["en"]) == 2
    # Check start and end timestamps are preserved strictly
    assert res.translations["en"][0].start == 0.0
    assert res.translations["en"][0].end == 2.0
    assert res.translations["en"][1].start == 2.5
    assert res.translations["en"][1].end == 4.5


def test_export_language_srt():
    service = SubtitleTranslationService()
    segments = [
        TranslatedSubtitleSegment(start=1.0, end=3.0, original_text="привіт", translated_text="Hello", language="en", speaker="Alice")
    ]
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_srt = Path(tmp_dir) / "test.en.srt"
        service.export_language_srt(segments, out_srt, include_speaker=True)
        assert out_srt.exists()
        content = out_srt.read_text(encoding="utf-8")
        assert "[Alice] Hello" in content
        assert "00:00:01,000 --> 00:00:03,000" in content


def test_multitrack_embed_command():
    service = SubtitleTranslationService(ffmpeg_path="ffmpeg")
    cmd = service.build_multitrack_embed_command(
        video_path="/tmp/video.mp4",
        subtitle_files={"uk": "/tmp/sub.uk.srt", "en": "/tmp/sub.en.srt"},
        output_path="/tmp/video_multisubs.mp4",
    )
    cmd_str = " ".join(cmd)
    assert "-map 1:s" in cmd_str
    assert "-map 2:s" in cmd_str
    assert "language=ukr" in cmd_str
    assert "language=eng" in cmd_str
