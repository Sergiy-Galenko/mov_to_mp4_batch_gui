from pathlib import Path
import tempfile
from services.speaker_diarization_service import (
    DiarizationResult,
    SpeakerDiarizationService,
    SpeakerSegment,
)


def test_diarization_result_dataclass_and_aliases():
    service = SpeakerDiarizationService()
    seg1 = SpeakerSegment(start=0.0, end=2.5, text="Доброго дня!", speaker_id="SPEAKER_00", speaker_name="Мовець 1")
    seg2 = SpeakerSegment(start=2.6, end=5.0, text="Вітаю вас!", speaker_id="SPEAKER_01", speaker_name="Мовець 2")

    res = DiarizationResult(
        segments=[seg1, seg2],
        speaker_aliases={"SPEAKER_00": "Мовець 1", "SPEAKER_01": "Мовець 2"},
        detected_speakers_count=2,
    )

    # Apply custom rename
    renamed = service.apply_aliases(res, {"SPEAKER_00": "Олексій", "SPEAKER_01": "Марія"})
    assert renamed.segments[0].speaker_name == "Олексій"
    assert renamed.segments[1].speaker_name == "Марія"
    assert renamed.speaker_aliases["SPEAKER_00"] == "Олексій"


def test_diarization_export_srt_and_vtt():
    service = SpeakerDiarizationService()
    seg = SpeakerSegment(start=1.5, end=4.2, text="Тестовий сегмент", speaker_id="SPEAKER_00", speaker_name="Богдан")
    res = DiarizationResult(segments=[seg], speaker_aliases={"SPEAKER_00": "Богдан"}, detected_speakers_count=1)

    with tempfile.TemporaryDirectory() as tmp_dir:
        srt_file = Path(tmp_dir) / "test.srt"
        vtt_file = Path(tmp_dir) / "test.vtt"

        srt_text = service.export_srt(res, srt_file, include_speaker_tags=True)
        assert "[Богдан] Тестовий сегмент" in srt_text
        assert "00:00:01,500 --> 00:00:04,200" in srt_text
        assert srt_file.exists()

        vtt_text = service.export_vtt(res, vtt_file)
        assert "WEBVTT" in vtt_text
        assert "<v Богдан>Тестовий сегмент" in vtt_text
        assert vtt_file.exists()


def test_diarize_segments_fallback():
    service = SpeakerDiarizationService()
    raw_segments = [
        {"start": 0.0, "end": 2.0, "text": "Перша фраза першого учасника"},
        {"start": 2.5, "end": 5.0, "text": "Друга фраза другого учасника"},
        {"start": 5.5, "end": 7.0, "text": "Третя фраза"},
    ]
    # Diarize with mock media path (uses feature fallback)
    result = service.diarize_segments("/nonexistent/video.mp4", raw_segments, num_speakers=2, language="uk")
    assert len(result.segments) == 3
    assert result.detected_speakers_count == 2
    assert "SPEAKER_00" in result.speaker_aliases
    assert "SPEAKER_01" in result.speaker_aliases

