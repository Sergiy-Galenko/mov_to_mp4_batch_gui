"""Editor export orchestration; reuses the existing timeline/FFmpeg filter builder."""
from __future__ import annotations

import copy
import re
import tempfile
import threading
import time
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from services.background_job import BackgroundJob
from services.montage_editing import require_success
from services.timeline_service import TimelineProject, TimelineService


def ass_time(seconds):
    centis = max(0, round(float(seconds) * 100))
    return f"{centis // 360000}:{centis // 6000 % 60:02}:{centis // 100 % 60:02}.{centis % 100:02}"


def title_subtitles(data, path):
    """One ASS overlay stream for real titles and imported subtitle cues."""
    width, height = data["project_settings"]["width"], data["project_settings"]["height"]
    header = f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n\n[V4+ Styles]\n"
    header += "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    header += "Style: Default,Arial,42,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,30,30,40,1\n\n[Events]\n"
    header += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = []
    titles = data["titles"] if data["tracks"].get("titles_visible", True) else []
    for title in [*data.get("subtitles", []), *titles]:
        text = str(title.get("text", "")).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")
        if not text or title["end"] <= title["start"]:
            continue
        tags = ""
        if title in titles:
            color = str(title.get("color", "#ffffff")).lstrip("#")
            color = color if re.fullmatch(r"[0-9a-fA-F]{6}", color) else "ffffff"
            bgr = color[4:6] + color[2:4] + color[:2]
            font = re.sub(r"[{},\\\r\n]", "", title.get("font", "Arial"))
            alpha = round(255 * (1 - max(0, min(1, float(title.get("opacity", 1))))))
            tags = (f"{{\\fn{font}\\fs{int(title.get('size', 48))}\\b{int(title.get('bold', False))}"
                    f"\\c&H{bgr}&\\alpha&H{alpha:02X}&\\an{int(title.get('alignment', 2))}"
                    f"\\pos({round(title.get('x', .5)*width)},{round(title.get('y', .85)*height)})"
                    + ("\\bord8\\shad0\\3c&H000000&" if title.get("background") else "\\bord2") + "}")
        events.append(f"Dialogue: 0,{ass_time(title['start'])},{ass_time(title['end'])},Default,,0,0,0,,{tags}{text}\n")
    Path(path).write_text(header + "".join(events), encoding="utf-8")


def render_project(data, subtitle_path=""):
    settings, tracks = data["project_settings"], data["tracks"]
    clips = []
    for clip in data["timeline"]["clips"]:
        if clip.get("enabled", True):
            clips.append({**clip, "has_audio": clip.get("has_audio", False) and clip.get("audio_enabled", True) and not tracks.get("audio_muted", False)})
    audio = [] if tracks.get("music_muted") else data["timeline"]["audio_tracks"]
    export = data["export_settings"]
    resolution = export.get("resolution", "timeline")
    width, height = (map(int, resolution.split("x")) if resolution != "timeline" else (settings["width"], settings["height"]))
    return TimelineProject.from_dict({"title": data["project_name"], "clips": clips, "audio_tracks": audio,
        "output_format": export["format"], "width": width, "height": height,
        "fps": float(export.get("fps") or settings["fps"]), "subtitle_path": subtitle_path})


def export_command(ffmpeg, data, output, subtitles=""):
    project = render_project(data, subtitles)
    options = data["export_settings"]
    if options.get("fast_copy") or options.get("codec") == "copy":
        if len(project.clips) != 1 or project.clips[0].media_type != "video" or project.clips[0].crop or project.audio_tracks or subtitles or options.get("resolution", "timeline") != "timeline" or options.get("fps"):
            raise ValueError("Fast Copy requires one video clip without crop, titles, subtitles, music or resolution/frame-rate changes.")
        clip = project.clips[0]
        return [ffmpeg, "-y", "-ss", str(clip.in_point), "-i", clip.source_path, "-t", str(clip.effective_duration()),
                "-map", "0:v:0", *(["-map", "0:a?"] if clip.has_audio else ["-an"]), "-c", "copy", str(output)]
    command = TimelineService(ffmpeg).build_render_command(project, output)
    codec = options.get("codec", "h264")
    encoder = {"h264": "libx264", "h265": "libx265", "prores": "prores_ks"}.get(codec)
    if encoder is None:
        raise ValueError("Unsupported export codec")
    if codec == "prores" and options["format"] != "mov":
        raise ValueError("ProRes requires the MOV format")
    command[command.index("-c:v") + 1] = encoder
    if codec == "prores":
        command[command.index("-c:a") + 1] = "pcm_s16le"
        if "-pix_fmt" in command:
            command[command.index("-pix_fmt") + 1] = "yuv422p10le"
        command[-1:-1] = ["-profile:v", "3"]
    else:
        quality = {"low": "28", "medium": "23", "high": "18", "auto": "23"}.get(options.get("quality"), "18")
        command[-1:-1] = ["-crf", quality, "-preset", "medium"]
        if options.get("bitrate", 0) > 0:
            command[-1:-1] = ["-b:v", f"{int(options['bitrate'])}k"]
    return command


class EditorRenderService(BackgroundJob):
    timingChanged = QtCore.Signal()

    def __init__(self, backend):
        super().__init__(backend)
        self.backend = backend
        self._started = 0
        self._elapsed = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self.changed.connect(self._on_changed)

    def _on_changed(self):
        if self.busy and not self._timer.isActive():
            self._started = time.monotonic()
            self._timer.start()
        elif not self.busy:
            self._timer.stop()

    def _tick(self):
        self._elapsed = int(time.monotonic() - self._started)
        self.timingChanged.emit()

    @QtCore.Property(int, notify=timingChanged)
    def elapsed(self):
        return self._elapsed

    @QtCore.Property(int, notify=timingChanged)
    def remaining(self):
        return int(self._elapsed * (100 - self.progress) / self.progress) if self.progress > 0 else -1

    @QtCore.Slot("QVariantMap", result=str)
    def chooseOutput(self, data):
        options = data["export_settings"]
        base = Path(options.get("directory") or str(Path.home() / "Movies"))
        name = Path(options.get("filename") or (data["project_name"] + "_Final")).name
        suggestion = base / (Path(name).stem + "." + options["format"])
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Export video", str(suggestion), f"Video (*.{options['format']})")
        return path

    @QtCore.Slot("QVariantMap", str, result=bool)
    def export(self, data, destination):
        snapshot = copy.deepcopy(data)
        if not destination:
            return False
        output = Path(destination).expanduser().resolve()
        sources = {Path(c["source_path"]).resolve() for c in data["timeline"]["clips"]}
        sources.update(Path(a["audio_path"]).resolve() for a in data["timeline"]["audio_tracks"])
        ffmpeg = self.backend.ffmpegPath
        self._elapsed = 0
        self.timingChanged.emit()

        def work(context):
            if not ffmpeg or not Path(ffmpeg).is_file():
                raise ValueError("Configure FFmpeg before exporting.")
            if output in sources:
                raise ValueError("Choose a new output file; source media cannot be overwritten.")
            if output.suffix.lower() != "." + snapshot["export_settings"]["format"]:
                raise ValueError("The filename extension must match the selected format.")
            for source in sources:
                if not source.is_file():
                    raise ValueError(f"Media offline: {source.name}")
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".editor-render-", dir=output.parent) as directory:
                folder = Path(directory)
                subtitles = ""
                if snapshot["subtitles"] or (snapshot["titles"] and snapshot["tracks"].get("titles_visible", True)):
                    subtitles = str(folder / "overlays.ass")
                    title_subtitles(snapshot, subtitles)
                temporary = folder / output.name
                command = export_command(ffmpeg, snapshot, temporary, subtitles)
                progress = folder / "progress.txt"
                command[1:1] = ["-nostdin", "-progress", str(progress), "-stats_period", "0.25"]
                duration = render_project(snapshot).total_duration()
                done = threading.Event()
                def monitor():
                    while not done.wait(.25):
                        try:
                            values = re.findall(r"out_time_us=(\d+)", progress.read_text())
                            if values:
                                context.progress("exporting", min(99, int(int(values[-1]) / 10000 / max(.001, duration))))
                        except OSError:
                            pass
                watcher = threading.Thread(target=monitor, daemon=True)
                watcher.start()
                try:
                    context.progress("exporting", 0)
                    require_success(context.run(command, timeout=86400))
                    context.check()
                    temporary.replace(output)
                finally:
                    done.set()
                    watcher.join(timeout=1)
            return {"path": str(output), "kind": "editor_export"}
        return self.start_job(work)
