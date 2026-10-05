"""Cost, renewable share and CO2 metrics for a plan."""

from dataclasses import asdict, dataclass

import pandas as pd

from backend.forecast.horizon import local_dates
from backend.planner.model import Site


@dataclass
class Metrics:
    """Headline numbers for one plan."""

    cost_eur: float
    peak_charge_eur: float
    total_cost_eur: float
    import_kwh: float
    export_kwh: float
    renewable_used_kwh: float
    renewable_share: float
    co2_avoided_kg: float
    peak_import_kw: float
    unmet_kwh: float

    def to_dict(self) -> dict:
        """Return the metrics as a plain dict."""
        return asdict(self)


def hourly_cost(hourly: pd.DataFrame, site: Site) -> pd.Series:
    """Return the net grid cost in EUR for each hour."""
    price = hourly["price"] / 1000 + site.grid.fee_eur_per_kwh
    return hourly["grid_import"] * price - hourly["grid_export"] * site.grid.export_price_eur_per_kwh


def peak_charge_eur(hourly: pd.DataFrame, site: Site) -> float:
    """Return the extra annual peak charge from importing above this year's record."""
    new_kw = max(0.0, float(hourly["grid_import"].max()) - site.grid.peak_so_far_kw)
    return new_kw * site.grid.peak_charge_eur_per_kw_year


def measure(hourly: pd.DataFrame, site: Site) -> Metrics:
    """Return headline metrics for a plan's hourly flows."""
    renewable = hourly["solar"] + hourly["wind"] - hourly["grid_export"] - hourly["curtail"]
    used = float(renewable.clip(lower=0).sum())
    imported = float(hourly["grid_import"].sum())
    total = used + imported
    cost = float(hourly_cost(hourly, site).sum())
    peak_charge = peak_charge_eur(hourly, site)
    return Metrics(
        cost_eur=round(cost, 2),
        peak_charge_eur=round(peak_charge, 2),
        total_cost_eur=round(cost + peak_charge, 2),
        import_kwh=round(imported, 1),
        export_kwh=round(float(hourly["grid_export"].sum()), 1),
        renewable_used_kwh=round(used, 1),
        renewable_share=round(used / total, 4) if total else 0.0,
        co2_avoided_kg=round(used * site.co2_kg_per_kwh, 1),
        peak_import_kw=round(float(hourly["grid_import"].max()), 1),
        unmet_kwh=round(float(hourly["unmet"].sum()), 1),
    )


def daily_costs(hourly: pd.DataFrame, site: Site) -> pd.Series:
    """Return net grid cost per local day."""
    cost = hourly_cost(hourly, site)
    return cost.groupby(local_dates(hourly.index)).sum().round(2)
