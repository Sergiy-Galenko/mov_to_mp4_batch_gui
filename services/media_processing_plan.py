"""Conservative stream decisions: copying requires known, compatible source data."""

from dataclasses import dataclass

from app.models import MediaInfo


@dataclass(frozen=True)
class ProcessingPlan:
    video_copy: bool
    audio_copy: bool
    reason: str = ""


def audio_copy_compatible(extension: str, codec: str | None) -> bool:
    if not codec:
        return False
    codecs = {
        ".mp4": {"aac", "mp3", "alac", "ac3", "eac3"},
        ".m4v": {"aac", "mp3", "alac", "ac3", "eac3"},
        ".mov": {"aac", "mp3", "alac", "ac3", "eac3", "pcm_s16le", "pcm_s24le", "pcm_s32le"},
        ".webm": {"opus", "vorbis"},
        ".avi": {"mp3", "ac3", "pcm_s16le"},
        ".mpg": {"mp2", "mp3", "ac3"},
        ".mpeg": {"mp2", "mp3", "ac3"},
        ".m2ts": {"aac", "ac3", "eac3", "dts"},
        ".ts": {"aac", "ac3", "eac3", "dts", "mp2", "mp3"},
    }
    return extension.lower() == ".mkv" or codec.lower() in codecs.get(extension.lower(), set())


def plan_streams(
    info: MediaInfo | None,
    extension: str,
    *,
    requested: bool,
    video_compatible: bool,
    video_processing: bool,
    audio_processing: bool,
    remove_audio: bool = False,
    cross_container: bool = False,
) -> ProcessingPlan:
    if not requested or info is None or not info.vcodec:
        return ProcessingPlan(False, False, "Немає підтверджених даних потоків або копіювання не обрано")
    if video_processing or not video_compatible:
        return ProcessingPlan(False, False, "Відео потребує перекодування")
    if cross_container and info.subtitle_streams:
        return ProcessingPlan(False, False, "Сумісність субтитрів з новим контейнером не підтверджена")
    audio_copy = remove_audio or (
        not audio_processing and ((not info.acodec and not info.audio_streams) or audio_copy_compatible(extension, info.acodec))
    )
    return ProcessingPlan(True, audio_copy, "Копіювання потоків" if audio_copy else "Копіювання відео, перекодування аудіо")
