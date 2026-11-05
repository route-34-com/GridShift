from datetime import datetime, timezone

import httpx
import pytest

from backend.sources import entsoe
from backend.sources.entsoe import fetch_day_ahead_entsoe, parse_prices
from backend.sources.http import SourceError

START = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)
END = datetime(2026, 11, 6, 23, tzinfo=timezone.utc)
NS = "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"


def period(start, end, resolution, points):
    body = "".join(f"<Point><position>{p}</position><price.amount>{v}</price.amount></Point>" for p, v in points)
    return f"<Period><timeInterval><start>{start}</start><end>{end}</end></timeInterval><resolution>{resolution}</resolution>{body}</Period>"


def document(*periods):
    series = "".join(f"<TimeSeries><curveType>A03</curveType>{p}</TimeSeries>" for p in periods)
    return f'<?xml version="1.0" encoding="UTF-8"?><Publication_MarketDocument xmlns="{NS}">{series}</Publication_MarketDocument>'


def acknowledgement(text):
    return (
        '<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">'
        f"<Reason><code>999</code><text>{text}</text></Reason></Acknowledgement_MarketDocument>"
    )


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def text_client(body, status=200):
    return client(lambda request: httpx.Response(status, text=body))


def quarter_day():
    return period("2026-11-05T23:00Z", "2026-11-06T23:00Z", "PT15M", [(i, float(i)) for i in range(1, 97)])


def test_quarter_hours_are_read_in_order():
    prices = fetch_day_ahead_entsoe(START, END, "token", text_client(document(quarter_day())))
    assert len(prices) == 96
    assert prices.index[0] == START and prices.iloc[0] == 1 and prices.iloc[-1] == 96
    assert (prices.index[1] - prices.index[0]).seconds == 900


def test_left_out_positions_repeat_the_previous_price():
    prices = parse_prices(document(period("2026-11-05T23:00Z", "2026-11-06T00:00Z", "PT15M", [(1, 50.0), (3, 70.0)])))
    assert prices.tolist() == [50.0, 50.0, 70.0, 70.0]


def test_finest_resolution_wins_when_both_are_published():
    hourly = period("2026-11-05T23:00Z", "2026-11-06T23:00Z", "PT60M", [(i, 999.0) for i in range(1, 25)])
    prices = parse_prices(document(hourly, quarter_day()))
    assert len(prices) == 96 and 999.0 not in prices.tolist()


def test_hourly_only_document_is_used():
    hourly = period("2026-11-05T23:00Z", "2026-11-06T23:00Z", "PT60M", [(i, float(i)) for i in range(1, 25)])
    assert len(parse_prices(document(hourly))) == 24


def test_prices_outside_the_window_are_dropped():
    two_days = period("2026-11-04T23:00Z", "2026-11-06T23:00Z", "PT60M", [(i, float(i)) for i in range(1, 49)])
    prices = fetch_day_ahead_entsoe(START, END, "token", text_client(document(two_days)))
    assert len(prices) == 24 and prices.index[0] == START


def test_no_matching_data_means_not_published_yet():
    assert parse_prices(acknowledgement("No matching data found for Data item Day-ahead Prices")).empty


def test_other_acknowledgements_raise():
    with pytest.raises(SourceError, match="refused"):
        parse_prices(acknowledgement("Request has invalid parameters"))


def test_bad_xml_raises():
    with pytest.raises(SourceError, match="valid XML"):
        parse_prices("<html>maintenance")


def test_request_parameters():
    seen = {}

    def handler(request):
        seen.update(request.url.params)
        return httpx.Response(200, text=document(quarter_day()))

    fetch_day_ahead_entsoe(START, END, "secret-token", client(handler))
    assert seen["documentType"] == "A44"
    assert seen["in_Domain"] == seen["out_Domain"] == "10Y1001A1001A82H"
    assert seen["periodStart"] == "202611042300" and seen["periodEnd"] == "202611072300"


def test_errors_never_leak_the_token():
    for response in (httpx.Response(503), httpx.Response(401)):
        with pytest.raises(SourceError) as caught:
            fetch_day_ahead_entsoe(START, END, "secret-token", client(lambda request, r=response: r))
        assert "secret-token" not in str(caught.value)

    def boom(request):
        raise httpx.ConnectError(f"cannot reach {request.url}")

    with pytest.raises(SourceError) as caught:
        fetch_day_ahead_entsoe(START, END, "secret-token", client(boom))
    assert "secret-token" not in str(caught.value)


def test_token_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv(entsoe.TOKEN_ENV, raising=False)
    assert entsoe.from_env() is None
    monkeypatch.setenv(entsoe.TOKEN_ENV, "  abc  ")
    assert entsoe.from_env().keywords == {"token": "abc"}
