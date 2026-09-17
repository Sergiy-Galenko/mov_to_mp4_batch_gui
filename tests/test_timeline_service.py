from services.timeline_service import (
    TimelineAudioTrack,
    TimelineClip,
    TimelineProject,
    TimelineService,
)


def test_timeline_clip_and_project_duration():
    clip1 = TimelineClip(source_path="/tmp/v1.mp4", in_point=1.0, out_point=5.0)
    assert clip1.effective_duration() == 4.0

    clip2 = TimelineClip(
        source_path="/tmp/v2.mp4",
        in_point=0.0,
        out_point=6.0,
        transition_to_next="fade",
        transition_duration=1.0,
    )
    assert clip2.effective_duration() == 6.0

    # Project with 2 clips without transition from clip1
    proj = TimelineProject(clips=[clip1, clip2])
    assert proj.total_duration() == 10.0

    # If clip1 has transition to clip2, duration is reduced by transition duration
    clip1.transition_to_next = "fade"
    clip1.transition_duration = 1.0
    assert proj.total_duration() == 9.0


def test_timeline_project_serialization():
    clip = TimelineClip(source_path="/video/intro.mp4", in_point=0.0, out_point=10.0)
    audio = TimelineAudioTrack(audio_path="/music/bg.mp3", volume=0.75, loop=True)
    proj = TimelineProject(title="My Edit", clips=[clip], audio_tracks=[audio])

    d = proj.to_dict()
    assert d["title"] == "My Edit"
    assert len(d["clips"]) == 1
    assert len(d["audio_tracks"]) == 1
    assert d["audio_tracks"][0]["volume"] == 0.75

    restored = TimelineProject.from_dict(d)
    assert restored.title == "My Edit"
    assert restored.clips[0].source_path == "/video/intro.mp4"
    assert restored.audio_tracks[0].loop is True


def test_timeline_service_build_command_transitions_and_audio():
    service = TimelineService(ffmpeg_path="ffmpeg")
    clip1 = TimelineClip(source_path="/tmp/v1.mp4", in_point=0.0, out_point=4.0, transition_to_next="fade", transition_duration=1.0)
    clip2 = TimelineClip(source_path="/tmp/v2.mp4", in_point=0.0, out_point=5.0)
    audio = TimelineAudioTrack(audio_path="/tmp/bg.mp3", volume=0.8, loop=True)

    proj = TimelineProject(clips=[clip1, clip2], audio_tracks=[audio], output_format="mp4")
    cmd = service.build_render_command(proj, "/tmp/out.mp4")

    cmd_str = " ".join(cmd)
    assert "-filter_complex" in cmd_str
    assert "xfade=transition=fade" in cmd_str
    assert "acrossfade=" in cmd_str
    assert "amix=" in cmd_str
    assert "-stream_loop -1" in cmd_str
    assert "/tmp/out.mp4" in cmd[-1]
