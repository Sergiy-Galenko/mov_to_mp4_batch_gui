"""Versioned editing documents, atomic project files and independent autosave copies.

The document contains edits only. Selection, playback and panel geometry are UI state.
Disk writes and media probing run outside Qt's event thread.
"""
from __future__ import annotations

import contextlib
import copy
import json
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app.paths import APP_DATA_DIR
from services.background_job import BackgroundJob


def now():
    return datetime.now(UTC).isoformat()


def new_document(name="Untitled Project"):
    return {
        "version": 1, "project_id": uuid.uuid4().hex, "project_name": name, "created_at": now(),
        "project_settings": {"width": 1920, "height": 1080, "fps": 30, "autosave": True, "autosave_minutes": 5},
        "media": [], "timeline": {"clips": [], "audio_tracks": []}, "titles": [], "subtitles": [],
        "editing_documents": {}, "effects": [],
        "tracks": {"video_locked": False, "titles_locked": False, "audio_locked": False,
                   "titles_visible": True, "audio_muted": False, "music_muted": False},
        "export_settings": {"format": "mp4", "codec": "h264", "quality": "high", "resolution": "timeline",
                            "fps": 0, "fast_copy": False, "directory": "", "filename": "", "bitrate": 0},
    }


def fingerprint(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False)


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_document(path):
    path = Path(path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Project files must be smaller than 16 MiB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported project version")
    defaults = new_document()
    defaults.update(data)
    data = defaults
    if not isinstance(data["timeline"], dict) or not isinstance(data["timeline"].get("clips"), list):
        raise ValueError("Invalid timeline")
    for field in ("media", "titles", "subtitles"):
        if not isinstance(data[field], list) or any(not isinstance(item, dict) for item in data[field]):
            raise ValueError(f"Invalid {field}")
    settings = {**new_document()["project_settings"], **data["project_settings"]}
    if not (16 <= int(settings["width"]) <= 16384 and 16 <= int(settings["height"]) <= 16384
            and 1 <= float(settings["fps"]) <= 240):
        raise ValueError("Invalid project resolution or frame rate")
    settings["autosave_minutes"] = settings["autosave_minutes"] if settings["autosave_minutes"] in (1, 2, 5, 10, 15) else 5
    data["project_settings"] = settings
    data["export_settings"] = {**new_document()["export_settings"], **data["export_settings"]}
    data["tracks"] = {**new_document()["tracks"], **data["tracks"]}
    fingerprint(data)  # Reject NaN/infinity before they can enter QML.
    for clip in data["timeline"]["clips"]:
        if not isinstance(clip, dict) or not isinstance(clip.get("source_path"), str):
            raise ValueError("Invalid timeline clip")
        if float(clip.get("in_point", 0)) < 0 or float(clip.get("out_point", 0)) <= float(clip.get("in_point", 0)):
            raise ValueError("Invalid clip range")
    # Resolve relative media references against the project, never against cwd.
    for item, key in [(m, "path") for m in data["media"]] + [(c, "source_path") for c in data["timeline"]["clips"]] + [(a, "audio_path") for a in data["timeline"].get("audio_tracks", [])]:
        if item.get(key) and not Path(item[key]).is_absolute():
            item[key] = str((path.parent / item[key]).resolve())
    return data


class EditorProject(QtCore.QObject):
    changed = QtCore.Signal()
    documentChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()
    loaded = QtCore.Signal()
    saved = QtCore.Signal()
    _writeDone = QtCore.Signal(dict)

    def __init__(self, backend, directory=None):
        super().__init__(backend)
        self.backend = backend
        self.directory = Path(directory or APP_DATA_DIR / "editor")
        self._data = new_document()
        self._path = ""
        self._saved = fingerprint(self._data)
        self._selection = ""
        self._error = ""
        self._status = "new"
        self._saving = False
        self._autosaving = False
        self._closed = False
        self._last_autosave = ""
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="project-save")
        self._writeDone.connect(self._finish_write)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.autosave)
        self._timer.start(300000)
        self._importer = BackgroundJob(self)
        self._importer.completed.connect(self._imported)
        self._recent = []
        with contextlib.suppress(OSError, ValueError, TypeError):
            self._recent = json.loads((self.directory / "recent.json").read_text())[:12]

    @QtCore.Property("QVariantMap", notify=documentChanged)
    def data(self):
        return copy.deepcopy(self._data)

    @QtCore.Property(str, notify=changed)
    def path(self):
        return self._path

    @QtCore.Property(bool, notify=changed)
    def dirty(self):
        return fingerprint(self._data) != self._saved

    @QtCore.Property(bool, notify=changed)
    def saving(self):
        return self._saving

    @QtCore.Property(str, notify=changed)
    def status(self):
        return self._status

    @QtCore.Property(str, notify=changed)
    def error(self):
        return self._error

    @QtCore.Property(str, notify=changed)
    def lastAutosave(self):
        return self._last_autosave

    @QtCore.Property("QVariantList", notify=changed)
    def recent(self):
        return self._recent

    @QtCore.Property("QVariantList", notify=changed)
    def recoveries(self):
        found = []
        for path in sorted((self.directory / "autosave").glob("*.vproj"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = read_document(path)
                original = data.get("recovery_path", "")
                if original and Path(original).exists() and Path(original).stat().st_mtime >= path.stat().st_mtime:
                    continue
                found.append({"path": str(path), "name": data["project_name"], "modified": data.get("modified_at", "")})
            except (OSError, ValueError, TypeError, KeyError):
                continue
        return found

    @QtCore.Property("QVariantList", notify=changed)
    def offline(self):
        return [m for m in self._data["media"] if not Path(m["path"]).is_file()]

    @QtCore.Property(str, notify=selectionChanged)
    def selectedId(self):
        return self._selection

    @QtCore.Property("QVariantMap", notify=selectionChanged)
    def selected(self):
        for kind, items in (("video", self._data["timeline"]["clips"]), ("title", self._data["titles"]), ("audio", self._data["timeline"]["audio_tracks"])):
            for item in items:
                if item.get("id") == self._selection:
                    return {**copy.deepcopy(item), "kind": kind}
        return {}

    @QtCore.Property(QtCore.QObject, constant=True)
    def importer(self):
        return self._importer

    def _notify(self):
        self._timer.setInterval(int(self._data["project_settings"].get("autosave_minutes", 5)) * 60000)
        self.documentChanged.emit()
        self.selectionChanged.emit()
        self.changed.emit()

    @QtCore.Slot("QVariantMap")
    def restore(self, data):
        self._data = copy.deepcopy(data)
        self._notify()

    @QtCore.Slot("QVariantMap")
    def update(self, values):
        self._data = {**self._data, **copy.deepcopy(values)}
        self._notify()

    @QtCore.Slot(str, "QVariantMap")
    def updateSection(self, section, values):
        if section in ("project_settings", "export_settings", "tracks", "editing_documents"):
            self.update({section: {**self._data[section], **values}})

    @QtCore.Slot(str)
    def select(self, identifier):
        self._selection = identifier
        self.selectionChanged.emit()

    @QtCore.Slot("QVariantMap")
    def editSelected(self, values):
        selected = self.selected
        if not selected or self._locked(selected["kind"]):
            return
        collections = {"video": self._data["timeline"]["clips"], "audio": self._data["timeline"]["audio_tracks"], "title": self._data["titles"]}
        for item in collections[selected["kind"]]:
            if item["id"] == self._selection:
                item.update(copy.deepcopy(values))
        self._notify()

    def _locked(self, kind):
        return self._data["tracks"].get({"video": "video_locked", "title": "titles_locked", "audio": "audio_locked"}[kind], False)

    @QtCore.Slot()
    def deleteSelected(self):
        item = self.selected
        if not item or self._locked(item["kind"]):
            return
        if item["kind"] == "title":
            self._data["titles"] = [c for c in self._data["titles"] if c["id"] != self._selection]
        else:
            key = "clips" if item["kind"] == "video" else "audio_tracks"
            self._data["timeline"][key] = [c for c in self._data["timeline"][key] if c["id"] != self._selection]
        self._selection = ""
        self._notify()

    @QtCore.Slot(str, "QVariantMap")
    def create(self, name, settings):
        if self._saving:
            return
        self._data = new_document(name.strip() or "Untitled Project")
        self._data["project_settings"].update(settings)
        self._path, self._selection, self._error, self._status = "", "", "", "new"
        self._saved = fingerprint(self._data)
        self._notify()
        self.loaded.emit()

    @QtCore.Slot(str)
    def rename(self, name):
        if name.strip():
            self.update({"project_name": name.strip()[:200]})

    @QtCore.Slot(result=str)
    def chooseFolder(self):
        return QtWidgets.QFileDialog.getExistingDirectory(None, "Project location", str(Path.home() / "Movies"))

    @QtCore.Slot(result=str)
    def chooseProject(self):
        return QtWidgets.QFileDialog.getOpenFileName(None, "Open project", "", "Video project (*.vproj)")[0]

    @QtCore.Slot(str, result=bool)
    def open(self, path):
        if self._saving:
            return False
        try:
            data = read_document(path)
            data.pop("modified_at", None)
            data.pop("recovery_path", None)
            self._data = data
            self._path = str(Path(path).resolve())
            self._saved = fingerprint(data)
            self._selection, self._error, self._status = "", "", "saved"
            self._remember(self._path)
            self._notify()
            self.loaded.emit()
            return True
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._error, self._status = str(exc), "open_failed"
            self.changed.emit()
            return False

    def _remember(self, path):
        self._recent = [{"path": path, "name": self._data["project_name"], "modified": now()}, *[p for p in self._recent if p["path"] != path]][:12]
        recent = copy.deepcopy(self._recent)
        self._executor.submit(atomic_write, self.directory / "recent.json", recent)

    @QtCore.Slot(result=bool)
    def save(self):
        return self.saveTo(self._path) if self._path else self.saveAs()

    @QtCore.Slot(result=bool)
    def saveAs(self):
        target, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save project", self._path or str(Path.home() / (self._data["project_name"] + ".vproj")), "Video project (*.vproj)")
        return self.saveTo(target) if target else False

    @QtCore.Slot(str, result=bool)
    def saveTo(self, path):
        if self._saving or not path:
            return False
        path = Path(path).expanduser()
        if path.suffix.lower() != ".vproj":
            path = path.with_suffix(".vproj")
            if path.exists():
                self._error = "Choose the complete existing .vproj filename to confirm replacement."
                self.changed.emit()
                return False
        if str(path.resolve()) in {m["path"] for m in self._data["media"]}:
            self._error = "The project cannot replace source media."
            self.changed.emit()
            return False
        self._saving, self._status, self._error = True, "saving", ""
        self.changed.emit()
        self._write(path.resolve(), False)
        return True

    def _write(self, path, autosave):
        snapshot = copy.deepcopy(self._data)
        stamp = fingerprint(snapshot)
        snapshot["modified_at"] = now()
        if autosave:
            snapshot["recovery_path"] = self._path
        project_id = self._data["project_id"]

        def work():
            error = ""
            try:
                atomic_write(path, snapshot)
            except (OSError, ValueError) as exc:
                error = str(exc)
            if not self._closed:
                self._writeDone.emit({"path": str(path), "autosave": autosave, "stamp": stamp, "id": project_id, "error": error})
        self._executor.submit(work)

    @QtCore.Slot(dict)
    def _finish_write(self, result):
        automatic = result["autosave"]
        if automatic:
            self._autosaving = False
        else:
            self._saving = False
        if result["id"] != self._data["project_id"]:
            return
        if result["error"]:
            self._error, self._status = result["error"], "save_failed"
        elif automatic:
            self._last_autosave = now()
        else:
            self._path, self._saved, self._status = result["path"], result["stamp"], "saved"
            self._remember(self._path)
            if not self.dirty:
                self._autosave_path().unlink(missing_ok=True)
            self.saved.emit()
        self.changed.emit()

    def _autosave_path(self):
        return self.directory / "autosave" / (self._data["project_id"] + ".vproj")

    @QtCore.Slot()
    def autosave(self):
        if self.dirty and not self._saving and not self._autosaving and self._data["project_settings"].get("autosave", True):
            self._autosaving = True
            self._write(self._autosave_path(), True)

    @QtCore.Slot(str, result=bool)
    def recover(self, path):
        try:
            data = read_document(path)
            original = data.pop("recovery_path", "")
            data.pop("modified_at", None)
            self._data, self._path, self._saved, self._selection = data, original, "", ""
            self._status, self._error = "recovered", ""
            self._notify()
            self.loaded.emit()
            return True
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._error = str(exc)
            self.changed.emit()
            return False

    @QtCore.Slot(str)
    def discardRecovery(self, path):
        candidate = Path(path).resolve()
        if candidate.parent == (self.directory / "autosave").resolve():
            candidate.unlink(missing_ok=True)
            self.changed.emit()

    @QtCore.Slot()
    def discardAutosave(self):
        # Queue deletion after any in-flight write so discarded edits cannot reappear.
        self._executor.submit(lambda path=self._autosave_path(): path.unlink(missing_ok=True))

    @QtCore.Slot()
    def chooseMedia(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(None, "Import media", "", "Media (*.mov *.mp4 *.mkv *.avi *.webm *.m4v *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.heic *.avif);;All files (*)")
        if paths:
            self.importMedia(paths, False)

    @QtCore.Slot("QVariantList", bool)
    def importMedia(self, paths, append=False):
        paths = [QtCore.QUrl(p).toLocalFile() if str(p).startswith("file:") else str(p) for p in paths]
        generation = self._data["project_id"]
        def work(context):
            items = []
            for index, source in enumerate(dict.fromkeys(paths)):
                context.check()
                path = Path(source).resolve()
                if not path.is_file():
                    raise ValueError(f"Media offline: {path.name}")
                meta = self.backend.montage_service.get_media_metadata(path)
                kind = meta.get("media_type", "video")
                if kind not in ("video", "image", "audio"):
                    raise ValueError(f"Unsupported media: {path.name}")
                item = {**meta, "id": uuid.uuid4().hex, "path": str(path), "name": path.name, "media_type": kind,
                        "duration": float(meta.get("duration") or (5 if kind == "image" else 0)), "thumbnail": ""}
                if kind == "image":
                    item["thumbnail"] = self.fileUrl(str(path))
                elif kind == "video":
                    thumbnails = self.backend.montage_service.preview_service.thumbnail_strip(path, count=1, duration=item["duration"])
                    if thumbnails:
                        item["thumbnail"] = self.fileUrl(thumbnails[0])
                items.append(item)
                context.progress("importing", round((index + 1) * 100 / len(paths)))
            return {"items": items, "append": append, "generation": generation}
        self._importer.start_job(work)

    def _imported(self, result):
        if result["generation"] != self._data["project_id"]:
            return
        for item in result["items"]:
            existing = next((m for m in self._data["media"] if m["path"] == item["path"]), None)
            if not existing:
                self._data["media"].append(item)
            if result["append"]:
                self.addToTimeline((existing or item)["id"])
        self._notify()

    @QtCore.Slot(str)
    def addToTimeline(self, media_id):
        media = next((m for m in self._data["media"] if m["id"] == media_id), None)
        if not media:
            return
        identifier = uuid.uuid4().hex
        if media["media_type"] == "audio":
            if self._locked("audio"):
                return
            self._data["timeline"]["audio_tracks"].append({"id": identifier, "audio_path": media["path"], "name": media["name"], "volume": 0.8, "loop": True, "ducking": True, "offset": 0})
        else:
            if self._locked("video"):
                return
            duration = media["duration"]
            if duration <= 0:
                self._error = "The media duration could not be read. Configure FFmpeg and import the file again."
                self.changed.emit()
                return
            self._data["timeline"]["clips"].append({"id": identifier, "media_id": media_id, "name": media["name"],
                "source_path": media["path"], "in_point": 0, "out_point": duration, "source_duration": duration,
                "media_type": media["media_type"], "still_duration": duration, "has_audio": media.get("has_audio", False),
                "audio_enabled": True, "enabled": True, "crop": [], "crop_aspect": "free", "width": media.get("width", 1920),
                "height": media.get("height", 1080), "fps": media.get("fps", 30), "thumbnail": media.get("thumbnail", ""),
                "transition_to_next": "none", "transition_duration": 0.5})
        self._selection = identifier
        self._notify()

    @QtCore.Slot(float)
    def addTitle(self, position):
        if self._locked("title"):
            return
        identifier = uuid.uuid4().hex
        self._data["titles"].append({"id": identifier, "text": "Title", "start": max(0, position), "end": max(0, position) + 3,
            "font": "Arial", "size": 48, "bold": True, "color": "#ffffff", "alignment": 2, "x": 0.5, "y": 0.85, "opacity": 1, "background": False})
        self._selection = identifier
        self._notify()

    @QtCore.Slot(float)
    def split(self, position):
        if self._locked("video"):
            return
        start = 0.0
        clips = self._data["timeline"]["clips"]
        for index, clip in enumerate(clips):
            duration = clip["out_point"] - clip["in_point"]
            local = position - start
            if 0.001 < local < duration - 0.001:
                right = {**copy.deepcopy(clip), "id": uuid.uuid4().hex, "in_point": clip["in_point"] + local}
                clip["out_point"] = right["in_point"]
                clip["transition_to_next"] = "none"
                if clip["media_type"] == "image":
                    right.update(in_point=0, out_point=duration-local, still_duration=duration-local)
                    clip.update(in_point=0, out_point=local, still_duration=local)
                clips.insert(index + 1, right)
                self._selection = right["id"]
                self._notify()
                return
            overlap = min(clip.get("transition_duration", 0.5), (clips[index+1]["out_point"] - clips[index+1]["in_point"]) / 2, 5) if index+1 < len(clips) and clip.get("transition_to_next") != "none" else 0
            start += duration - overlap

    @QtCore.Slot(str)
    def removeMedia(self, identifier):
        self._data["media"] = [m for m in self._data["media"] if m["id"] != identifier]
        self._notify()  # Referenced clips keep their source paths.

    @QtCore.Slot(str, str)
    def renameMedia(self, identifier, name):
        for item in self._data["media"]:
            if item["id"] == identifier and name.strip():
                item["name"] = name.strip()
        self._notify()

    @QtCore.Slot(str, str)
    def relink(self, old, new):
        if not Path(new).is_file():
            return
        new = str(Path(new).resolve())
        for item in self._data["media"]:
            if item["path"] == old:
                item["path"] = new
        for collection, key in ((self._data["timeline"]["clips"], "source_path"), (self._data["timeline"]["audio_tracks"], "audio_path")):
            for item in collection:
                if item[key] == old:
                    item[key] = new
        self._notify()

    @QtCore.Slot(str)
    def locate(self, old):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Locate " + Path(old).name)
        if path:
            self.relink(old, path)

    @QtCore.Slot(str)
    def reveal(self, path):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(Path(path).parent)))

    @QtCore.Slot(str, result=str)
    def fileUrl(self, path):
        return QtCore.QUrl.fromLocalFile(path).toString() if path else ""

    def shutdown(self):
        if self._closed:
            return
        self._timer.stop()
        self._importer.shutdown()
        self._executor.shutdown(wait=True, cancel_futures=False)
        self._closed = True
