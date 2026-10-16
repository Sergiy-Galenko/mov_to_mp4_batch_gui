"""Durable task identities and publication checkpoints; recovery never trusts a path alone."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from app.models import TaskStatus
from app.paths import APP_DATA_DIR
from services.cache_manager import source_fingerprint
from utils.sqlite_store import database

TERMINAL = {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}


class TaskJournal:
    def __init__(self, path: Path = APP_DATA_DIR / "tasks.sqlite3"):
        self.path = path
        with database(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, source TEXT NOT NULL, status TEXT NOT NULL, "
                "fingerprint TEXT, settings TEXT NOT NULL, output TEXT, published TEXT, message TEXT NOT NULL, updated REAL NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL, time REAL NOT NULL)"
            )

    def prepare(self, task, settings):
        self.prepare_many([(task, settings)])

    def prepare_many(self, tasks):
        rows = []
        for task, settings in tasks:
            try:
                fingerprint = json.dumps(source_fingerprint(task.path), sort_keys=True)
            except OSError:
                fingerprint = None
            rows.append(
                (
                    task.task_id,
                    str(task.path),
                    TaskStatus.QUEUED,
                    fingerprint,
                    json.dumps(asdict(settings), sort_keys=True),
                    None,
                    None,
                    "",
                    time.time(),
                )
            )
        with database(self.path) as db:
            db.executemany("INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?,?,?)", rows)
            db.execute(
                "DELETE FROM tasks WHERE id NOT IN (SELECT id FROM tasks ORDER BY updated DESC LIMIT 10000) AND status IN ('success','failed','skipped','cancelled')"
            )

    def plan_output(self, task_id: str, output: Path):
        with database(self.path) as db:
            db.execute("UPDATE tasks SET output=?, updated=? WHERE id=?", (str(output), time.time(), task_id))

    def transition(self, task_id: str, status: str, message: str = "", output: str = ""):
        if status not in {TaskStatus.ANALYZING, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.PAUSED, *TERMINAL}:
            raise ValueError("Invalid journal status")
        published = None
        if status == TaskStatus.SUCCESS and output:
            with database(self.path) as db:
                row = db.execute("SELECT output FROM tasks WHERE id=?", (task_id,)).fetchone()
            paths = [output] if row and row["output"] == output else output.split(";")
            try:
                published = json.dumps([source_fingerprint(Path(value.strip())) for value in paths if value.strip()], sort_keys=True)
            except OSError:
                status, message = TaskStatus.FAILED, "Published output is missing"
        with database(self.path) as db:
            db.execute(
                "UPDATE tasks SET status=?,message=?,output=COALESCE(NULLIF(?,''),output),published=COALESCE(?,published),updated=? WHERE id=?",
                (status, message, output, published, time.time(), task_id),
            )
            db.execute("INSERT INTO events(task_id,status,message,time) VALUES (?,?,?,?)", (task_id, status, message, time.time()))
            db.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 2000)")

    def publication(self, task_id: str, output: Path):
        with database(self.path) as db:
            row = db.execute("SELECT output,settings FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row or row["output"] != str(output):
                return
            settings = json.loads(row["settings"])
            if settings.get("merge") or settings.get("split_chapters"):
                return
            fingerprint = json.dumps([source_fingerprint(output)], sort_keys=True)
            db.execute("UPDATE tasks SET published=?,updated=? WHERE id=?", (fingerprint, time.time(), task_id))

    def recover_items(self, items):
        with database(self.path) as db:
            records = {row["id"]: dict(row) for row in db.execute("SELECT * FROM tasks")}
        for item in items:
            row = records.get(item.task_id)
            if row is None:
                continue
            try:
                same_source = json.loads(row["fingerprint"] or "null") == source_fingerprint(item.path)
                outputs = json.loads(row["published"] or "[]")
                valid_outputs = bool(outputs) and all(
                    source_fingerprint(Path(output["path"])) == output and output["size"] > 0 for output in outputs
                )
            except (OSError, ValueError, TypeError, KeyError):
                same_source, valid_outputs = False, False
            if row["status"] == TaskStatus.SUCCESS and valid_outputs and (same_source or not item.path.exists()):
                item.status, item.last_output, item.progress = TaskStatus.SUCCESS, row["output"] or "", 1.0
            elif row["status"] not in TERMINAL and valid_outputs and same_source:
                settings = json.loads(row["settings"])
                postprocess = any(settings.get(key) for key in ("cloud_upload_enabled", "smart_integrity_check", "secure_delete_original"))
                postprocess = (
                    postprocess
                    or settings.get("checksum_algorithm", "none") != "none"
                    or settings.get("smart_quality_metric", "none") != "none"
                )
                item.last_output = row["output"] or ""
                item.status = TaskStatus.FAILED if postprocess else TaskStatus.SUCCESS
                item.last_error = "Result preserved; post-processing was interrupted" if postprocess else ""
                item.progress = 1.0
            elif row["status"] not in TERMINAL or row["status"] == TaskStatus.SUCCESS:
                item.status, item.progress, item.eta_text, item.speed_text = TaskStatus.QUEUED, 0.0, "", ""
                item.elapsed_seconds = 0.0
                item.last_error = (
                    "Source or output changed; task needs to run again" if not same_source or outputs else "Interrupted task recovered"
                )
            else:
                item.status, item.last_error = row["status"], row["message"]
        return items

    def recent_events(self, limit=50):
        with database(self.path) as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT task_id,status,message,time FROM events ORDER BY id DESC LIMIT ?", (max(0, min(2000, limit)),)
                )
            ]
