from datetime import datetime, timedelta, timezone

from backend.database import connect, iso
from tests.conftest import PASSWORD, add_user, make_client, sign_in


def test_everything_needs_sign_in(settings):
    client = make_client(settings)
    for path in ("/api/runs/latest", "/api/status", "/api/config", "/api/users", "/api/audit", "/api/exports/run/report"):
        assert client.get(path).status_code == 401, path
    assert client.post("/api/runs").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_first_admin_setup_only_once(settings):
    client = make_client(settings)
    assert client.get("/api/auth/setup").json()["needed"] is True
    created = client.post("/api/auth/setup", json={"email": "Boss@Example.com", "password": PASSWORD, "name": "Boss"})
    assert created.status_code == 200 and created.json()["role"] == "admin"
    assert created.json()["email"] == "boss@example.com"
    again = make_client(settings).post("/api/auth/setup", json={"email": "x@example.com", "password": PASSWORD})
    assert again.status_code == 403


def test_remote_setup_refused_without_flag(settings):
    client = make_client(settings)
    response = client.post("/api/auth/setup", json={"email": "a@example.com", "password": PASSWORD}, headers={"x-forwarded-for": "203.0.113.9"})
    assert response.status_code == 403


def test_setup_validates_email_and_password(settings):
    client = make_client(settings)
    assert client.post("/api/auth/setup", json={"email": "not-an-email", "password": PASSWORD}).status_code == 400
    weak = client.post("/api/auth/setup", json={"email": "a@example.com", "password": "short"})
    assert weak.status_code == 400 and "at least 8" in weak.json()["detail"]
    digits = client.post("/api/auth/setup", json={"email": "a@example.com", "password": "12345678"})
    assert "mix of letters" in digits.json()["detail"]


def test_login_logout_and_me(admin, settings):
    add_user(settings, "viewer@example.com", "viewer")
    client = sign_in(settings, "VIEWER@example.com")
    me = client.get("/api/auth/me").json()
    assert me["role"] == "viewer" and "plan.run" not in me["permissions"]
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_wrong_password_and_unknown_email_look_the_same(admin, settings):
    client = make_client(settings)
    wrong = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "nope-nope-1"})
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope-nope-1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_lockout_after_five_failures(admin, settings):
    client = make_client(settings)
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "admin@example.com", "password": "bad-guess-1"})
    locked = client.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert locked.status_code == 429 and "15 minutes" in locked.json()["detail"]


def test_disabled_and_invited_accounts_cannot_sign_in(admin, settings):
    add_user(settings, "off@example.com", "viewer", status="disabled")
    add_user(settings, "new@example.com", "viewer", status="invited")
    client = make_client(settings)
    off = client.post("/api/auth/login", json={"email": "off@example.com", "password": PASSWORD})
    assert off.status_code == 401 and "switched off" in off.json()["detail"]
    new = client.post("/api/auth/login", json={"email": "new@example.com", "password": PASSWORD})
    assert "invitation" in new.json()["detail"]


def test_expired_session_is_rejected(admin, settings):
    with connect(settings.db_path) as db:
        db.execute("UPDATE sessions SET expires_at = ?", (iso(datetime.now(timezone.utc) - timedelta(minutes=1)),))
    assert admin.get("/api/auth/me").status_code == 401


def test_change_own_password(admin, settings):
    wrong = admin.post("/api/auth/password", json={"current": "not-it-123", "new": "brand-new-pass-2"})
    assert wrong.status_code == 400
    ok = admin.post("/api/auth/password", json={"current": PASSWORD, "new": "brand-new-pass-2"})
    assert ok.status_code == 200
    assert admin.get("/api/auth/me").status_code == 200
    old = make_client(settings).post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    assert old.status_code == 401
    new = make_client(settings).post("/api/auth/login", json={"email": "admin@example.com", "password": "brand-new-pass-2"})
    assert new.status_code == 200


def test_update_profile_name(admin):
    response = admin.put("/api/auth/profile", json={"name": "  Ada L.  "})
    assert response.json()["name"] == "Ada L."


def test_viewer_cannot_plan_or_manage(admin, settings):
    add_user(settings, "viewer@example.com", "viewer")
    viewer = sign_in(settings, "viewer@example.com")
    assert viewer.post("/api/runs").status_code == 403
    assert viewer.get("/api/users").status_code == 403
    assert viewer.get("/api/audit").status_code == 403
    assert viewer.get("/api/exports/audit").status_code == 403


def test_planner_can_plan_but_not_manage(admin, settings):
    add_user(settings, "planner@example.com", "planner")
    planner = sign_in(settings, "planner@example.com")
    assert planner.post("/api/runs").status_code == 201
    assert planner.get("/api/users").status_code == 403
    assert planner.get("/api/exports/run/schedule?format=csv").status_code == 200
