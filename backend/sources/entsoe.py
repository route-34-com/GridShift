"""German day-ahead prices from the ENTSO-E Transparency Platform, the official European source."""

import os
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import partial

import httpx
import pandas as pd

from backend.sources.http import SourceError
from backend.sources.price import _window

URL = "https://web-api.tp.entsoe.eu/api"
DE_LU = "10Y1001A1001A82H"
TOKEN_ENV = "ENTSOE_API_TOKEN"
RESOLUTIONS = {"PT15M": timedelta(minutes=15), "PT30M": timedelta(minutes=30), "PT60M": timedelta(hours=1)}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in node if _local(c.tag) == name]


def _text(node: ET.Element, *path: str) -> str | None:
    for name in path:
        found = _children(node, name)
        if not found:
            return None
        node = found[0]
    return (node.text or "").strip()


def _stamp(value: str) -> pd.Timestamp:
    return pd.Timestamp(datetime.strptime(value, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc))


def _period(period: ET.Element) -> tuple[timedelta, pd.Series]:
    """Return one period's step length and prices, repeating the last price where positions are left out (curve A03)."""
    start, end = _text(period, "timeInterval", "start"), _text(period, "timeInterval", "end")
    step = RESOLUTIONS.get(_text(period, "resolution") or "")
    if not start or not end or step is None:
        raise SourceError("ENTSO-E period is missing its interval or has an unknown resolution")
    first, last = _stamp(start), _stamp(end)
    slots = int((last - first) / step)
    points = {}
    for point in _children(period, "Point"):
        position, amount = _text(point, "position"), _text(point, "price.amount")
        if position and amount:
            points[int(position)] = float(amount)
    values, current = [], None
    for position in range(1, slots + 1):
        current = points.get(position, current)
        values.append(current)
    index = pd.date_range(first, periods=slots, freq=step)
    return step, pd.Series(values, index=index, dtype="float64")


def parse_prices(text: str) -> pd.Series:
    """Return prices in EUR/MWh from an ENTSO-E day-ahead document, keeping the finest resolution it holds."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SourceError("ENTSO-E returned a response that isn't valid XML") from exc
    if _local(root.tag) == "Acknowledgement_MarketDocument":
        reason = _text(root, "Reason", "text") or "no reason given"
        if "no matching data" in reason.lower():
            return pd.Series(dtype="float64", name="price")
        raise SourceError(f"ENTSO-E refused the request: {reason[:200]}")
    if _local(root.tag) != "Publication_MarketDocument":
        raise SourceError("ENTSO-E returned an unexpected document")
    by_step: dict[timedelta, list[pd.Series]] = {}
    for series in _children(root, "TimeSeries"):
        for period in _children(series, "Period"):
            step, prices = _period(period)
            by_step.setdefault(step, []).append(prices)
    if not by_step:
        return pd.Series(dtype="float64", name="price")
    finest = pd.concat(by_step[min(by_step)])
    return finest[~finest.index.duplicated(keep="last")].sort_index().rename("price")


def _get(params: dict, client: httpx.Client, retries: int = 3) -> str:
    """Return the response body, with errors that never include the URL, because it carries the token."""
    problem = "no response"
    for attempt in range(retries):
        try:
            response = client.get(URL, params=params)
        except httpx.HTTPError as exc:
            problem = type(exc).__name__
        else:
            if response.status_code == 401:
                raise SourceError("ENTSO-E rejected the API token (HTTP 401)")
            if response.status_code < 500 and response.status_code != 429:
                return response.text
            problem = f"HTTP {response.status_code}"
        if attempt < retries - 1:
            time.sleep(0.5 * 2**attempt)
    raise SourceError(f"ENTSO-E failed after {retries} attempts: {problem}")


def fetch_day_ahead_entsoe(start: datetime, end: datetime, token: str, client: httpx.Client | None = None) -> pd.Series:
    """Return DE-LU day-ahead prices in EUR/MWh for [start, end) in UTC, at the market's own resolution."""
    params = {
        "securityToken": token,
        "documentType": "A44",
        "in_Domain": DE_LU,
        "out_Domain": DE_LU,
        "contract_MarketAgreement.type": "A01",
        "periodStart": (start - timedelta(days=1)).strftime("%Y%m%d%H00"),
        "periodEnd": (end + timedelta(days=1)).strftime("%Y%m%d%H00"),
    }
    owned = client is None
    client = client or httpx.Client(timeout=30)
    try:
        return _window(parse_prices(_get(params, client)), start, end)
    finally:
        if owned:
            client.close()


def from_env() -> Callable | None:
    """Return the ENTSO-E fetcher when an API token is configured, else None so the next source is used."""
    token = (os.getenv(TOKEN_ENV) or "").strip()
    return partial(fetch_day_ahead_entsoe, token=token) if token else None
