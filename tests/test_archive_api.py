import asyncio
import io
import time
import zipfile
from concurrent.futures import Future
from unittest.mock import Mock

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("multipart")
from api import app as api
from fastapi.testclient import TestClient


class InlineExecutor:
    def submit(self, work, *args):
        future = Future()
        try:
            future.set_result(work(*args))
        except BaseException as exc:
            future.set_exception(exc)
        return future


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(api, "jobs", {})
    monkeypatch.setattr(api, "executor", InlineExecutor())
    with TestClient(api.app) as client:
        yield client


@pytest.mark.parametrize("filename", ["../../escape.txt", "/absolute.txt", r"C:\temp\escape.txt"])
def test_compression_paths_are_confined_and_download_works(client, filename):
    response = client.post("/api/v1/compress", files={"files": (filename, b"hello")}, data={"archive_name": "../../out"})
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    job = api.jobs[job_id]
    assert job.status == "completed", job.error
    assert all(p.is_relative_to(api.UPLOAD_DIR) for p in api.UPLOAD_DIR.rglob("*"))
    output = client.get(f"/api/v1/jobs/{job_id}/download")
    assert output.status_code == 200
    with zipfile.ZipFile(io.BytesIO(output.content)) as archive:
        assert len(archive.namelist()) == 1
        assert archive.read(archive.namelist()[0]) == b"hello"


def test_extraction_paths_are_confined_and_download_is_rejected(client):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("hello.txt", "hello")
    response = client.post("/api/v1/extract", files={"archive": ("../../upload.zip", data.getvalue())})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert api.jobs[job_id].status == "completed"
    assert (api.OUTPUT_DIR / job_id / "extracted" / "hello.txt").read_text() == "hello"
    assert client.get(f"/api/v1/jobs/{job_id}/download").status_code == 400


def test_upload_limit_discards_reservation_and_files(client, monkeypatch):
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 3)
    response = client.post("/api/v1/compress", files={"files": ("test.txt", b"too much")})
    assert response.status_code == 413
    assert api.jobs == {}
    assert not list(api.UPLOAD_DIR.rglob("*"))
    assert not list(api.OUTPUT_DIR.rglob("*"))


def test_capacity_limit_rejects_before_upload(client, monkeypatch):
    monkeypatch.setattr(api, "MAX_JOBS", 1)
    job = api._reserve_job("compress")
    response = client.post("/api/v1/compress", files={"files": ("test.txt", b"hello")})
    assert response.status_code == 429
    assert list(api.jobs) == [job.job_id]


def test_cleanup_expires_finished_jobs_but_preserves_active_jobs(client):
    old = api._reserve_job("compress")
    active = api._reserve_job("compress")
    for job in (old, active):
        for path in api._job_paths(job.job_id):
            path.mkdir(parents=True)
            (path / "test.txt").write_text("data")
    old.status = "completed"
    old.finished_at = time.monotonic() - api.JOB_TTL_SECONDS - 1
    api.cleanup_jobs()
    assert old.job_id not in api.jobs
    assert not any(p.exists() for p in api._job_paths(old.job_id))
    assert active.job_id in api.jobs
    assert all(p.exists() for p in api._job_paths(active.job_id))


def test_submission_failure_cleans_uploads(client, monkeypatch):
    monkeypatch.setattr(api.executor, "submit", Mock(side_effect=RuntimeError("shutdown")))
    with pytest.raises(RuntimeError, match="shutdown"):
        client.post("/api/v1/compress", files={"files": ("test.txt", b"hello")})
    assert api.jobs == {}
    assert not list(api.UPLOAD_DIR.rglob("*"))


def test_download_rejects_directory_and_missing_path(client):
    job = api._reserve_job("compress")
    job.status = "completed"
    assert client.get(f"/api/v1/jobs/{job.job_id}/download").status_code == 404
    directory = api._job_paths(job.job_id)[1]
    directory.mkdir(parents=True)
    job.output_path = str(directory)
    assert client.get(f"/api/v1/jobs/{job.job_id}/download").status_code == 404


def test_download_selects_volume(client):
    job = api._reserve_job("compress")
    directory = api._job_paths(job.job_id)[1]
    directory.mkdir(parents=True)
    paths = [directory / "archive.7z.001", directory / "archive.7z.002"]
    for i, path in enumerate(paths):
        path.write_bytes(bytes([i]))
    job.result = {"outputPaths": [str(p) for p in paths]}
    job.status = "completed"
    assert client.get(f"/api/v1/jobs/{job.job_id}/download?part=1").content == b"\x01"
    assert client.get(f"/api/v1/jobs/{job.job_id}/download?part=2").status_code == 404


def test_request_limit_without_content_length(client, monkeypatch):
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 2)
    monkeypatch.setattr(api, "MAX_FILES", 1)

    async def request():
        messages = iter([{"type": "http.request", "body": b"x" * 5000, "more_body": False}])
        sent = []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        async def inner(scope, receive, send):
            await receive()

        await api.UploadLimitMiddleware(inner)({"type": "http", "headers": []}, receive, send)
        assert sent[0]["status"] == 413

    asyncio.run(request())


def test_multipart_stream_without_content_length_returns_413(client, monkeypatch):
    import httpx

    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 2)
    monkeypatch.setattr(api, "MAX_FILES", 1)

    async def request():
        async def body():
            yield b'--boundary\r\nContent-Disposition: form-data; name="files"; filename="a.txt"\r\n\r\n'
            yield b"x" * 5000
            yield b"\r\n--boundary--\r\n"

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test") as http:
            response = await http.post(
                "/api/v1/compress", content=body(), headers={"Content-Type": "multipart/form-data; boundary=boundary"}
            )
            assert response.status_code == 413
        assert api.jobs == {}

    asyncio.run(request())


def test_cleanup_reclaims_orphans_after_restart(client):
    import os
    import uuid

    identity = str(uuid.uuid4())
    for root in (api.UPLOAD_DIR, api.OUTPUT_DIR):
        directory = root / identity
        directory.mkdir(parents=True)
        (directory / "leftover").write_text("data")
        old = time.time() - api.JOB_TTL_SECONDS - 1
        os.utime(directory, (old, old))
    unrelated = api.OUTPUT_DIR / "unrelated"
    unrelated.mkdir()
    api.cleanup_jobs()
    assert not (api.UPLOAD_DIR / identity).exists()
    assert not (api.OUTPUT_DIR / identity).exists()
    assert unrelated.is_dir()


def test_duplicate_names_are_rejected_without_leaving_files(client):
    response = client.post("/api/v1/compress", files=[("files", ("same.txt", b"first")), ("files", ("same.txt", b"second"))])
    assert response.status_code == 400
    assert api.jobs == {}
    assert not list(api.UPLOAD_DIR.rglob("*"))


def test_inspect_cleans_up_files_and_reservation(client):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("hello.txt", "hello")
    response = client.post("/api/v1/inspect", files={"archive": ("../../upload.zip", data.getvalue())})
    assert response.status_code == 200, response.text
    assert api.jobs == {}
    assert not list(api.UPLOAD_DIR.rglob("*"))
