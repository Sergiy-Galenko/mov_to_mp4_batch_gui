"""Qt facade for the editing workspace. Media work stays in cancellable subprocesses."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from services.background_job import BackgroundJob
from services.subtitle_editing import (
    kept_ranges,
    merge_cues,
    normalize_cues,
    parse_subtitles,
    retime_cues,
    scenes_from_timestamps,
    seconds,
    serialize_subtitles,
    split_cue,
    word_cut,
)
from services.timeline_service import TimelineAudioTrack, TimelineClip, TimelineProject, TimelineService
from services.whisper_environment import worker_command, worker_environment
from services.whisper_setup import read_worker_result


def require_success(process):
    if process.returncode:
        raise RuntimeError((process.stderr or process.stdout or "FFmpeg failed")[-3000:])


def export_path(path: str, extension: str, allowed: tuple[str, ...]) -> Path:
    """Never silently overwrite a filename the save dialog did not confirm."""
    target = Path(path)
    if not target.suffix:
        target = target.with_suffix(extension)
        if target.exists():
            raise ValueError(f"The output already exists. Select its full filename to replace it: {target.name}")
    if target.suffix.lower() not in allowed:
        raise ValueError(f"Choose a file with one of these extensions: {', '.join(allowed)}")
    return target


def preview_ranges(ranges: list, start: float, limit=12.0) -> list:
    result = []
    for left, right in ranges:
        left = max(left, start)
        if left >= right:
            continue
        right = min(right, left + limit)
        result.append([left, right])
        limit -= right - left
        if limit <= 0.001:
            break
    if not result:
        raise ValueError("Move the playhead into a retained part of the video")
    return result


def editing_project(source: str, document: dict, options: dict, ranges: list, *, preview=False, original=False, subtitles=""):
    width, height = int(options["width"]), int(options["height"])
    crop = options.get("crop") if not original else []
    if crop:
        x, y, w, h = (int(value) for value in crop)
        if x < 0 or y < 0 or w < 2 or h < 2 or x + w > width or y + h > height:
            raise ValueError("Crop rectangle is outside the source frame")
        width, height = w, h
    if preview:
        factor = min(1.0, 960 / max(width, height))
        width, height = int(width * factor), int(height * factor)
    width, height = max(2, width // 2 * 2), max(2, height // 2 * 2)
    music = document.get("music", "")
    tracks = []
    if music and not original:
        if not Path(music).is_file():
            raise ValueError("The background music file is missing")
        kept = kept_ranges(
            options["duration"], document.get("removed", []), options.get("start", 0), options.get("end") or options["duration"]
        )
        music_start = sum(max(0, min(right, ranges[0][0]) - left) for left, right in kept) if preview else 0
        tracks.append(
            TimelineAudioTrack(
                audio_path=music,
                volume=float(document.get("music_volume", 0.3)),
                loop=True,
                source_start=music_start,
                ducking=bool(document.get("ducking", True)),
                duck_ratio=float(document.get("duck_ratio", 8)),
                duck_release_ms=float(document.get("duck_release_ms", 450)),
            )
        )
    ext = Path(source).suffix.lower()
    is_image = ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif", ".jxl"}
    still_dur = float(options.get("still_duration") or 5.0) if is_image else 5.0

    return TimelineProject(
        clips=[
            TimelineClip(
                source_path=source,
                in_point=a,
                out_point=b,
                has_audio=bool(options.get("has_audio")) if not is_image else False,
                crop=crop or [],
                media_type="image" if is_image else "video",
                still_duration=still_dur,
            )
            for a, b in ranges
        ],
        audio_tracks=tracks,
        width=width,
        height=height,
        fps=min(60.0, max(1.0, float(options.get("fps") or 30))),
        subtitle_path=subtitles if not original else "",
    )


class MontageEditing(BackgroundJob):
    def __init__(self, backend):
        super().__init__(backend)
        self.backend = backend
        self._preview_dirs = []

    @QtCore.Slot(str, result=str)
    def fileUrl(self, path):
        return QtCore.QUrl.fromLocalFile(path).toString() if path else ""

    @QtCore.Slot(str, result="QVariantMap")
    def loadDocument(self, source):
        session = self.backend.montage_service.session_store.get_session(source) or {}
        return dict(session.get("editing_tools") or {})

    @QtCore.Slot(str, "QVariantMap")
    def saveDocument(self, source, document):
        if not source:
            return
        store = self.backend.montage_service.session_store
        session = dict(store.get_session(source) or {})
        session["editing_tools"] = dict(document)
        store.save_session(source, session)

    @QtCore.Slot(str, result=str)
    def chooseFile(self, kind):
        filters = {"subtitles": "Subtitles (*.srt *.vtt)", "music": "Audio (*.wav *.mp3 *.m4a *.flac *.ogg);;All files (*)"}
        if kind not in filters:
            return ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Media Converter", "", filters[kind])
        return path

    @QtCore.Slot(str, result="QVariantMap")
    def importSubtitles(self, path):
        try:
            if Path(path).stat().st_size > 4 * 1024 * 1024:
                raise ValueError("Subtitle file is too large (maximum 4 MiB)")
            return {"ok": True, "cues": parse_subtitles(Path(path).read_text(encoding="utf-8-sig"))}
        except (OSError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}

    @QtCore.Slot("QVariantList", str, "QVariantMap", result="QVariantMap")
    def editCues(self, cues, operation, args):
        try:
            if operation == "split":
                result = split_cue(cues, args["id"], args["at"], int(args["cursor"]))
            elif operation == "merge":
                result = merge_cues(cues, args["id"])
            elif operation == "update":
                result = normalize_cues(
                    [{**cue, **args["values"], "words": []} if cue["id"] == args["id"] else cue for cue in cues], args.get("duration")
                )
            elif operation == "add":
                result = normalize_cues([*cues, args], args.get("duration"))
            elif operation == "delete":
                result = [cue for cue in cues if cue["id"] != args["id"]]
            else:
                raise ValueError("Unknown subtitle operation")
            return {"ok": True, "cues": result}
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            return {"ok": False, "error": str(exc) or "Select a subtitle first"}

    @QtCore.Slot("QVariantList", int, int, result="QVariantMap")
    def cutWords(self, words, first, last):
        try:
            return {"ok": True, "range": word_cut(words, first, last)}
        except (ValueError, KeyError, TypeError) as exc:
            return {"ok": False, "error": str(exc)}

    @QtCore.Slot(str, "QVariantMap", "QVariantMap", result=bool)
    def exportSubtitles(self, source, document, options):
        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            None, "Subtitles", str(Path(source).with_suffix(".edited.srt")), "SubRip (*.srt);;WebVTT (*.vtt)"
        )
        if not path:
            return False
        try:
            target = export_path(path, ".vtt" if "vtt" in selected_filter else ".srt", (".srt", ".vtt"))
            if target.resolve() in {Path(source).resolve(), Path(document.get("music") or source).resolve()}:
                raise ValueError("The output cannot overwrite an input file")
            ranges = self._ranges(document, options)
            text = serialize_subtitles(retime_cues(document.get("cues", []), ranges), target.suffix[1:].lower())
            self._write_text(target, text)
            return True
        except (OSError, ValueError) as exc:
            self._error = str(exc)
            self.changed.emit()
            return False

    @staticmethod
    def _write_text(path, text):
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _ranges(document, options):
        duration = seconds(options["duration"])
        return kept_ranges(duration, document.get("removed", []), options.get("start", 0), options.get("end") or duration)

    def _ffmpeg(self):
        path = self.backend.ffmpegPath
        if not path or not Path(path).is_file():
            raise ValueError("Select a working FFmpeg executable in the application settings")
        return path

    @QtCore.Slot(str)
    def transcribe(self, source):
        settings = dict(self.backend._last_settings_map)

        def work(context):
            ffmpeg = self._ffmpeg()
            context.progress("recognizing", 10)
            with tempfile.TemporaryDirectory(prefix="montage-words-") as folder:
                output = Path(folder) / "words.json"
                command = worker_command(
                    "align",
                    source,
                    str(output),
                    settings.get("subtitle_model") or "base",
                    settings.get("subtitle_engine") or "auto",
                    settings.get("subtitle_device") or "auto",
                )
                env = worker_environment(ffmpeg)
                env.setdefault("OMP_NUM_THREADS", "2")
                read_worker_result(context.run(command, timeout=7200, env=env))
                data = json.loads(output.read_text(encoding="utf-8"))
                data["cues"] = normalize_cues(data.get("cues", []))
                if not data["cues"] or not data.get("words"):
                    raise ValueError("No timed speech found in this file")
                return {"kind": "transcript", "source": source, **data}

        self.start_job(work)

    @QtCore.Slot(str, float, float)
    def detectScenes(self, source, duration, threshold):
        def work(context):
            ffmpeg = self._ffmpeg()
            context.progress("scenes", 15)
            level = max(0.01, min(0.95, float(threshold)))
            command = [
                ffmpeg,
                "-hide_banner",
                "-nostdin",
                "-i",
                source,
                "-an",
                "-vf",
                f"scale=320:-2,select='gt(scene,{level:.3f})',metadata=print",
                "-fps_mode",
                "vfr",
                "-f",
                "null",
                "-",
            ]
            process = context.run(command, timeout=7200)
            require_success(process)
            times = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", process.stderr + process.stdout)]
            return {"kind": "scenes", "source": source, "scenes": scenes_from_timestamps(times, duration)}

        self.start_job(work)

    def _render(self, context, ffmpeg, source, document, options, ranges, output, *, preview=False, original=False):
        with tempfile.TemporaryDirectory(prefix="montage-subs-") as folder:
            subtitles = ""
            if document.get("burn_subtitles") and document.get("cues") and not original:
                subtitle_file = Path(folder) / "captions.srt"
                subtitle_file.write_text(serialize_subtitles(retime_cues(document["cues"], ranges)), encoding="utf-8")
                subtitles = str(subtitle_file)
            project = editing_project(source, document, options, ranges, preview=preview, original=original, subtitles=subtitles)
            command = TimelineService(ffmpeg).build_render_command(project, output)
            command[1:1] = ["-hide_banner", "-loglevel", "error", "-nostdin", "-filter_complex_threads", "2"]
            command[-1:-1] = ["-preset", "veryfast" if preview else "medium", "-threads", "2"]
            require_success(context.run(command, timeout=300 if preview else 14400))

    @QtCore.Slot(str, "QVariantMap", "QVariantMap", float)
    def preview(self, source, document, options, position):
        def work(context):
            ffmpeg = self._ffmpeg()
            ranges = preview_ranges(self._ranges(document, options), position)
            directory = Path(tempfile.mkdtemp(prefix="montage-preview-"))
            try:
                context.progress("preview", 10)
                before, after = directory / "before.mp4", directory / "after.mp4"
                self._render(context, ffmpeg, source, document, options, ranges, before, preview=True, original=True)
                context.progress("preview", 55)
                self._render(context, ffmpeg, source, document, options, ranges, after, preview=True)
                context.check()
                self._preview_dirs.append(directory)
                return {"kind": "preview", "source": source, "before": self.fileUrl(str(before)), "after": self.fileUrl(str(after))}
            except BaseException:
                shutil.rmtree(directory, ignore_errors=True)
                raise

        self.start_job(work)

    @QtCore.Slot(str, "QVariantMap", "QVariantMap")
    def exportVideo(self, source, document, options):
        if self.busy:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Export montage", str(Path(source).with_suffix(".edited.mp4")), "MP4 (*.mp4)")
        if not path:
            return

        def work(context):
            output = export_path(path, ".mp4", (".mp4",))
            ffmpeg = self._ffmpeg()
            if output.resolve() == Path(source).resolve() or (
                document.get("music") and output.resolve() == Path(document["music"]).resolve()
            ):
                raise ValueError("The output cannot overwrite an input file")
            context.progress("exporting", 10)
            with tempfile.TemporaryDirectory(prefix=".montage-export-", dir=output.parent) as folder:
                temporary = Path(folder) / "output.mp4"
                ranges = self._ranges(document, options)
                if not ranges:
                    raise ValueError("All video has been removed; undo a cut before exporting")
                self._render(context, ffmpeg, source, document, options, ranges, temporary)
                context.check()
                temporary.replace(output)
            return {"kind": "export", "source": source, "path": str(output)}

        self.start_job(work)

    @QtCore.Slot(str, "QVariantList", "QVariantMap")
    def exportScenes(self, source, scenes, options):
        if self.busy:
            return
        selected = [scene for scene in scenes if scene.get("selected")]
        if not selected:
            return
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Export scenes")
        if not folder:
            return

        def work(context):
            ffmpeg = self._ffmpeg()
            target = Path(folder) / f"{Path(source).stem}_scenes_{uuid.uuid4().hex[:8]}"
            with tempfile.TemporaryDirectory(prefix=".scene-export-", dir=folder) as temporary:
                staging = Path(temporary) / "scenes"
                staging.mkdir()
                for index, scene in enumerate(selected):
                    context.progress("exporting", int(100 * index / len(selected)))
                    start, end = seconds(scene["start"]), seconds(scene["end"])
                    if not 0 <= start < end <= seconds(options["duration"]):
                        raise ValueError("Scene is outside the source duration")
                    self._render(context, ffmpeg, source, {}, options, [[start, end]], staging / f"scene_{index + 1:03}.mp4", original=True)
                context.check()
                staging.rename(target)
            return {"kind": "export", "source": source, "path": str(target), "count": len(selected)}

        self.start_job(work)

    @QtCore.Slot()
    def clearPreviews(self):
        if self.busy:
            return
        for directory in self._preview_dirs:
            shutil.rmtree(directory, ignore_errors=True)
        self._preview_dirs.clear()

    def shutdown(self):
        super().shutdown()
        for directory in self._preview_dirs:
            shutil.rmtree(directory, ignore_errors=True)
