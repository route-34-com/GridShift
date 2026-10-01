"""Convert weather forecasts into on-site solar and wind output."""

import numpy as np
import pandas as pd

from backend.planner.model import Solar, Wind


def solar_kw(weather: pd.DataFrame, solar: Solar) -> pd.Series:
    """Return PV output in kW from tilted irradiance and air temperature."""
    irradiance = weather["irradiance"].clip(lower=0).fillna(0)
    cell_temp = weather["temperature"].fillna(15) + 0.03 * irradiance
    derate = (1 - 0.004 * (cell_temp - 25)).clip(0.7, 1.05)
    output = solar.kwp * irradiance / 1000 * solar.performance_ratio * derate
    return output.clip(0, solar.kwp).rename("solar_kw")


def wind_kw(weather: pd.DataFrame, wind: Wind) -> pd.Series:
    """Return turbine output in kW from 100 m wind speed adjusted to hub height."""
    speed = weather["wind_100m"].clip(lower=0).fillna(0) * (wind.hub_height_m / 100) ** (1 / 7)
    speeds, power = zip(*wind.power_curve)
    output = np.interp(speed.to_numpy(), speeds, power, left=0, right=0)
    return pd.Series(np.clip(output, 0, wind.rated_kw), index=weather.index, name="wind_kw")
