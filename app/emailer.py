# Supports marketplace notifications and secure OTP emails.
# OTP values are never stored in the administrator's email log.

import logging
from flask import current_app
from app.db import get_db, now
logger = logging.getLogger(__name__)

#Record and optionally send a notification email.
#Returns True only when the email is successfully sent via SMTP.
#Sensitive content can be redacted from email_log using log_body.
def send_notification_email(recipient, subject, body, log_body=None):
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

            with smtplib.SMTP(
                smtp_host,
                current_app.config["SMTP_PORT"],
                timeout=10
            ) as smtp:
                smtp.starttls()

                if current_app.config.get("SMTP_USER"):
                    smtp.login(
                        current_app.config["SMTP_USER"],
                        current_app.config["SMTP_PASSWORD"]
                    )

                smtp.send_message(msg)

            status = "sent"

        except Exception as exc:
            logger.warning(
                "Email send failed (%s); logged to email_log",
                exc
            )
            status = "failed"

    # Store the redacted body when supplied.
    safe_body = log_body if log_body is not None else body

    db.execute(
        """
        INSERT INTO email_log
            (recipient, subject, body, status, sent_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (recipient, subject, safe_body, status, now())
    )

    return status == "sent"

#Send an OTP email without exposing the OTP in email_log.
def send_otp_email(recipient, otp, purpose="email verification"):
    subject = "UON Student Marketplace - Verification Code"

    body = f"""
Hello,

Your verification code for {purpose} is:

{otp}

This code expires in 5 minutes.

Do not share this code with anyone.

If you did not request this code, please ignore this email.

UON Student Marketplace
"""

    # The actual OTP is sent by email but never saved in email_log.
    redacted_body = """
OTP email sent.

The verification code has been redacted for security.
"""

    return send_notification_email(
        recipient,
        subject,
        body,
        log_body=redacted_body
    )
