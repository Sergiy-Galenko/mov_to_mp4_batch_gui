import array
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from services.background_job import JobCancelled
from services.montage_editing import editing_project, export_path, preview_ranges
from services.montage_service import MontageService
from services.subtitle_editing import (
    kept_ranges,
    merge_cues,
    normalize_cues,
    parse_subtitles,
    retime_cues,
    scenes_from_timestamps,
    serialize_subtitles,
    split_cue,
    word_cut,
)
from services.timeline_service import TimelineAudioTrack, TimelineClip, TimelineProject, TimelineService
from ui.backend import Backend


def test_srt_vtt_unicode_roundtrip_and_editing():
    cues = parse_subtitles("1\n00:00:01,250 --> 00:00:04,500\nПривіт 🌍 світе\n\n2\n00:00:05,000 --> 00:00:06,000\nДруга репліка\n")
    vtt = serialize_subtitles(cues, "vtt")
    restored = parse_subtitles(vtt)
    assert [cue["text"] for cue in restored] == ["Привіт 🌍 світе", "Друга репліка"]
    assert restored[0]["start"] == 1.25
    divided = split_cue(cues, cues[0]["id"], 3.0, len("Привіт 🌍".encode("utf-16-le")) // 2)
    assert [cue["text"] for cue in divided[:2]] == ["Привіт 🌍", "світе"]
    assert divided[0]["end"] == divided[1]["start"] == 3
    assert merge_cues(divided, divided[0]["id"])[0]["text"] == "Привіт 🌍 світе"
    assert cues[0]["text"] == "Привіт 🌍 світе"  # Pure operations preserve undo snapshots.


@pytest.mark.parametrize("start,end", [(1, 1), (2, 1), (-1, 2), (0, float("nan")), (0, float("inf"))])
def test_invalid_subtitle_times_are_rejected(start, end):
    with pytest.raises(ValueError):
        normalize_cues([{"start": start, "end": end, "text": "text"}])


def test_text_cut_uses_real_word_times_and_retimes_remaining_subtitles():
    words = [{"word": "one", "start": 0, "end": 0.5}, {"word": "two", "start": 0.5, "end": 2}, {"word": "three", "start": 2, "end": 3}]
    assert word_cut(words, 1, 1) == [0.5, 2]
    ranges = kept_ranges(3, [[0.5, 1], [0.8, 2], [0.5, 2]])
    assert ranges == [[0, 0.5], [2, 3]]
    cues = [{"start": 0, "end": 3, "text": "one two three", "words": words}]
    retimed = retime_cues(cues, ranges)
    assert [cue["text"] for cue in retimed] == ["one", "three"]
    assert retimed[-1]["start"] == 0.5
    assert retimed[-1]["end"] == 1.5
    assert kept_ranges(3, [[0, 3]]) == []
    with pytest.raises(ValueError):
        word_cut(words, -1, 1)
    assert preview_ranges([[0, 5], [8, 30]], 4) == [[4, 5], [8, 19]]


def test_scene_boundaries_cover_source_without_tiny_or_duplicate_scenes():
    scenes = scenes_from_timestamps([0, 1, 1, 1.1, 2.5, 9.9], 10)
    assert [(scene["start"], scene["end"]) for scene in scenes] == [(0, 1), (1, 2.5), (2.5, 10)]
    assert scenes_from_timestamps([], 10) == [{"start": 0, "end": 10, "selected": True}]


def test_word_alignment_uses_cpu_for_mps_and_never_invents_times(tmp_path, monkeypatch):
    import sys

    from services import transcription_service, whisper_runtime, whisper_worker
    from services.whisper_model_manager import WhisperModelManager

    checkpoint = tmp_path / "tiny.pt"
    checkpoint.touch()
    monkeypatch.setattr(WhisperModelManager, "model_path", lambda *args: checkpoint)
    monkeypatch.setattr(whisper_runtime, "resolve_device", lambda *args: "mps")
    monkeypatch.setattr(transcription_service.TranscriptionService, "_whisper_audio", lambda *args: [0])
    model = Mock()
    model.transcribe.return_value = {
        "segments": [
            {
                "start": 1,
                "end": 4,
                "text": " hello world",
                "words": [{"start": 1.1, "end": 1.5, "word": " hello"}, {"start": 3.2, "end": 3.8, "word": " world"}],
            }
        ]
    }
    load = Mock(return_value=model)
    monkeypatch.setitem(sys.modules, "whisper", SimpleNamespace(load_model=load))
    output = tmp_path / "transcript.json"
    result = whisper_worker.timed_transcript("audio.wav", str(output), "tiny", "whisper", "mps")
    assert load.call_args.kwargs["device"] == "cpu"
    assert model.transcribe.call_args.kwargs["word_timestamps"] is True
    assert result["device"] == "cpu"
    assert json.loads(output.read_text())["words"][1]["start"] == 3.2


@pytest.fixture
def studio(tmp_path):
    app = QApplication.instance() or QApplication([])
    backend = Backend()
    backend.settings_manager.save = Mock()
    backend.montage_service = MontageService(store_path=tmp_path / "sessions.json")
    engine = QQmlApplicationEngine()
    directory = Path(__file__).resolve().parents[1] / "ui/qml"
    engine.addImportPath(str(directory))
    engine.rootContext().setContextProperty("backend", backend)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    engine.load(QUrl.fromLocalFile(str(directory / "components/MontageToolsWindow.qml")))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    source = str(tmp_path / "source.mp4")
    invoke(root, "openSource", source, {"duration": 10, "width": 640, "height": 360, "has_audio": True})
    QTest.qWait(30)
    yield root, backend, source
    root.close()
    backend.shutdown()
    engine.deleteLater()
    app.processEvents()
    assert not warnings, warnings


def invoke(obj, name, *args):
    assert QMetaObject.invokeMethod(obj, name, *[Q_ARG("QVariant", value) for value in args])


def document(root):
    return root.property("document").toVariant()


def test_editor_changes_undo_and_persist_without_erasing_montage(studio):
    root, backend, source = studio
    backend.montage_service.save_session(source, {"in_point": 2})
    invoke(root, "edit", "add", {"start": 1, "end": 4, "text": "Hello world"})
    cue_id = document(root)["cues"][0]["id"]
    root.setProperty("selectedId", cue_id)
    history = root.findChild(QObject, "studioUndoHistory")
    invoke(history, "flush")
    invoke(root, "edit", "split", {"id": cue_id, "at": 2, "cursor": 5})
    assert len(document(root)["cues"]) == 2
    invoke(history, "undo")
    assert [cue["text"] for cue in document(root)["cues"]] == ["Hello world"]
    invoke(history, "redo")
    assert len(document(root)["cues"]) == 2
    invoke(history, "begin")
    invoke(root, "edit", "update", {"id": cue_id, "values": {"start": 0.5}})
    QTest.qWait(350)
    invoke(root, "edit", "update", {"id": cue_id, "values": {"start": 0.2}})
    invoke(history, "end")
    invoke(history, "undo")
    assert document(root)["cues"][0]["start"] == 1
    invoke(root, "save")
    backend.montage_service.save_session(source, {"in_point": 3, "out_point": 9})
    stored = backend.montage_service.session_store.get_session(source)
    assert len(stored["editing_tools"]["cues"]) == 2
    assert stored["in_point"] == 3
    assert root.findChild(QObject, "subtitleStartHandle")
    assert root.findChild(QObject, "comparisonDivider")


def test_stale_analysis_results_cannot_change_another_file(studio):
    root, backend, source = studio
    job = backend._montage_editing
    job.completed.emit({"kind": "scenes", "source": "other.mp4", "scenes": [{"start": 0, "end": 2}]})
    assert not document(root)["scenes"]
    job.completed.emit({"kind": "scenes", "source": source, "scenes": [{"start": 0, "end": 10, "selected": True}]})
    assert len(document(root)["scenes"]) == 1


def test_selecting_unicode_words_creates_one_undoable_video_cut(studio):
    root, _backend, _source = studio
    state = document(root)
    state["words"] = [{"word": "Hi", "start": 1, "end": 1.5}, {"word": "🌍", "start": 2, "end": 3}, {"word": "there", "start": 4, "end": 5}]
    root.setProperty("document", state)
    root.setProperty("page", 1)
    history = root.findChild(QObject, "studioUndoHistory")
    invoke(history, "reset")
    editor = root.findChild(QObject, "timedTranscript")
    assert QMetaObject.invokeMethod(editor, "select", Q_ARG(int, 3), Q_ARG(int, 5))
    invoke(root, "cutSelection")
    assert document(root)["removed"] == [[2, 3]]
    invoke(history, "undo")
    assert document(root)["removed"] == []


def test_dragging_subtitle_boundary_tracks_pointer_and_undoes_once(studio):
    root, _backend, _source = studio
    invoke(root, "edit", "add", {"start": 1, "end": 4, "text": "Move me"})
    root.setProperty("selectedId", document(root)["cues"][0]["id"])
    history = root.findChild(QObject, "studioUndoHistory")
    invoke(history, "reset")
    QTest.qWait(50)
    marker = root.findChild(QObject, "subtitleStartHandle")
    origin = marker.mapToScene(QPointF(8, 10)).toPoint()
    distance = round(marker.property("trackWidth") / 10)
    QTest.mousePress(root, Qt.LeftButton, Qt.NoModifier, origin)
    for part in (0.25, 0.5, 0.75, 1):
        QTest.mouseMove(root, origin + QPoint(round(distance * part), 0), 20)
    QTest.mouseRelease(root, Qt.LeftButton, Qt.NoModifier, origin + QPoint(distance, 0))
    assert document(root)["cues"][0]["start"] == pytest.approx(2, abs=0.03)
    invoke(history, "undo")
    assert document(root)["cues"][0]["start"] == 1


def test_export_extension_cannot_bypass_overwrite_confirmation(tmp_path):
    existing = tmp_path / "movie.mp4"
    existing.touch()
    assert export_path(str(existing), ".mp4", (".mp4",)) == existing
    with pytest.raises(ValueError, match="already exists"):
        export_path(str(existing.with_suffix("")), ".mp4", (".mp4",))
    with pytest.raises(ValueError, match="extensions"):
        export_path(str(existing.with_suffix(".mkv")), ".mp4", (".mp4",))


def test_cancelled_export_preserves_existing_file(studio, tmp_path, monkeypatch):
    _root, backend, source = studio
    output = tmp_path / "existing.mp4"
    output.write_bytes(b"original output")
    service = backend._montage_editing
    monkeypatch.setattr("services.montage_editing.QtWidgets.QFileDialog.getSaveFileName", lambda *args: (str(output), "MP4"))
    monkeypatch.setattr(service, "_ffmpeg", lambda: "ffmpeg")

    def interrupted(*args, **kwargs):
        Path(args[6]).write_bytes(b"partial")
        raise JobCancelled()

    monkeypatch.setattr(service, "_render", interrupted)
    service.exportVideo(source, {}, {"duration": 10})
    for _ in range(100):
        if not service.busy:
            break
        QTest.qWait(10)
    assert service.stage == "cancelled"
    assert output.read_bytes() == b"original output"
    assert not list(tmp_path.glob(".montage-export-*"))


@pytest.fixture
def ffmpeg():
    binary = os.environ.get("MEDIA_CONVERTER_TEST_FFMPEG") or shutil.which("ffmpeg")
    if not binary:
        pytest.skip("FFmpeg is required for media integration tests")
    return binary


def run_ffmpeg(binary, *args):
    result = subprocess.run([binary, "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return result.stdout


@pytest.fixture
def media(ffmpeg, tmp_path):
    source, music = tmp_path / "three scenes.mp4", tmp_path / "music.wav"
    run_ffmpeg(
        ffmpeg,
        "-f",
        "lavfi",
        "-i",
        "color=black:s=160x90:r=10:d=1",
        "-f",
        "lavfi",
        "-i",
        "color=white:s=160x90:r=10:d=1",
        "-f",
        "lavfi",
        "-i",
        "color=black:s=160x90:r=10:d=2",
        "-f",
        "lavfi",
        "-i",
        "aevalsrc='0.6*sin(2*PI*440*t)*between(t,1,2)':s=44100:d=4",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
        "-map",
        "[v]",
        "-map",
        "3:a",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(source),
    )
    run_ffmpeg(ffmpeg, "-f", "lavfi", "-i", "aevalsrc=0.2*sin(2*PI*880*t):s=44100:d=4", str(music))
    return source, music


def render_command(binary, project, output):
    cmd = TimelineService(binary).build_render_command(project, output)
    cmd[1:1] = ["-hide_banner", "-loglevel", "error", "-filter_complex_threads", "1"]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_real_render_cuts_silent_sources_crop_subtitles_and_preview(ffmpeg, media, tmp_path):
    source, _music = media
    subtitles = tmp_path / "captions.srt"
    subtitles.write_text("1\n00:00:00,000 --> 00:00:02,500\nTest captions\n", encoding="utf-8")
    options = {"width": 160, "height": 90, "duration": 4, "has_audio": False, "crop": [10, 10, 120, 70]}
    ranges = kept_ranges(4, [[1, 2]])
    for original in (False, True):
        project = editing_project(str(source), {}, options, ranges, preview=True, original=original, subtitles=str(subtitles))
        output = tmp_path / f"{original}.mp4"
        render_command(ffmpeg, project, output)
        samples = run_ffmpeg(ffmpeg, "-i", str(output), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-")
        assert abs(len(samples) / 32000 - 3) < 0.15
    decoded = [
        run_ffmpeg(ffmpeg, "-i", str(tmp_path / f"{original}.mp4"), "-frames:v", "1", "-f", "md5", "-") for original in (False, True)
    ]
    assert decoded[0] != decoded[1]


def test_real_ducking_reduces_music_during_voice_and_recovers(ffmpeg, media, tmp_path):
    source, music = media
    amplitudes = []
    for ducking in (False, True):
        project = TimelineProject(
            clips=[TimelineClip(str(source), 0, 4)],
            width=160,
            height=90,
            fps=10,
            audio_tracks=[TimelineAudioTrack(str(music), volume=0.5, ducking=ducking)],
        )
        output = tmp_path / f"duck-{ducking}.mp4"
        render_command(ffmpeg, project, output)
        raw = run_ffmpeg(
            ffmpeg, "-i", str(output), "-vn", "-af", "bandpass=f=880:width_type=h:w=60", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"
        )
        samples = array.array("f", raw)
        amplitudes.append(
            [
                math.sqrt(sum(x * x for x in samples[int(a * 16000) : int(b * 16000)]) / int((b - a) * 16000))
                for a, b in [(0.4, 0.7), (1.4, 1.7), (3.4, 3.7)]
            ]
        )
    plain, ducked = amplitudes
    assert ducked[0] / plain[0] > 0.9
    assert ducked[1] / plain[1] < 0.6
    assert ducked[2] / plain[2] > 0.8


def test_preview_music_starts_at_retained_output_time(ffmpeg, media, tmp_path):
    source, music = media
    run_ffmpeg(ffmpeg, "-f", "lavfi", "-i", "aevalsrc=0.2*sin(2*PI*880*t)*gte(t\\,1.5):s=44100:d=4", str(music))
    state = {"music": str(music), "removed": [[0.5, 1]], "ducking": False, "music_volume": 1}
    project = editing_project(str(source), state, {"width": 160, "height": 90, "duration": 4}, [[2, 3]], preview=True)
    assert project.audio_tracks[0].source_start == 1.5
    output = tmp_path / "music-offset.mp4"
    render_command(ffmpeg, project, output)
    samples = array.array("f", run_ffmpeg(ffmpeg, "-i", str(output), "-vn", "-ac", "1", "-f", "f32le", "-"))
    assert max(abs(sample) for sample in samples) > 0.1


def test_comparison_shows_frames_seeks_and_plays_in_sync(studio, media):
    root, _backend, _source = studio
    source, _music = media
    comparison = root.findChild(QObject, "studioComparison")
    comparison.setProperty("muted", True)
    root.setProperty("page", 2)
    root.setProperty("beforeUrl", QUrl.fromLocalFile(str(source)).toString())
    root.setProperty("afterUrl", QUrl.fromLocalFile(str(source)).toString())
    before = root.findChild(QMediaPlayer, "comparisonBeforePlayer")
    after = root.findChild(QMediaPlayer, "comparisonAfterPlayer")
    for _ in range(100):
        QTest.qWait(20)
        if before.videoSink().videoFrame().isValid() and after.videoSink().videoFrame().isValid():
            break
    assert before.videoSink().videoFrame().isValid()
    assert after.videoSink().videoFrame().isValid()
    assert before.audioOutput().isMuted()
    invoke(comparison, "seek", 1500)
    QTest.qWait(200)
    assert comparison.property("driftMs") <= 80
    assert after.videoSink().videoFrame().toImage().pixelColor(50, 40).lightness() > 230
    invoke(comparison, "togglePlayback")
    QTest.qWait(600)
    assert before.playbackState() == after.playbackState() == QMediaPlayer.PlayingState
    assert after.position() > 1700
    assert comparison.property("driftMs") <= 100
    invoke(comparison, "togglePlayback")
    assert before.playbackState() == after.playbackState() == QMediaPlayer.PausedState
    divider = root.findChild(QObject, "comparisonDivider")
    origin = divider.mapToScene(QPointF(1, 80)).toPoint()
    QTest.mousePress(root, Qt.LeftButton, Qt.NoModifier, origin)
    QTest.mouseMove(root, origin + QPoint(100, 0), 30)
    QTest.mouseRelease(root, Qt.LeftButton, Qt.NoModifier, origin + QPoint(100, 0))
    assert comparison.property("split") > 0.55


def test_real_scene_detection_and_selected_scene_exports(studio, ffmpeg, media, tmp_path, monkeypatch):
    _root, backend, _source = studio
    source, _music = media
    service = backend._montage_editing
    monkeypatch.setattr(service, "_ffmpeg", lambda: ffmpeg)
    service.detectScenes(str(source), 4, 0.3)
    for _ in range(500):
        if not service.busy:
            break
        QTest.qWait(10)
    assert not service.error
    scenes = service.result["scenes"]
    assert [round(scene["start"]) for scene in scenes] == [0, 1, 2]
    scenes[1]["selected"] = False
    monkeypatch.setattr("services.montage_editing.QtWidgets.QFileDialog.getExistingDirectory", lambda *args: str(tmp_path))
    service.exportScenes(str(source), scenes, {"duration": 4, "width": 160, "height": 90, "has_audio": True, "fps": 10})
    for _ in range(1000):
        if not service.busy:
            break
        QTest.qWait(10)
    assert not service.error
    folder = Path(service.result["path"])
    assert len(list(folder.glob("*.mp4"))) == 2
