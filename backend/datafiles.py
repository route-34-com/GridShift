"""Keep the company's site files in the database when the host's disk doesn't last (Vercel)."""

import os
import threading
import uuid

from backend.database import connect, is_postgres, one, rows
from backend.settings import Settings

NAMES = ("site.yaml", "machines.yaml", "demand_history.csv", "meter_data.csv")

_restored: dict[str, str] = {}
_guard = threading.Lock()


def _key(settings: Settings) -> str:
    return f"files:{settings.data_dir}"


def _enabled(settings: Settings) -> bool:
    return is_postgres(settings.db_path)


def save(settings: Settings) -> None:
    """Copy the data folder's files into the database after a change."""
    if not _enabled(settings):
        return
    folder, key, version = str(settings.data_dir), _key(settings), uuid.uuid4().hex
    with connect(settings.db_path) as db:
        db.execute("DELETE FROM data_files WHERE dataset = ?", (folder,))
        for name in NAMES:
            path = settings.data_dir / name
            if path.exists():
                db.execute("INSERT INTO data_files (dataset, name, content) VALUES (?, ?, ?)", (folder, name, path.read_text(encoding="utf-8")))
        db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value", (key, version))
    with _guard:
        _restored[key] = version


def restore(settings: Settings) -> None:
    """Write the database copy of the data folder to disk when this server hasn't got the latest one."""
    if not _enabled(settings):
        return
    key = _key(settings)
    with connect(settings.db_path) as db:
        found = one(db, "SELECT value FROM app_settings WHERE key = ?", (key,))
        if found is None or _restored.get(key) == found["value"]:
            return
        files = {r["name"]: r["content"] for r in rows(db, "SELECT name, content FROM data_files WHERE dataset = ?", (str(settings.data_dir),))}
    with _guard:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            path = settings.data_dir / name
            if name in files:
                temp = path.with_suffix(".restore")
                temp.write_text(files[name], encoding="utf-8")
                os.replace(temp, path)
            elif path.exists():
                path.unlink()
        _restored[key] = found["value"]


def forget() -> None:
    """Drop what this server remembers restoring, so the next request reads the database again."""
    with _guard:
        _restored.clear()
