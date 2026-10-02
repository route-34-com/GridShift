"""SQLite connection handling and schema for every GridShift table."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

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
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    user_id INTEGER,
    user_email TEXT,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'success',
    entity TEXT,
    entity_id TEXT,
    summary TEXT,
    detail TEXT,
    ip TEXT,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS audit_at ON audit_log(at);
CREATE INDEX IF NOT EXISTS audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS audit_action ON audit_log(action);
"""


def now_iso() -> str:
    """Return the current UTC time as ISO text."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def iso(moment: datetime) -> str:
    """Return a datetime as UTC ISO text."""
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def init_db(path: Path) -> None:
    """Create the database file and every table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(SCHEMA)
    finally:
        db.close()


@contextmanager
def connect(path: Path):
    """Yield a connection that commits on success and rolls back on error."""
    db = sqlite3.connect(path, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("BEGIN")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException as exc:
        db.execute("COMMIT" if getattr(exc, "keeps_writes", False) else "ROLLBACK")
        raise
    finally:
        db.close()


def one(db: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    """Return the first row as a dict, or None."""
    row = db.execute(sql, params).fetchone()
    return dict(row) if row else None


def rows(db: sqlite3.Connection, sql: str, params: tuple | list = ()) -> list[dict]:
    """Return every row as a dict."""
    return [dict(r) for r in db.execute(sql, params).fetchall()]


def insert(db: sqlite3.Connection, table: str, values: dict) -> int:
    """Insert a row and return its id."""
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    return db.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values())).lastrowid
