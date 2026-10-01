"""Render and send plan emails."""

import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.planner.model import LOCAL_TZ
from backend.settings import Smtp

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=select_autoescape(["html"]))


def _local(stamp: str, fmt: str) -> str:
    return datetime.fromisoformat(stamp).astimezone(LOCAL_TZ).strftime(fmt)


TEMPLATES.filters["local"] = _local
TEMPLATES.filters["eur"] = lambda v: f"€{v:,.0f}" if abs(v) >= 100 else f"€{v:,.2f}"
TEMPLATES.filters["pct"] = lambda v: f"{v:.0%}"
TEMPLATES.filters["kwh"] = lambda v: f"{v / 1000:,.1f} MWh" if abs(v) >= 1000 else f"{v:,.0f} kWh"


def render_plan_email(payload: dict) -> tuple[str, str]:
    """Return the subject and HTML body of the daily plan email."""
    first = payload["daily"][0]
    tomorrow = [b for b in payload["blocks"] if b["start"] < payload["daily"][1]["start"]] if len(payload["daily"]) > 1 else payload["blocks"]
    subject = f"GridShift plan for {first['label']}: €{first['cost_eur']:,.0f} tomorrow · €{payload['summary']['savings_eur']:,.0f} saved this week"
    if payload["alerts"]:
        subject = f"[{len(payload['alerts'])} alert{'s' if len(payload['alerts']) > 1 else ''}] " + subject
    html = TEMPLATES.get_template("daily_plan.html").render(run=payload, first=first, tomorrow=tomorrow)
    return subject, html


def send_email(smtp: Smtp, recipients: list[str], subject: str, html: str) -> str:
    """Send an HTML email and return a short delivery status."""
    if not smtp.enabled:
        return "disabled"
    if not recipients:
        return "no recipients"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp.sender
    message["To"] = ", ".join(recipients)
    message.set_content("Open this email in an HTML-capable client to see the GridShift plan.")
    message.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(smtp.host, smtp.port, timeout=30) as server:
            if smtp.starttls:
                server.starttls(context=ssl.create_default_context())
            if smtp.user:
                server.login(smtp.user, smtp.password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        return f"failed: {exc}"
    return "sent"
