from pathlib import Path
import tempfile
from services.subtitle_style_service import (
    STYLE_PRESETS,
    StyledSubtitleLine,
    SubtitleStyleService,
)


def test_interpolate_word_timings():
    service = SubtitleStyleService()
    words = service.interpolate_word_timings("Швидкий монтаж відео!", 0.0, 3.0)
    assert len(words) == 3
    assert words[0].word == "Швидкий"
    assert words[0].start == 0.0
    assert words[-1].end <= 3.0


def test_ass_script_generation_tiktok_pop():
    service = SubtitleStyleService()
    line = StyledSubtitleLine(start=0.5, end=2.5, text="Геніальне відео", speaker="Олексій")
    script = service.build_ass_script([line], template_name="tiktok_pop")

    assert "[Script Info]" in script
    assert "[V4+ Styles]" in script
    assert "PlayResX: 1080" in script
    assert "Style: Default" in script
    assert "Dialogue: 0," in script
    assert "Олексій" in script
    # TikTok pop has highlight color override tag
    assert r"{\c" in script


def test_ass_script_generation_karaoke_classic():
    service = SubtitleStyleService()
    line = StyledSubtitleLine(start=0.0, end=4.0, text="Слова пісні тут")
    script = service.build_ass_script([line], template_name="karaoke_classic")

    assert r"{\k" in script


def test_export_ass_and_burnin_filter():
    service = SubtitleStyleService()
    line = StyledSubtitleLine(start=1.0, end=3.0, text="Subtitles for Shorts")

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "output.ass"
        res_path = service.export_ass_file([line], out_file, template_name="reels_modern")
        assert res_path.exists()
        assert res_path.stat().st_size > 100

        filter_str = service.build_burnin_filter(res_path)
        assert filter_str.startswith("ass='")
        assert filter_str.endswith("'")

