"""Universal Archive & Compression Service — Web API (FastAPI + WebSockets).

Provides cross-platform REST endpoints and real-time WebSocket progress
for archiving, extraction, and inspection without any GUI / Qt dependencies.
Can be deployed as a microservice on Linux, macOS, Windows, or Kubernetes.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from services.archive_service import ArchiveService

logger = logging.getLogger("archive_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
UPLOAD_DIR = Path(os.environ.get("ARCHIVE_UPLOAD_DIR", tempfile.gettempdir())) / "archive_api_uploads"
OUTPUT_DIR = Path(os.environ.get("ARCHIVE_OUTPUT_DIR", tempfile.gettempdir())) / "archive_api_outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_WORKERS = max(1, int(os.environ.get("ARCHIVE_MAX_WORKERS", "4")))
MAX_JOBS = max(1, int(os.environ.get("ARCHIVE_MAX_JOBS", "100")))
MAX_UPLOAD_BYTES = max(1, int(os.environ.get("ARCHIVE_MAX_UPLOAD_BYTES", str(1024**3))))
MAX_FILES = max(1, int(os.environ.get("ARCHIVE_MAX_FILES", "100")))
JOB_TTL_SECONDS = max(1, int(os.environ.get("ARCHIVE_JOB_TTL_SECONDS", "3600")))
CLEANUP_INTERVAL_SECONDS = max(1, int(os.environ.get("ARCHIVE_CLEANUP_INTERVAL_SECONDS", "60")))
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

service = ArchiveService()


# -----------------------------------------------------------------------------
# Job Store (In-Memory with thread safety)
# -----------------------------------------------------------------------------
class JobState:
    def __init__(self, job_id: str, op_type: str) -> None:
        self.finished_at: float | None = None
        self.job_id = job_id
        self.op_type = op_type
        self.status: str = "pending"  # pending, running, completed, failed, cancelled
        self.progress: float = 0.0
        self.files_done: int = 0
        self.files_total: int = 0
        self.bytes_done: int = 0
        self.bytes_total: int = 0
        self.current_file: str = ""
        self.speed_bps: float = 0.0
        self.eta_seconds: float = 0.0
        self.elapsed_seconds: float = 0.0
        self.output_path: str = ""
        self.result: dict[str, Any] = {}
        self.error: str = ""
        self.cancel_requested: bool = False
        self.websockets: list[WebSocket] = []

    def start(self) -> bool:
        with jobs_lock:
            if self.cancel_requested:
                self.finish(error="Cancelled by user")
                return False
            self.status = "running"
            return True

    def update_progress(self, pct: float, f_done: int, f_total: int, b_done: int, b_total: int, curr_f: str, elapsed: float) -> None:
        with jobs_lock:
            self.progress = pct
            self.files_done = f_done
            self.files_total = f_total
            self.bytes_done = b_done
            self.bytes_total = b_total
            self.current_file = curr_f
            self.elapsed_seconds = elapsed
            self.speed_bps = b_done / elapsed if elapsed > 0 else 0.0
            self.eta_seconds = max(0, b_total - b_done) / self.speed_bps if self.speed_bps else 0.0

    def finish(self, *, result: dict[str, Any] | None = None, error: str = "") -> None:
        with jobs_lock:
            if self.cancel_requested:
                self.error = "Cancelled by user"
                self.status = "cancelled"
            elif result is None:
                self.error = error
                self.status = "failed"
            else:
                self.result = result
                self.output_path = result.get("outputPath", "")
                self.status = "completed"
            self.eta_seconds = 0.0
            self.finished_at = time.monotonic()


jobs: dict[str, JobState] = {}
jobs_lock = threading.RLock()


def _job_paths(job_id: str) -> tuple[Path, Path]:
    return UPLOAD_DIR / job_id, OUTPUT_DIR / job_id


def _remove_job_files(job_id: str) -> None:
    for directory in _job_paths(job_id):
        shutil.rmtree(directory, ignore_errors=True)


def cleanup_jobs() -> None:
    now = time.monotonic()
    with jobs_lock:
        for job_id, job in list(jobs.items()):
            if job.finished_at is not None and now - job.finished_at >= JOB_TTL_SECONDS:
                _remove_job_files(job_id)
                del jobs[job_id]
        # Reclaim files left by a previous process, but never touch active jobs
        # or directories that do not belong to this API's UUID namespace.
        for root in (UPLOAD_DIR, OUTPUT_DIR):
            if not root.is_dir():
                continue
            for directory in root.iterdir():
                try:
                    identity = str(uuid.UUID(directory.name))
                    if identity != directory.name or identity in jobs or directory.is_symlink():
                        continue
                    if time.time() - directory.stat().st_mtime >= JOB_TTL_SECONDS:
                        shutil.rmtree(directory)
                except (ValueError, OSError):
                    continue


def _reserve_job(op_type: str) -> JobState:
    cleanup_jobs()
    with jobs_lock:
        if len(jobs) >= MAX_JOBS:
            raise HTTPException(status_code=429, detail="Job capacity reached; retry later")
        job = JobState(str(uuid.uuid4()), op_type)
        jobs[job.job_id] = job
        return job


def _discard_job(job: JobState) -> None:
    with jobs_lock:
        _remove_job_files(job.job_id)
        jobs.pop(job.job_id, None)


def _safe_name(value: str, fallback: str) -> str:
    # Handle both Windows and POSIX separators irrespective of the host OS.
    name = str(value or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if c.isprintable() and c not in "/\\:")[:160]
    return name if name not in {"", ".", ".."} else fallback


async def _save_upload(upload: UploadFile, directory: Path, used_bytes: int = 0) -> tuple[Path, int]:
    # UUID directory prevents collisions while preserving the original basename
    # and suffix needed by archive format detection.
    parent = directory / uuid.uuid4().hex
    parent.mkdir(parents=True)
    target = parent / _safe_name(upload.filename, "upload.bin")
    if not target.resolve().is_relative_to(directory.resolve()):
        raise HTTPException(status_code=400, detail="Invalid upload path")
    try:
        with target.open("xb") as destination:
            while chunk := await upload.read(1024 * 1024):
                used_bytes += len(chunk)
                if used_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Upload size limit exceeded")
                destination.write(chunk)
    finally:
        await upload.close()
    return target, used_bytes


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(cleanup_jobs)

    async def cleanup_loop():
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            await asyncio.to_thread(cleanup_jobs)

    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    lifespan=lifespan,
    title="Universal Archiver API",
    description="High-performance, cross-platform archiving and compression service with REST & WebSockets.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadTooLarge(Exception):
    pass


class UploadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Allow bounded multipart overhead in addition to the actual file budget.
        limit = MAX_UPLOAD_BYTES + MAX_FILES * 4096
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > limit:
            return await JSONResponse({"detail": "Upload size limit exceeded"}, status_code=413)(scope, receive, send)
        total = 0
        exceeded = False
        rejected = False

        async def bounded_receive():
            nonlocal total, exceeded
            message = await receive()
            total += len(message.get("body", b""))
            if total > limit:
                exceeded = True
                raise UploadTooLarge()
            return message

        async def limited_send(message):
            nonlocal rejected
            if exceeded:
                if not rejected:
                    rejected = True
                    await JSONResponse({"detail": "Upload size limit exceeded"}, status_code=413)(scope, receive, send)
                return
            await send(message)

        try:
            await self.app(scope, bounded_receive, limited_send)
        except UploadTooLarge:
            if not rejected:
                await JSONResponse({"detail": "Upload size limit exceeded"}, status_code=413)(scope, receive, send)


app.add_middleware(UploadLimitMiddleware)


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class FormatInfoResponse(BaseModel):
    id: str
    name: str
    extension: str
    can_create: bool
    can_extract: bool
    supports_encryption: bool
    supports_filename_encryption: bool
    supports_split: bool
    supports_solid: bool
    description: str
    recommendation: str


class PresetInfoResponse(BaseModel):
    id: str
    label: str
    description: str
    recommended: bool = False


class JobStatusResponse(BaseModel):
    job_id: str
    op_type: str
    status: str
    progress: float
    files_done: int
    files_total: int
    bytes_done: int
    bytes_total: int
    current_file: str
    speed_bps: float
    eta_seconds: float
    elapsed_seconds: float
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/health")
def health_check() -> dict[str, Any]:
    """Check service health and underlying tool capabilities."""
    return {
        "status": "healthy",
        "has_7z": service.has_7z,
        "has_rar": service.has_rar,
        "seven_zip_path": str(service._7z_path or ""),
        "rar_path": str(service._rar_path or ""),
        "max_workers": MAX_WORKERS,
        "active_jobs": sum(1 for j in list(jobs.values()) if j.status == "running"),
    }


@app.get("/api/v1/formats", response_model=list[FormatInfoResponse])
def get_formats() -> list[dict[str, Any]]:
    """List all supported formats with compression & encryption features."""
    formats = service.get_supported_formats()
    return [asdict(f) for f in formats]


@app.get("/api/v1/presets", response_model=list[PresetInfoResponse])
def get_presets() -> list[dict[str, Any]]:
    """List compression presets (Fast, Balanced, Maximum)."""
    return [
        {"id": "fast", "label": "Fast", "description": "Швидке стиснення, більший розмір файлу", "recommended": False},
        {"id": "balanced", "label": "Balanced", "description": "Рекомендований баланс швидкості та розміру", "recommended": True},
        {"id": "maximum", "label": "Maximum", "description": "Максимальне стиснення, займає більше часу", "recommended": False},
    ]


# -----------------------------------------------------------------------------
# Compression
# -----------------------------------------------------------------------------
def _run_compression(
    job: JobState, source_paths: list[str], output_path: str, format_str: str, preset: str, password: str, split_mb: int
) -> None:
    if not job.start():
        return
    try:
        res = service.create_archive(
            sources=source_paths,
            output_path=output_path,
            archive_format=format_str,
            preset=preset,
            password=password,
            split_size_mb=split_mb,
            cancel_requested=lambda: job.cancel_requested,
            progress_callback=job.update_progress,
        )
        if res.success:
            job.finish(
                result={
                    "outputPath": res.output_path,
                    "outputPaths": res.output_paths,
                    "originalSize": res.original_size,
                    "archiveSize": res.archive_size,
                    "savedPercent": res.saved_percent,
                    "isLarger": res.is_larger,
                    "filesCount": res.files_count,
                    "elapsedSeconds": res.elapsed_seconds,
                }
            )
        else:
            job.finish(error=res.error_message or "Unknown compression error")
    except Exception as e:
        logger.exception("Compression job %s failed", job.job_id)
        job.finish(error=str(e))


@app.post("/api/v1/compress")
async def start_compression(
    files: list[UploadFile] = File(...),
    format: str = Form("zip"),
    preset: str = Form("balanced"),
    archive_name: str = Form("archive"),
    password: str = Form(""),
    split_size_mb: int = Form(0),
) -> dict[str, str]:
    """Upload files and start an asynchronous compression task."""
    format = format.lower().lstrip(".")
    supported = {f.id for f in service.get_supported_formats() if f.can_create}
    if format not in supported or preset not in {"fast", "balanced", "maximum"}:
        raise HTTPException(status_code=400, detail="Unsupported archive format or preset")
    if split_size_mb < 0 or (split_size_mb and format not in {"7z", "rar"}):
        raise HTTPException(status_code=400, detail="Invalid split size or format")
    if not files or len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail="Invalid number of files")
    job = _reserve_job("compress")
    try:
        job_dir, output_dir = _job_paths(job.job_id)
        output_dir.mkdir(parents=True)
        saved_paths = []
        used_bytes = 0
        names: set[str] = set()
        for uploaded in files:
            name = _safe_name(uploaded.filename, "upload.bin")
            if name in names:
                raise HTTPException(status_code=400, detail="Duplicate upload filenames; rename files before uploading")
            names.add(name)
            target, used_bytes = await _save_upload(uploaded, job_dir, used_bytes)
            saved_paths.append(str(target))
        name = _safe_name(archive_name, "archive")
        ext = f".{format}"
        if not name.lower().endswith(ext):
            name += ext
        out_file = output_dir / name
        if not out_file.resolve().is_relative_to(output_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid output path")
        executor.submit(_run_compression, job, saved_paths, str(out_file), format, preset, password, split_size_mb)
    except BaseException:
        _discard_job(job)
        raise
    return {"job_id": job.job_id, "status": "pending"}


# -----------------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------------
def _run_extraction(job: JobState, archive_path: str, dest_dir: str, password: str, overwrite: str) -> None:
    if not job.start():
        return
    try:
        res = service.extract_archive(
            archive_path=archive_path,
            destination_dir=dest_dir,
            password=password,
            overwrite_mode=overwrite,
            cancel_requested=lambda: job.cancel_requested,
            progress_callback=job.update_progress,
        )
        if res.success:
            job.finish(
                result={
                    "destination": res.destination,
                    "filesExtracted": res.files_extracted,
                    "bytesExtracted": res.bytes_extracted,
                    "elapsedSeconds": res.elapsed_seconds,
                }
            )
        else:
            job.finish(error=res.error_message or "Extraction error")
    except Exception as e:
        logger.exception("Extraction job %s failed", job.job_id)
        job.finish(error=str(e))


@app.post("/api/v1/extract")
async def start_extraction(
    archive: UploadFile = File(...),
    password: str = Form(""),
    overwrite: str = Form("replace"),
) -> dict[str, str]:
    """Upload an archive and extract it in the background."""
    if overwrite not in {"replace", "skip", "keep_both"}:
        raise HTTPException(status_code=400, detail="Invalid overwrite mode")
    job = _reserve_job("extract")
    try:
        job_dir, output_dir = _job_paths(job.job_id)
        arc_path, _ = await _save_upload(archive, job_dir)
        dest_dir = output_dir / "extracted"
        dest_dir.mkdir(parents=True)
        executor.submit(_run_extraction, job, str(arc_path), str(dest_dir), password, overwrite)
    except BaseException:
        _discard_job(job)
        raise
    return {"job_id": job.job_id, "status": "pending"}


# -----------------------------------------------------------------------------
# Inspect Archive (Without extraction)
# -----------------------------------------------------------------------------
@app.post("/api/v1/inspect")
async def inspect_archive(
    archive: UploadFile = File(...),
    password: str = Form(""),
) -> list[dict[str, Any]]:
    """View archive contents (file tree, dates, uncompressed and compressed sizes)."""
    job = _reserve_job("inspect")
    try:
        tmp_path, _ = await _save_upload(archive, _job_paths(job.job_id)[0])
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(executor, lambda: service.list_archive(str(tmp_path), password=password))
        try:
            entries = await asyncio.shield(future)
        except asyncio.CancelledError:
            # Keep the reservation/files alive until the thread releases them.
            await future
            raise
        return [asdict(e) for e in entries]
    finally:
        _discard_job(job)


# -----------------------------------------------------------------------------
# Job Status & Download & Cancel
# -----------------------------------------------------------------------------
@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> dict[str, Any]:
    """Poll job status, progress, speed, and ETA."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "job_id": job.job_id,
            "op_type": job.op_type,
            "status": job.status,
            "progress": job.progress,
            "files_done": job.files_done,
            "files_total": job.files_total,
            "bytes_done": job.bytes_done,
            "bytes_total": job.bytes_total,
            "current_file": job.current_file,
            "speed_bps": job.speed_bps,
            "eta_seconds": job.eta_seconds,
            "elapsed_seconds": job.elapsed_seconds,
            "result": job.result,
            "error": job.error,
        }


@app.post("/api/v1/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, str]:
    """Request early cancellation of an active job."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status in {"completed", "failed", "cancelled"}:
            return {"job_id": job_id, "status": job.status}
        job.cancel_requested = True
        return {"job_id": job_id, "status": "cancelling"}


@app.get("/api/v1/jobs/{job_id}/download")
def download_job_output(job_id: str, part: int = 0):
    """Download the resulting archive once completed."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed (current status: {job.status})")

    if job.op_type != "compress":
        raise HTTPException(status_code=400, detail="Downloads are only available for compression jobs")
    paths = job.result.get("outputPaths") or ([job.output_path] if job.output_path else [])
    if part < 0 or part >= len(paths):
        raise HTTPException(status_code=404, detail="Output part not found")
    p = Path(paths[part])
    if not p.resolve().is_relative_to(_job_paths(job_id)[1].resolve()) or not p.is_file():
        raise HTTPException(status_code=404, detail="Output file not found on disk")

    return FileResponse(path=str(p), filename=p.name, media_type="application/octet-stream")


# -----------------------------------------------------------------------------
# Real-Time WebSocket Endpoint
# -----------------------------------------------------------------------------
@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str) -> None:
    """Stream live progress updates (10Hz) to connected WebSocket clients."""
    await websocket.accept()
    job = jobs.get(job_id)
    if not job:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    try:
        while True:
            with jobs_lock:
                snapshot = {
                    "job_id": job.job_id,
                    "status": job.status,
                    "progress": round(job.progress, 1),
                    "files_done": job.files_done,
                    "files_total": job.files_total,
                    "bytes_done": job.bytes_done,
                    "bytes_total": job.bytes_total,
                    "current_file": job.current_file,
                    "speed_bps": round(job.speed_bps, 0),
                    "eta_seconds": round(job.eta_seconds, 1),
                    "elapsed_seconds": round(job.elapsed_seconds, 1),
                    "result": job.result,
                    "error": job.error,
                }
            await websocket.send_json(snapshot)
            if snapshot["status"] in {"completed", "failed", "cancelled"}:
                break

            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        logger.info("Client disconnected from job %s", job_id)
