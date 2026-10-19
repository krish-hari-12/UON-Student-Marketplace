"""
app/emailer.py
==============
Email notification helper (FR-10).

The marketplace notifies users about important events (new messages,
moderation outcomes) by email. When SMTP settings are not configured the
notification is *simulated*: it is stored in the ``email_log`` table and
can be reviewed by administrators under **Admin -> Email Log**. This keeps
the feature fully demonstrable without requiring a real mail server.

With SMTP settings present (config.py) the same helper sends real email.
"""
import logging

from flask import current_app

from .db import get_db, now

logger = logging.getLogger(__name__)


def send_notification_email(recipient, subject, body):
    """Record (and optionally send) a notification email.

    Returns True when the email was sent via SMTP, False when it was
    only logged to the database (simulated mode).
    """
    db = get_db()
    status = "simulated"

    smtp_host = current_app.config.get("SMTP_HOST")
    if smtp_host:
        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = current_app.config["EMAIL_FROM"]
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.set_content(body)

            with smtplib.SMTP(smtp_host, current_app.config["SMTP_PORT"], timeout=10) as s:
                s.starttls()
                if current_app.config.get("SMTP_USER"):
                    s.login(
                        current_app.config["SMTP_USER"],
                        current_app.config["SMTP_PASSWORD"],
                    )
                s.send_message(msg)
            status = "sent"
        except Exception as exc:  # never let mail failure break a request
            logger.warning("Email send failed (%s); logged to email_log", exc)
            status = "failed"

    db.execute(
        "INSERT INTO email_log (recipient, subject, body, status, sent_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (recipient, subject, body, status, now()),
    )
    return status == "sent"
