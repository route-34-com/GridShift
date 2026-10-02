from datetime import datetime, timedelta, timezone

from backend.database import connect, iso
from tests.conftest import PASSWORD, add_user, make_client, sign_in


def admin_with_mail(mail_settings):
    client = make_client(mail_settings)
    if client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD, "name": "Ada Admin"}).status_code != 200:
        client.post("/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
    return client


def token_of(link: str) -> str:
    return link.split("#t=", 1)[1]


def test_invite_email_and_accept(mail_settings, mailbox):
    admin = admin_with_mail(mail_settings)
    invited = admin.post("/api/users/invite", json={"email": "pat@example.com", "role": "planner", "name": "Pat"})
    assert invited.status_code == 201 and invited.json()["emailed"] is True and "link" not in invited.json()
    message = mailbox.last("pat@example.com")
    assert message["Subject"] == "You've been invited to GridShift"
    assert "Ada Admin has invited you to GridShift as Planner" in message.get_body(("plain",)).get_content()
    link = mailbox.link("pat@example.com")
    assert link.startswith("http://gridshift.test/invite#t=")
    guest = make_client(mail_settings)
    assert guest.post("/api/auth/invite", json={"token": token_of(link)}).json() == {"email": "pat@example.com", "name": "Pat", "role": "planner"}
    accepted = guest.post("/api/auth/accept-invite", json={"token": token_of(link), "password": "pat-password-1"})
    assert accepted.status_code == 200 and accepted.json()["status"] == "active"
    assert guest.get("/api/auth/me").json()["role"] == "planner"
    reused = make_client(mail_settings).post("/api/auth/accept-invite", json={"token": token_of(link), "password": "pat-password-1"})
    assert reused.status_code == 400 and "expired or was already used" in reused.json()["detail"]


def test_invite_without_email_returns_link(admin):
    response = admin.post("/api/users/invite", json={"email": "no-mail@example.com", "role": "viewer"}).json()
    assert response["emailed"] is False and response["link"].startswith("http://gridshift.test/invite#t=")
    assert "isn't set up" in response["warning"]


def test_invite_rejects_duplicates_and_bad_input(admin):
    assert admin.post("/api/users/invite", json={"email": "admin@example.com", "role": "viewer"}).status_code == 400
    assert admin.post("/api/users/invite", json={"email": "bad", "role": "viewer"}).status_code == 400
    assert admin.post("/api/users/invite", json={"email": "x@example.com", "role": "superuser"}).status_code == 400


def test_resend_invite_voids_old_link(mail_settings, mailbox):
    admin = admin_with_mail(mail_settings)
    user_id = admin.post("/api/users/invite", json={"email": "sam@example.com", "role": "viewer"}).json()["id"]
    first = token_of(mailbox.link("sam@example.com"))
    assert admin.post(f"/api/users/{user_id}/resend-invite").json()["emailed"] is True
    second = token_of(mailbox.link("sam@example.com"))
    assert first != second
    guest = make_client(mail_settings)
    assert guest.post("/api/auth/invite", json={"token": first}).status_code == 400
    assert guest.post("/api/auth/invite", json={"token": second}).status_code == 200


def test_expired_invite_is_refused(admin, settings):
    link = admin.post("/api/users/invite", json={"email": "late@example.com", "role": "viewer"}).json()["link"]
    with connect(settings.db_path) as db:
        db.execute("UPDATE auth_tokens SET expires_at = ?", (iso(datetime.now(timezone.utc) - timedelta(seconds=1)),))
    assert make_client(settings).post("/api/auth/accept-invite", json={"token": token_of(link), "password": "late-pass-1"}).status_code == 400


def test_forgot_and_reset_password(mail_settings, mailbox):
    admin_with_mail(mail_settings)
    add_user(mail_settings, "op@example.com", "viewer")
    guest = make_client(mail_settings)
    answer = guest.post("/api/auth/forgot-password", json={"email": "OP@example.com"}).json()["message"]
    assert "If that email belongs" in answer
    assert mailbox.last("op@example.com")["Subject"] == "Reset your GridShift password"
    link = mailbox.link("op@example.com")
    assert link.startswith("http://gridshift.test/reset#t=")
    weak = guest.post("/api/auth/reset-password", json={"token": token_of(link), "password": "short"})
    assert weak.status_code == 400
    done = guest.post("/api/auth/reset-password", json={"token": token_of(link), "password": "fresh-pass-9"})
    assert done.status_code == 200
    assert mailbox.last("op@example.com")["Subject"] == "Your GridShift password was changed"
    assert make_client(mail_settings).post("/api/auth/login", json={"email": "op@example.com", "password": "fresh-pass-9"}).status_code == 200
    assert guest.post("/api/auth/reset-password", json={"token": token_of(link), "password": "again-pass-9"}).status_code == 400


def test_forgot_password_does_not_reveal_accounts(mail_settings, mailbox):
    admin_with_mail(mail_settings)
    guest = make_client(mail_settings)
    known = guest.post("/api/auth/forgot-password", json={"email": "admin@example.com"}).json()
    unknown = guest.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}).json()
    assert known == unknown
    assert mailbox.last("nobody@example.com") is None


def test_forgot_password_without_email_setup(admin, settings):
    message = make_client(settings).post("/api/auth/forgot-password", json={"email": "admin@example.com"}).json()["message"]
    assert "isn't set up" in message


def test_forgot_password_is_rate_limited(mail_settings, mailbox):
    admin_with_mail(mail_settings)
    guest = make_client(mail_settings)
    for _ in range(5):
        guest.post("/api/auth/forgot-password", json={"email": "admin@example.com"})
    assert guest.post("/api/auth/forgot-password", json={"email": "admin@example.com"}).status_code == 429


def test_admin_reset_link_and_session_revoked(mail_settings, mailbox):
    admin = admin_with_mail(mail_settings)
    user_id = add_user(mail_settings, "op@example.com", "planner")
    op = sign_in(mail_settings, "op@example.com")
    assert admin.post(f"/api/users/{user_id}/reset-link").json()["emailed"] is True
    make_client(mail_settings).post("/api/auth/reset-password", json={"token": token_of(mailbox.link("op@example.com")), "password": "brand-new-9"})
    assert op.get("/api/auth/me").status_code == 401


def test_role_change_and_disable_sign_user_out(admin, settings):
    user_id = add_user(settings, "op@example.com", "planner")
    op = sign_in(settings, "op@example.com")
    assert admin.put(f"/api/users/{user_id}", json={"role": "viewer"}).json()["role"] == "viewer"
    assert op.get("/api/auth/me").status_code == 401
    op = sign_in(settings, "op@example.com")
    admin.put(f"/api/users/{user_id}", json={"status": "disabled"})
    assert op.get("/api/auth/me").status_code == 401


def test_last_admin_is_protected(admin, settings):
    me = admin.get("/api/auth/me").json()["id"]
    demote = admin.put(f"/api/users/{me}", json={"role": "viewer"})
    assert demote.status_code == 400 and "at least one active admin" in demote.json()["detail"]
    assert admin.delete(f"/api/users/{me}").status_code == 400
    second = add_user(settings, "second@example.com", "admin")
    assert admin.put(f"/api/users/{second}", json={"role": "viewer"}).status_code == 200


def test_delete_user_and_invited_status_rules(admin, settings):
    invited = admin.post("/api/users/invite", json={"email": "inv@example.com", "role": "viewer"}).json()["id"]
    assert admin.put(f"/api/users/{invited}", json={"status": "disabled"}).status_code == 400
    assert admin.delete(f"/api/users/{invited}").status_code == 200
    assert all(u["email"] != "inv@example.com" for u in admin.get("/api/users").json())
    assert admin.delete("/api/users/999").status_code == 404


def test_test_email(mail_settings, mailbox, admin):
    assert admin.post("/api/users/test-email").status_code == 400
    with_mail = admin_with_mail(mail_settings)
    assert with_mail.post("/api/users/test-email").status_code == 200
    assert mailbox.last("admin@example.com")["Subject"] == "GridShift test email"


def test_unreachable_mail_server_falls_back_to_link(settings):
    from dataclasses import replace

    from backend.settings import Smtp

    broken = replace(settings, smtp=Smtp("127.0.0.1", 1, "", "", "GridShift <g@example.com>", "none"))
    client = make_client(broken)
    client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD})
    result = client.post("/api/users/invite", json={"email": "x@example.com", "role": "viewer"}).json()
    assert result["emailed"] is False and "could not be sent" in result["warning"] and "#t=" in result["link"]
    actions = [e["action"] for e in client.get("/api/audit").json()["entries"]]
    assert "email.failed" in actions
