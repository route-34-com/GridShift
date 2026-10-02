"""Send email through the configured SMTP server."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from backend.settings import Smtp

log = logging.getLogger("gridshift.mail")
TIMEOUT_SECONDS = 20


class MailError(Exception):
    """The email could not be handed to the SMTP server."""


def mail_status(smtp: Smtp) -> dict:
    """Return whether email is set up, without any secret."""
    return {"configured": smtp.enabled, "host": smtp.host or None, "sender": smtp.sender or None}


def send_mail(smtp: Smtp, to: list[str] | str, subject: str, html: str, text: str) -> bool:
    """Send one email; False when email is not set up, MailError when sending fails."""
    recipients = [to] if isinstance(to, str) else list(to)
    if not smtp.enabled or not recipients:
        return False
    message = EmailMessage()
    message["From"] = smtp.sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    try:
        if smtp.tls == "ssl":
            server = smtplib.SMTP_SSL(smtp.host, smtp.port, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(smtp.host, smtp.port, timeout=TIMEOUT_SECONDS)
        with server:
            if smtp.tls == "starttls":
                server.starttls(context=ssl.create_default_context())
            if smtp.user:
                server.login(smtp.user, smtp.password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        log.warning("Email to %s failed: %s", recipients, exc)
        raise MailError(f"The email could not be sent ({exc.__class__.__name__}).") from exc
    return True
