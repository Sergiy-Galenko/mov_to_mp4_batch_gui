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
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

MAX_WORKERS = int(os.environ.get("ARCHIVE_MAX_WORKERS", "4"))
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

service = ArchiveService()

# -----------------------------------------------------------------------------
# Job Store (In-Memory with thread safety)
# -----------------------------------------------------------------------------
class JobState:
    def __init__(self, job_id: str, op_type: str) -> None:
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

jobs: dict[str, JobState] = {}

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
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
        "active_jobs": sum(1 for j in jobs.values() if j.status == "running"),
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
def _run_compression(job: JobState, source_paths: list[str], output_path: str, format_str: str, preset: str, password: str, split_mb: int) -> None:
    job.status = "running"

    def on_progress(pct: float, f_done: int, f_total: int, b_done: int, b_total: int, curr_f: str, elapsed: float) -> None:
        job.progress = pct
        job.files_done = f_done
        job.files_total = f_total
        job.bytes_done = b_done
        job.bytes_total = b_total
        job.current_file = curr_f
        job.elapsed_seconds = elapsed
        if elapsed > 0.5 and b_done > 0:
            speed = b_done / elapsed
            job.speed_bps = speed
            rem_bytes = max(0, b_total - b_done)
            job.eta_seconds = (rem_bytes / speed) if speed > 0 else 0.0

    try:
        res = service.create_archive(
            sources=source_paths,
            output_path=output_path,
            archive_format=format_str,
            preset=preset,
            password=password,
            split_size_mb=split_mb,
            cancel_requested=lambda: job.cancel_requested,
            progress_callback=on_progress,
        )
        if job.cancel_requested:
            job.status = "cancelled"
            job.error = "Cancelled by user"
        elif res.success:
            job.status = "completed"
            job.output_path = res.output_path
            job.result = {
                "outputPath": res.output_path,
                "originalSize": res.original_size,
                "archiveSize": res.archive_size,
                "savedPercent": res.saved_percent,
                "isLarger": res.is_larger,
                "filesCount": res.files_count,
                "elapsedSeconds": res.elapsed_seconds,
            }
        else:
            job.status = "failed"
            job.error = res.error_message or "Unknown compression error"
    except Exception as e:
        logger.exception("Compression job %s failed", job.job_id)
        job.status = "failed"
        job.error = str(e)

@app.post("/api/v1/compress")
async def start_compression(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    format: str = Form("zip"),
    preset: str = Form("balanced"),
    archive_name: str = Form("archive"),
    password: str = Form(""),
    split_size_mb: int = Form(0),
) -> dict[str, str]:
    """Upload files and start an asynchronous compression task."""
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for uploaded in files:
        target = job_dir / (uploaded.filename or "file")
        with open(target, "wb") as buffer:
            shutil.copyfileobj(uploaded.file, buffer)
        saved_paths.append(str(target))

    ext = f".{format.lower().lstrip('.')}"
    if not archive_name.endswith(ext):
        safe_name = f"{archive_name}{ext}"
    else:
        safe_name = archive_name

    out_file = str(OUTPUT_DIR / f"{job_id}_{safe_name}")

    job = JobState(job_id, "compress")
    jobs[job_id] = job

    executor.submit(
        _run_compression,
        job,
        saved_paths,
        out_file,
        format,
        preset,
        password,
        split_size_mb,
    )

    return {"job_id": job_id, "status": "pending"}

# -----------------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------------
def _run_extraction(job: JobState, archive_path: str, dest_dir: str, password: str, overwrite: str) -> None:
    job.status = "running"

    def on_progress(pct: float, f_done: int, f_total: int, b_done: int, b_total: int, curr_f: str, elapsed: float) -> None:
        job.progress = pct
        job.files_done = f_done
        job.files_total = f_total
        job.bytes_done = b_done
        job.bytes_total = b_total
        job.current_file = curr_f
        job.elapsed_seconds = elapsed

    try:
        res = service.extract_archive(
            archive_path=archive_path,
            destination_dir=dest_dir,
            password=password,
            overwrite_mode=overwrite,
            cancel_requested=lambda: job.cancel_requested,
            progress_callback=on_progress,
        )
        if job.cancel_requested:
            job.status = "cancelled"
            job.error = "Cancelled by user"
        elif res.success:
            job.status = "completed"
            job.result = {
                "destination": res.destination,
                "filesExtracted": res.files_extracted,
                "bytesExtracted": res.bytes_extracted,
                "elapsedSeconds": res.elapsed_seconds,
            }
        else:
            job.status = "failed"
            job.error = res.error_message or "Extraction error"
    except Exception as e:
        logger.exception("Extraction job %s failed", job.job_id)
        job.status = "failed"
        job.error = str(e)

@app.post("/api/v1/extract")
async def start_extraction(
    archive: UploadFile = File(...),
    password: str = Form(""),
    overwrite: str = Form("replace"),
) -> dict[str, str]:
    """Upload an archive and extract it in the background."""
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    arc_path = job_dir / (archive.filename or "archive.bin")
    with open(arc_path, "wb") as buffer:
        shutil.copyfileobj(archive.file, buffer)

    dest_dir = OUTPUT_DIR / f"{job_id}_extracted"
    dest_dir.mkdir(parents=True, exist_ok=True)

    job = JobState(job_id, "extract")
    jobs[job_id] = job

    executor.submit(
        _run_extraction,
        job,
        str(arc_path),
        str(dest_dir),
        password,
        overwrite,
    )

    return {"job_id": job_id, "status": "pending"}

# -----------------------------------------------------------------------------
# Inspect Archive (Without extraction)
# -----------------------------------------------------------------------------
@app.post("/api/v1/inspect")
async def inspect_archive(
    archive: UploadFile = File(...),
    password: str = Form(""),
) -> list[dict[str, Any]]:
    """View archive contents (file tree, dates, uncompressed and compressed sizes)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{archive.filename}") as tmp:
        shutil.copyfileobj(archive.file, tmp)
        tmp_path = tmp.name

    try:
        entries = service.list_archive(tmp_path, password=password)
        return [asdict(e) for e in entries]
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

# -----------------------------------------------------------------------------
# Job Status & Download & Cancel
# -----------------------------------------------------------------------------
@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> dict[str, Any]:
    """Poll job status, progress, speed, and ETA."""
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
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.cancel_requested = True
    return {"job_id": job_id, "status": "cancelling"}

@app.get("/api/v1/jobs/{job_id}/download")
def download_job_output(job_id: str):
    """Download the resulting archive once completed."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed (current status: {job.status})")

    p = Path(job.output_path)
    if not p.exists():
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
            await websocket.send_json({
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
                "result": job.result if job.status == "completed" else {},
                "error": job.error if job.status in {"failed", "cancelled"} else "",
            })

            if job.status in {"completed", "failed", "cancelled"}:
                break

            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        logger.info("Client disconnected from job %s", job_id)
