"""Switching between the built-in sample data and the company's own data."""

import sqlite3
from dataclasses import dataclass

from backend.settings import Settings
from backend.store import Store

SAMPLE, LIVE = "sample", "live"
KEY = "dataset"


@dataclass(frozen=True)
class DataSet:
    """The data set in use, with settings and store pointed at it."""

    name: str
    settings: Settings
    store: Store


def active_name(settings: Settings, store: Store) -> str:
    """Return the data set in use; sample data is on by default when it is installed."""
    if settings.sample_dir is None:
        return LIVE
    return store.get_setting(KEY, SAMPLE)


def resolve(settings: Settings, store: Store, name: str | None = None) -> DataSet:
    """Return settings and store for a data set (the active one by default)."""
    name = name or active_name(settings, store)
    if name == SAMPLE and settings.sample_dir is not None:
        return DataSet(SAMPLE, settings.for_data(settings.sample_dir), store.scoped(SAMPLE))
    return DataSet(LIVE, settings, store.scoped(LIVE))


def choose(db: sqlite3.Connection, name: str) -> None:
    """Make a data set the active one for everyone, including the daily run, inside the caller's transaction."""
    db.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (KEY, name))


def ready(settings: Settings) -> bool:
    """Return whether a data folder has everything a plan needs."""
    return settings.site_path.exists() and settings.machines_path.exists() and settings.demand_path.exists()


def describe(settings: Settings, store: Store, active: str | None = None) -> dict:
    """Return which data set is on and whether each one has site data."""
    def info(name: str) -> dict:
        return {"available": ready(resolve(settings, store, name).settings)}

    return {
        "active": active or active_name(settings, store),
        "switchable": settings.sample_dir is not None,
        SAMPLE: info(SAMPLE) if settings.sample_dir is not None else {"available": False},
        LIVE: info(LIVE),
    }
