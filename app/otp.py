#OTP generation, secure storage, expiry and verification.

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from flask import current_app
from app.db import get_db, now


def _hash_otp(email, otp, purpose):
    #Create a keyed hash of the OTP.
    secret = current_app.config["SECRET_KEY"]
    value = f"{email.lower()}:{purpose}:{otp}"

    return hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def generate_otp(email, purpose):
    #Generate and securely store a new OTP.
    #Returns the OTP string, or None if the resend cooldown is active.
    email = email.strip().lower()

    if purpose not in ("registration", "password_reset"):
        raise ValueError("Invalid OTP purpose.")

    db = get_db()
    current_time = datetime.now()
    current_timestamp = now()

    # Check the resend cooldown.
    latest = db.query(
        """
        SELECT created_at
        FROM email_otps
        WHERE email = ? AND purpose = ?
        ORDER BY otp_id DESC
        LIMIT 1
        """,
        (email, purpose),
        one=True
    )

    if latest:
        last_created = datetime.strptime(
            latest["created_at"], "%Y-%m-%d %H:%M:%S"
        )
        cooldown = current_app.config["OTP_RESEND_COOLDOWN_SECONDS"]

        if (current_time - last_created).total_seconds() < cooldown:
            return None

    # Mark previous unused OTPs as used.
    db.execute(
        """
        UPDATE email_otps
        SET is_used = 1
        WHERE email = ? AND purpose = ? AND is_used = 0
        """,
        (email, purpose)
    )

    otp_length = current_app.config["OTP_LENGTH"]
    otp = f"{secrets.randbelow(10 ** otp_length):0{otp_length}d}"

    expiry = current_time + timedelta(
        minutes=current_app.config["OTP_EXPIRY_MINUTES"]
    )

    db.execute(
        """
        INSERT INTO email_otps
            (email, otp_hash, purpose, expires_at, attempts,
             is_used, created_at)
        VALUES (?, ?, ?, ?, 0, 0, ?)
        """,
        (
            email,
            _hash_otp(email, otp, purpose),
            purpose,
            expiry.strftime("%Y-%m-%d %H:%M:%S"),
            current_timestamp
        )
    )

    return otp


def verify_otp(email, otp, purpose):
    #Verify an OTP and mark it as used after successful verification.
    email = email.strip().lower()
    otp = (otp or "").strip()

    if purpose not in ("registration", "password_reset"):
        return False

    otp_length = current_app.config["OTP_LENGTH"]

    if len(otp) != otp_length or not otp.isdigit():
        return False

    db = get_db()

    record = db.query(
        """
        SELECT *
        FROM email_otps
        WHERE email = ? AND purpose = ? AND is_used = 0
        ORDER BY otp_id DESC
        LIMIT 1
        """,
        (email, purpose),
        one=True
    )

    if record is None:
        return False

    current_time = datetime.now()
    expiry = datetime.strptime(
        record["expires_at"], "%Y-%m-%d %H:%M:%S"
    )

    if current_time >= expiry:
        db.execute(
            "UPDATE email_otps SET is_used = 1 WHERE otp_id = ?",
            (record["otp_id"],)
        )
        return False

    max_attempts = current_app.config["OTP_MAX_ATTEMPTS"]

    if record["attempts"] >= max_attempts:
        db.execute(
            "UPDATE email_otps SET is_used = 1 WHERE otp_id = ?",
            (record["otp_id"],)
        )
        return False

    expected_hash = _hash_otp(email, otp, purpose)

    if not hmac.compare_digest(record["otp_hash"], expected_hash):
        new_attempts = record["attempts"] + 1

        db.execute(
            """
            UPDATE email_otps
            SET attempts = ?, is_used = ?
            WHERE otp_id = ?
            """,
            (
                new_attempts,
                1 if new_attempts >= max_attempts else 0,
                record["otp_id"]
            )
        )
        return False

    db.execute(
        "UPDATE email_otps SET is_used = 1 WHERE otp_id = ?",
        (record["otp_id"],)
    )

    return True
