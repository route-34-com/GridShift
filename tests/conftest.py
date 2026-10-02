import socket
from dataclasses import replace
from datetime import datetime, timezone
from email import message_from_bytes
from email.policy import default

import numpy as np
import pandas as pd
import pytest
from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.auth import lockout
from backend.auth.passwords import hash_password
from backend.database import connect, insert, now_iso
from backend.pipeline import Sources
from backend.settings import ROOT, Settings, Smtp
from backend.sources.http import SourceError
from backend.store import Store

NOW = datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc)


def hours(start, end):
    return pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="h", inclusive="left")


def fake_prices(start, end):
    index = hours(start, end)[:24]
    local = index.tz_convert("Europe/Berlin").hour
    return pd.Series(np.where((local < 6) | (local >= 22), 60.0, 140.0), index=index)


def fake_site_weather(site, start, end):
    index = hours(start, end)
    local = index.tz_convert("Europe/Berlin").hour.to_numpy()
    sun = np.clip(np.sin((local - 6) / 13 * np.pi), 0, None) * 700
    return pd.DataFrame({"irradiance": sun, "wind_100m": 6.0, "temperature": 14.0}, index=index)


def fake_national(start, end):
    return pd.DataFrame({"wind": 6.0, "solar": 150.0, "temperature": 14.0}, index=hours(start, end))


def broken(*args, **kwargs):
    raise SourceError("simulated outage")


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=ROOT / "data" / "sample",
        db_path=tmp_path / "test.db",
        solver_time_limit=30,
        smtp=Smtp("", 587, "", "", "gridshift@example.com", "none"),
        app_url="http://gridshift.test",
    )


@pytest.fixture
def store(settings) -> Store:
    return Store(settings.db_path)


def good_sources() -> Sources:
    return Sources(day_ahead=fake_prices, site_weather=fake_site_weather, national_weather=fake_national)


class Mailbox:
    """Collect messages delivered to a local SMTP server."""

    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(message_from_bytes(envelope.content, policy=default))
        return "250 OK"

    def last(self, to: str | None = None):
        found = [m for m in self.messages if to is None or to in m["To"]]
        return found[-1] if found else None

    def link(self, to: str | None = None) -> str:
        body = self.last(to).get_body(("plain",)).get_content()
        return next(line.strip() for line in body.splitlines() if "#t=" in line)


@pytest.fixture
def mailbox():
    box = Mailbox()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        box.port = probe.getsockname()[1]
    controller = Controller(box, hostname="127.0.0.1", port=box.port)
    controller.start()
    yield box
    controller.stop()


@pytest.fixture
def mail_settings(settings, mailbox) -> Settings:
    return replace(settings, smtp=Smtp("127.0.0.1", mailbox.port, "", "", "GridShift <gridshift@example.com>", "none"))


@pytest.fixture(autouse=True)
def reset_lockouts():
    lockout.logins.reset()
    lockout.links.reset()
    yield
    lockout.logins.reset()
    lockout.links.reset()


PASSWORD = "secret-pass-1"


def make_client(settings: Settings, sources: Sources | None = None) -> TestClient:
    return TestClient(create_app(settings, sources or good_sources(), dist=settings.db_path.parent / "no-dist"))


def add_user(settings: Settings, email: str, role: str, status: str = "active") -> int:
    with connect(settings.db_path) as db:
        return insert(db, "users", {"email": email, "name": email.split("@")[0].title(), "role": role, "status": status, "password_hash": hash_password(PASSWORD), "created_at": now_iso()})


def sign_in(settings: Settings, email: str, sources: Sources | None = None) -> TestClient:
    client = make_client(settings, sources)
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def admin(settings) -> TestClient:
    client = make_client(settings)
    assert client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada Admin"}).status_code == 200
    return client
