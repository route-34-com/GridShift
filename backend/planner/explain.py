"""Group scheduled hours into run blocks and explain each placement."""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from backend.forecast.horizon import local_dates
from backend.planner.model import LOCAL_TZ, FlexibleMachine


@dataclass
class Block:
    """A continuous run of one machine."""

    machine_id: str
    machine_name: str
    start: str
    end: str
    hours: int
    energy_kwh: float
    avg_price: float
    renewable_share: float
    reason: str

    def to_dict(self) -> dict:
        """Return the block as a plain dict."""
        return asdict(self)


def _runs(values: np.ndarray) -> list[tuple[int, int]]:
    padded = np.concatenate([[0], values, [0]])
    edges = np.flatnonzero(np.diff(padded))
    return list(zip(edges[::2], edges[1::2]))


def _clock(stamp: pd.Timestamp) -> str:
    return stamp.tz_convert(LOCAL_TZ).strftime("%a %H:%M")


def _reason(avg_price: float, day_avg: float, share: float, cheapest: bool) -> str:
    if share >= 0.5:
        return f"{share:.0%} covered by on-site solar and wind"
    if avg_price < 0:
        return f"negative grid price (avg €{avg_price:.0f}/MWh), paid to consume"
    if day_avg > 0 and avg_price < day_avg * 0.9:
        return f"avg €{avg_price:.0f}/MWh vs day avg €{day_avg:.0f}/MWh"
    if cheapest:
        return f"cheapest feasible hours (avg €{avg_price:.0f}/MWh)"
    return f"needed to meet its quota or deadline (avg €{avg_price:.0f}/MWh)"


def explain_blocks(hourly: pd.DataFrame, schedule: pd.DataFrame, machines: list[FlexibleMachine]) -> list[Block]:
    """Return every run block with a one-line reason for its placement."""
    dates = local_dates(hourly.index)
    day_avg = hourly["price"].groupby(dates).transform("mean").to_numpy()
    total_load = (hourly["demand"] + hourly["flexible"] + hourly["charge"]).to_numpy()
    renewable = (hourly["solar"] + hourly["wind"]).to_numpy()
    share = np.divide(np.minimum(renewable, total_load), total_load, out=np.zeros_like(total_load), where=total_load > 0)
    price = hourly["price"].to_numpy()
    blocks = []
    for machine in machines:
        if machine.id not in schedule:
            continue
        for a, b in _runs(schedule[machine.id].to_numpy()):
            avg = float(price[a:b].mean())
            cover = float(share[a:b].mean())
            window = price[max(0, a - 6) : b + 6]
            cheapest = avg <= float(np.sort(window)[: b - a].mean()) + 1
            blocks.append(
                Block(
                    machine.id,
                    machine.name,
                    hourly.index[a].isoformat(),
                    (hourly.index[b - 1] + pd.Timedelta(hours=1)).isoformat(),
                    int(b - a),
                    round(machine.power_kw * (b - a), 1),
                    round(avg, 2),
                    round(cover, 3),
                    f"{_clock(hourly.index[a])}–{_clock(hourly.index[b - 1] + pd.Timedelta(hours=1))[4:]}: "
                    + _reason(avg, float(day_avg[a:b].mean()), cover, cheapest),
                )
            )
    return sorted(blocks, key=lambda x: (x.start, x.machine_id))
