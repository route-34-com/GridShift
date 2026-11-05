"""Today's machine plan, taken from the run that was made for today."""

from datetime import datetime

import pandas as pd

from backend.forecast.horizon import day_bounds
from backend.store import Store


def _clip(block: dict, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Return the part of a run block inside the day, keeping its whole-block price and reason."""
    first, last = max(pd.Timestamp(block["start"]), start), min(pd.Timestamp(block["end"]), end)
    hours = (last - first) / pd.Timedelta(hours=1)
    return {
        **block,
        "start": first.isoformat(),
        "end": last.isoformat(),
        "hours": round(hours, 2),
        "energy_kwh": round(block["energy_kwh"] * hours / block["hours"], 1),
    }


def today_plan(store: Store, now: datetime) -> dict | None:
    """Return today's steps and run blocks, or None when no stored run covers today."""
    start, end = day_bounds(now)
    run = store.plan_for_day(start.isoformat())
    if run is None:
        return None
    steps = [row for row in run["hourly"] if start <= pd.Timestamp(row["ts"]) < end]
    if not steps:
        return None
    blocks = [_clip(b, start, end) for b in run["blocks"] if pd.Timestamp(b["start"]) < end and pd.Timestamp(b["end"]) > start]
    return {"run": {"id": run["id"], "created_at": run["created_at"], "machines": run["machines"]}, "hourly": steps, "blocks": blocks}
