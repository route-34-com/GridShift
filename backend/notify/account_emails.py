"""Invitation, password reset and test emails."""

from datetime import datetime

from backend.auth.permissions import ROLE_NAMES
from backend.notify.email import TEMPLATES
from backend.planner.model import LOCAL_TZ

Message = tuple[str, str, str]


def _render(label: str, title: str, paragraphs: list[str], notes: list[str], action: tuple[str, str] | None = None) -> str:
    sent = datetime.now(LOCAL_TZ).strftime("%d %b %Y, %H:%M %Z")
    return TEMPLATES.get_template("account.html").render(
        label=label,
        title=title,
        paragraphs=paragraphs,
        notes=notes,
        action={"label": action[0], "url": action[1]} if action else None,
        sent=sent,
    )


def invite_email(name: str | None, invited_by: str, role: str, link: str) -> Message:
    """Return subject, HTML and text of an invitation."""
    role_name = ROLE_NAMES.get(role, role)
    hello = f"Hi {name}," if name else "Hello,"
    lines = [hello, f"{invited_by} has invited you to GridShift as {role_name}. Click below to set your password and activate your account."]
    notes = ["This link expires in 7 days and works once.", "If you weren't expecting this invitation, you can ignore this email."]
    html = _render("Invitation", "You're invited to GridShift", lines, notes, ("Accept invitation", link))
    text = "\n\n".join([*lines, "Open this link to set your password (expires in 7 days):", link])
    return "You've been invited to GridShift", html, text


def reset_email(link: str) -> Message:
    """Return subject, HTML and text of a password reset."""
    lines = ["We received a request to reset the password for your GridShift account.", "Click below to choose a new password."]
    notes = ["This link expires in 1 hour and works once.", "If you didn't ask for this, you can ignore this email; your password stays the same."]
    html = _render("Security", "Reset your password", lines, notes, ("Reset password", link))
    text = "\n\n".join([*lines, "Open this link to choose a new password (expires in 1 hour):", link])
    return "Reset your GridShift password", html, text


def password_changed_email(name: str | None) -> Message:
    """Return subject, HTML and text of a password-changed notice."""
    lines = [f"Hi {name}," if name else "Hello,", "The password for your GridShift account was just changed and all other sessions were signed out."]
    notes = ["If this wasn't you, ask your GridShift admin to send you a reset link right away."]
    html = _render("Security", "Your password was changed", lines, notes)
    return "Your GridShift password was changed", html, "\n\n".join([*lines, *notes])


def test_email(sender: str) -> Message:
    """Return subject, HTML and text of the test email."""
    lines = [f"Email from GridShift is working. Invitations, password resets and daily plans will be sent from {sender}."]
    html = _render("Test", "Email is working", lines, ["You can ignore this email."])
    return "GridShift test email", html, lines[0]
