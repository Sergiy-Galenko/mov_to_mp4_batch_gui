# Archive API

Install `pip install -r api/requirements.txt`, then run
`uvicorn api.app:app --host 127.0.0.1 --port 8000` from the repository root.
Use a single server worker: the job registry is process-local.

Uploads and outputs are kept in server-generated job directories. Client filenames
are reduced to safe basenames; duplicate basenames in a compression request are
rejected. Successful single-file archives replace the destination atomically.
Split archives report every volume in `result.outputPaths` and their combined
size in `archiveSize`. Existing volume names are never overwritten.

`GET /api/v1/jobs/{job_id}/download?part=0` downloads the first output volume;
`part=1` selects the second, and so on. Extraction jobs expose their result through
job status; downloading an extraction job returns HTTP 400.

Configuration is read from environment variables at startup:

| Variable | Default | Meaning |
| --- | --- | --- |
| `ARCHIVE_UPLOAD_DIR` | System temporary directory | Parent of `archive_api_uploads` |
| `ARCHIVE_OUTPUT_DIR` | System temporary directory | Parent of `archive_api_outputs` |
| `ARCHIVE_MAX_WORKERS` | `4` | Concurrent processing threads |
| `ARCHIVE_MAX_JOBS` | `100` | Maximum retained jobs, including uploads, queued, running and finished jobs |
| `ARCHIVE_MAX_UPLOAD_BYTES` | `1073741824` | Combined uploaded file bytes per request (1 GiB) |
| `ARCHIVE_MAX_FILES` | `100` | Maximum files per compression request |
| `ARCHIVE_JOB_TTL_SECONDS` | `3600` | Retention after job completion |
| `ARCHIVE_CLEANUP_INTERVAL_SECONDS` | `60` | Periodic cleanup interval |

Requests exceeding job capacity return HTTP 429; oversized uploads return HTTP
413. The raw HTTP request body is also capped, allowing 4096 bytes of multipart
overhead per configured file. Cleanup removes expired job metadata and files,
preserves active jobs, and reclaims old UUID job directories after a restart.
A failed upload or submission releases its reservation and removes its files.

Run the API regression tests with `pytest -q tests/test_archive_api.py` after
installing `requirements-dev.txt`.
