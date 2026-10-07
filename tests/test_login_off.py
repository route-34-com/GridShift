from dataclasses import replace

from tests.conftest import make_client


def test_without_login_everyone_is_the_local_admin(settings):
    client = make_client(replace(settings, require_login=False))
    assert client.get("/api/auth/setup").json()["needed"] is False
    me = client.get("/api/auth/me").json()
    assert me["local"] is True and me["role"] == "admin" and "plan.run" in me["permissions"]
    assert client.post("/api/runs").status_code == 201
    assert client.get("/api/runs/latest").status_code == 200
    entry = client.get("/api/audit", params={"action": "plan.run"}).json()["entries"][0]
    assert entry["user_email"] == "local@gridshift"


def test_local_admin_has_no_account_to_change(settings):
    client = make_client(replace(settings, require_login=False))
    assert client.put("/api/auth/profile", json={"name": "X"}).status_code == 409
    assert client.post("/api/auth/password", json={"current": "a", "new": "b"}).status_code == 409


def test_login_is_still_required_by_default(settings):
    assert make_client(settings).get("/api/runs/latest").status_code == 401


def test_large_responses_are_compressed(settings):
    client = make_client(replace(settings, require_login=False))
    client.post("/api/runs")
    response = client.get("/api/runs/latest/hourly", headers={"accept-encoding": "gzip"})
    assert response.headers.get("content-encoding") == "gzip"


def test_sign_in_is_required_unless_switched_off(monkeypatch):
    from backend.settings import load_settings

    monkeypatch.delenv("GRIDSHIFT_REQUIRE_LOGIN", raising=False)
    monkeypatch.setattr("backend.settings.load_dotenv", lambda *a, **k: None)
    assert load_settings().require_login is True
    monkeypatch.setenv("GRIDSHIFT_REQUIRE_LOGIN", "false")
    assert load_settings().require_login is False
