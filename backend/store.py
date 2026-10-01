"""SQLite persistence for planning runs and cached weather."""

import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    horizon_start TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weather_cache (
    kind TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


class Store:
    """Read and write runs in a SQLite file."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def save_run(self, payload: dict) -> int:
        """Insert a run and return its id."""
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO runs (created_at, horizon_start, status, payload) VALUES (?, ?, ?, ?)",
                (payload["created_at"], payload["horizon_start"], payload["status"], "{}"),
            )
            run_id = cursor.lastrowid
            payload["id"] = run_id
            db.execute("UPDATE runs SET payload = ? WHERE id = ?", (json.dumps(payload), run_id))
        return run_id

    def update_run(self, payload: dict) -> None:
        """Overwrite a stored run payload."""
        with self._connect() as db:
            db.execute("UPDATE runs SET payload = ?, status = ? WHERE id = ?", (json.dumps(payload), payload["status"], payload["id"]))

    def get_run(self, run_id: int) -> dict | None:
        """Return one run payload by id."""
        with self._connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id = ?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def latest_run(self, successful: bool = False) -> dict | None:
        """Return the newest run payload, optionally skipping failed runs."""
        query = "SELECT payload FROM runs {} ORDER BY id DESC LIMIT 1".format("WHERE status != 'failed'" if successful else "")
        with self._connect() as db:
            row = db.execute(query).fetchone()
        return json.loads(row[0]) if row else None

    def list_runs(self, limit: int = 20) -> list[dict]:
        """Return recent run headers, newest first."""
        with self._connect() as db:
            rows = db.execute("SELECT id, created_at, horizon_start, status FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(zip(("id", "created_at", "horizon_start", "status"), r)) for r in rows]

    def save_weather(self, kind: str, frame: pd.DataFrame) -> None:
        """Cache a weather frame for fallback use."""
        stamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO weather_cache (kind, fetched_at, payload) VALUES (?, ?, ?)",
                (kind, stamp, frame.to_json(orient="split", date_format="iso")),
            )

    def load_weather(self, kind: str) -> pd.DataFrame | None:
        """Return the cached weather frame, if any."""
        with self._connect() as db:
            row = db.execute("SELECT payload FROM weather_cache WHERE kind = ?", (kind,)).fetchone()
        if not row:
            return None
        frame = pd.read_json(io.StringIO(row[0]), orient="split")
        frame.index = pd.to_datetime(frame.index, utc=True)
        return frame
