
#Handle student reports for inappropriate or suspicious listings.

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from config import Config
from app import db
from app.db import now
from app.emailer import send_notification_email
from app.security import current_user, login_required

bp = Blueprint("reports", __name__)

#Allow students to report a listing for review.
@bp.route("/listings/<int:listing_id>/report", methods=["GET", "POST"])
@login_required
def report_listing(listing_id):
    db_conn = db.get_db()
    user_id = current_user()["user_id"]

    # Check that the listing exists and has not been removed.
    listing = db_conn.query(
        """
        SELECT l.listing_id, l.title, l.user_id
        FROM listings l
        WHERE l.listing_id = ? AND l.status != 'removed'
        """,
        (listing_id,),
        one=True,
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

        # Prevent users from submitting multiple open reports for the same listing.
        open_duplicate = db_conn.query(
            """
            SELECT report_id FROM reports
            WHERE listing_id = ? AND reporter_id = ?
            AND status IN ('open', 'in_review')
            """,
            (listing_id, user_id),
            one=True,
        )

        if open_duplicate:
            errors["reason"] = "You already have an open report for this listing."

        if errors:
            return render_template(
                "report_form.html",
                listing=listing,
                errors=errors,
                form=request.form,
                reasons=Config.REPORT_REASONS,
            ), 400

        # Save the report for administrator review.
        db_conn.execute(
            """
            INSERT INTO reports (
                listing_id, reporter_id, reason, details, status, created_at
            )
            VALUES (?, ?, ?, ?, 'open', ?)
            """,
            (listing_id, user_id, reason, details, now()),
        )

        # Notify active administrators about the new report.
        admins = db_conn.query(
            "SELECT email FROM users WHERE role = 'admin' AND status = 'active'"
        )

        for admin in admins:
            send_notification_email(
                admin["email"],
                "New listing report awaiting review",
                f"A report (reason: {reason}) was filed for listing "
                f"\"{listing['title']}\". Log in to the admin dashboard to review it.",
            )

        flash("Thank you - your report has been submitted for review.", "success")
        return redirect(url_for("listings.detail", listing_id=listing_id))

    return render_template(
        "report_form.html",
        listing=listing,
        errors={},
        form={},
        reasons=Config.REPORT_REASONS,
    )
