"""
app/views/reports.py
=====================
User-facing listing reports (FR-11, BR-06).

Business rules:
* BR-06 - any student may REPORT a listing, but reporting never removes
  content directly; moderation is an administrator function (BR-07);
* a user may keep only one open report per listing (anti-spam).
"""
from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)

from config import Config

from .. import db
from ..db import now
from ..emailer import send_notification_email
from ..security import current_user, login_required

bp = Blueprint("reports", __name__)


@bp.route("/listings/<int:listing_id>/report", methods=["GET", "POST"])
@login_required
def report_listing(listing_id):
    """Report an inappropriate / suspicious listing (FR-11)."""
    db_conn = db.get_db()
    listing = db_conn.query(
        """
        SELECT l.listing_id, l.title, l.user_id FROM listings l
        WHERE l.listing_id = ? AND l.status != 'removed'
        """,
        (listing_id,), one=True,
    )
    if listing is None:
        abort(404)

    if request.method == "POST":
        reason = request.form.get("reason", "")
        details = (request.form.get("details") or "").strip()

        errors = {}
        if reason not in Config.REPORT_REASONS:
            errors["reason"] = "Choose a report reason."
        if len(details) < 10:
            errors["details"] = "Please describe the problem (at least 10 characters)."

        # One OPEN report per user per listing (anti-spam control).
        open_duplicate = db_conn.query(
            """
            SELECT report_id FROM reports
            WHERE listing_id = ? AND reporter_id = ? AND status IN ('open', 'in_review')
            """,
            (listing_id, current_user()["user_id"]), one=True,
        )
        if open_duplicate:
            errors["reason"] = "You already have an open report for this listing."

        if errors:
            return render_template(
                "report_form.html", listing=listing, errors=errors,
                form=request.form, reasons=Config.REPORT_REASONS,
            ), 400

        db_conn.execute(
            """
            INSERT INTO reports (listing_id, reporter_id, reason, details,
                                 status, created_at)
            VALUES (?, ?, ?, ?, 'open', ?)
            """,
            (listing_id, current_user()["user_id"], reason, details, now()),
        )
        # Notify every administrator that a report is waiting (FR-10).
        for admin in db_conn.query(
            "SELECT email FROM users WHERE role = 'admin' AND status = 'active'"
        ):
            send_notification_email(
                admin["email"],
                "New listing report awaiting review",
                f"A report (reason: {reason}) was filed for listing "
                f"\"{listing['title']}\". Log in to the admin dashboard to review it.",
            )
        flash("Thank you - your report has been submitted for review.", "success")
        return redirect(url_for("listings.detail", listing_id=listing_id))

    return render_template(
        "report_form.html", listing=listing, errors={}, form={},
        reasons=Config.REPORT_REASONS,
    )
