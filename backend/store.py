"""Persistence for planning runs and cached weather."""

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from backend.database import connect, init_db


class Store:
    """Read and write runs and cached weather for one data set in the SQLite database."""

    def __init__(self, path: Path, dataset: str = "live", init: bool = True):
        self.path = path
        self.dataset = dataset
        if init:
            init_db(path)

    def scoped(self, dataset: str) -> "Store":
        """Return a store for another data set in the same database."""
        return Store(self.path, dataset, init=False)

    def get_setting(self, key: str, default: str) -> str:
        """Return an app-wide setting."""
        with connect(self.path) as db:
            row = db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default


    def save_run(self, payload: dict) -> int:
        """Insert a run and return its id."""
        with connect(self.path) as db:
            cursor = db.execute(
                "INSERT INTO runs (created_at, horizon_start, status, payload, dataset) VALUES (?, ?, ?, ?, ?)",
                (payload["created_at"], payload["horizon_start"], payload["status"], "{}", self.dataset),
            )
            run_id = cursor.lastrowid
            payload["id"] = run_id
            db.execute("UPDATE runs SET payload = ? WHERE id = ?", (json.dumps(payload), run_id))
        return run_id

    def update_run(self, payload: dict) -> None:
        """Overwrite a stored run payload."""
        with connect(self.path) as db:
            db.execute("UPDATE runs SET payload = ?, status = ? WHERE id = ?", (json.dumps(payload), payload["status"], payload["id"]))

    def get_run(self, run_id: int) -> dict | None:
        """Return one run payload by id."""
        with connect(self.path) as db:
            row = db.execute("SELECT payload FROM runs WHERE id = ? AND dataset = ?", (run_id, self.dataset)).fetchone()
        return json.loads(row[0]) if row else None

    def latest_run(self, successful: bool = False) -> dict | None:
        """Return the newest run payload, optionally skipping failed runs."""
        query = "SELECT payload FROM runs WHERE dataset = ? {} ORDER BY id DESC LIMIT 1".format("AND status != 'failed'" if successful else "")
        with connect(self.path) as db:
            row = db.execute(query, (self.dataset,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_runs(self, limit: int = 20) -> list[dict]:
        """Return recent run headers, newest first."""
        with connect(self.path) as db:
            found = db.execute("SELECT id, created_at, horizon_start, status FROM runs WHERE dataset = ? ORDER BY id DESC LIMIT ?", (self.dataset, limit)).fetchall()
        return [dict(r) for r in found]

    def save_weather(self, kind: str, frame: pd.DataFrame) -> None:
        """Cache a weather frame for fallback use."""
        stamp = datetime.now(timezone.utc).isoformat()
        with connect(self.path) as db:
            db.execute(
                "INSERT OR REPLACE INTO weather_cache (kind, fetched_at, payload) VALUES (?, ?, ?)",
                (self._weather_key(kind), stamp, frame.to_json(orient="split", date_format="iso")),
            )

    def load_weather(self, kind: str) -> pd.DataFrame | None:
        """Return the cached weather frame, if any."""
        with connect(self.path) as db:
            row = db.execute("SELECT payload FROM weather_cache WHERE kind = ?", (self._weather_key(kind),)).fetchone()
        if not row:
            return None
        frame = pd.read_json(io.StringIO(row[0]), orient="split")
        frame.index = pd.to_datetime(frame.index, utc=True)
        return frame

    def _weather_key(self, kind: str) -> str:
        # Sites differ by data set, so each keeps its own fallback forecast; live keeps the original keys.
        return kind if self.dataset == "live" else f"{self.dataset}:{kind}"
