"""Short-lived SQLite transactions shared safely across worker threads."""

import sqlite3
from contextlib import contextmanager, suppress
from pathlib import Path


@contextmanager
def database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    with suppress(OSError):
        path.chmod(0o600)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=15000")
    connection.execute("PRAGMA journal_mode=WAL")
    try:
        with connection:
            yield connection
    finally:
        connection.close()
