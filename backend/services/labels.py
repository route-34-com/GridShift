"""Readable column titles and local times shared by every export format."""

from datetime import datetime

from backend.planner.model import LOCAL_TZ

UNITS = {"eur_mwh": "(€/MWh)", "eur": "(€)", "kwh": "(kWh)", "kw": "(kW)", "utc": "(UTC)", "local": "(local time)"}


def header(column: str) -> str:
    """Return a readable column title with its unit, e.g. planned_cost_eur -> Planned cost (€)."""
    for suffix, unit in UNITS.items():
        if column.endswith(f"_{suffix}"):
            return f"{column[: -len(suffix) - 1].replace('_', ' ').capitalize()} {unit}"
    return column.replace("_", " ").capitalize()


def local(stamp: str) -> str:
    """Return an ISO timestamp as Berlin local time text."""
    return datetime.fromisoformat(stamp).astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
