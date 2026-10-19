"""
app/views/admin.py
==================
Administration and moderation area (FR-12, FR-13) - every route requires
the administrator role (BR-07, BR-09, FR-14) and writes an audit-log entry
for every moderation or management action (BR-08).
"""
from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)

from .. import db
from ..db import now
from ..emailer import send_notification_email
from ..security import admin_required, current_user

bp = Blueprint("admin", __name__)


# ----------------------------------------------------------------------
# Dashboard + monitoring (WP-1.7.7)
# ----------------------------------------------------------------------
@bp.route("/")
@admin_required
def dashboard():
    """Platform overview: counts, recent reports and recent audit entries."""
    db_conn = db.get_db()
    stats = {
        "users": db_conn.query("SELECT COUNT(*) AS n FROM users", one=True)["n"],
        "listings": db_conn.query(
            "SELECT COUNT(*) AS n FROM listings WHERE status = 'active'", one=True
        )["n"],
        "open_reports": db_conn.query(
            "SELECT COUNT(*) AS n FROM reports WHERE status = 'open'", one=True
        )["n"],
        "messages": db_conn.query(
            "SELECT COUNT(*) AS n FROM messages", one=True
        )["n"],
    }
    recent_reports = db_conn.query(
        """
        SELECT r.*, l.title AS listing_title FROM reports r
        JOIN listings l ON l.listing_id = r.listing_id
        WHERE r.status = 'open' ORDER BY r.created_at DESC LIMIT 5
        """
    )
    recent_audit = db_conn.query(
        """
        SELECT a.*, u.first_name || ' ' || u.last_name AS admin_name
        FROM audit_log a JOIN users u ON u.user_id = a.admin_id
        ORDER BY a.audit_id DESC LIMIT 8
        """
    )
    return render_template(
        "admin/dashboard.html", stats=stats,
        recent_reports=recent_reports, recent_audit=recent_audit,
    )


# ----------------------------------------------------------------------
# Report review + moderation (FR-12, WP-1.7.4, WP-1.7.5)
# ----------------------------------------------------------------------
@bp.route("/reports")
@admin_required
def reports():
    """All listing reports with their status."""
    status = request.args.get("status", "")
    params, where = [], "1=1"
    if status in ("open", "in_review", "resolved", "dismissed"):
        where = "r.status = ?"
        params.append(status)
    rows = db.get_db().query(
        f"""
        SELECT r.*, l.title AS listing_title, l.status AS listing_status,
               u.first_name || ' ' || u.last_name AS reporter_name
        FROM reports r
        JOIN listings l ON l.listing_id = r.listing_id
        JOIN users u ON u.user_id = r.reporter_id
        WHERE {where}
        ORDER BY CASE r.status WHEN 'open' THEN 0 WHEN 'in_review' THEN 1 ELSE 2 END,
                 r.created_at DESC
        """,
        params,
    )
    return render_template("admin/reports.html", reports=rows, status=status)


@bp.route("/reports/<int:report_id>", methods=["GET", "POST"])
@admin_required
def report_detail(report_id):
    """Review one report and apply a moderation action (BR-07, BR-08)."""
    db_conn = db.get_db()
    report = _get_report(report_id)
    if report is None:
        abort(404)

    if request.method == "POST":
        action = request.form.get("action", "")
        note = (request.form.get("note") or "").strip()[:500]

        if action == "remove_listing":
            db_conn.execute(
                "UPDATE listings SET status = 'removed', updated_at = ? WHERE listing_id = ?",
                (now(), report["listing_id"]),
            )
            _audit("REMOVE_LISTING", "listing", report["listing_id"],
                   f"Removed listing for report #{report_id}: {note}")
            db_conn.execute(
                "UPDATE reports SET status = 'resolved', resolved_by = ?, "
                "resolved_at = ?, resolution_note = ? WHERE report_id = ?",
                (current_user()["user_id"], now(), note or "Listing removed", report_id),
            )
            _notify_reporter(report, "resolved - the listing was removed")
            flash("Listing removed and report resolved.", "success")

        elif action == "dismiss":
            db_conn.execute(
                "UPDATE reports SET status = 'dismissed', resolved_by = ?, "
                "resolved_at = ?, resolution_note = ? WHERE report_id = ?",
                (current_user()["user_id"], now(), note or "No breach found", report_id),
            )
            _audit("DISMISS_REPORT", "report", report_id, note)
            flash("Report dismissed.", "info")

        elif action == "in_review":
            db_conn.execute(
                "UPDATE reports SET status = 'in_review' WHERE report_id = ?", (report_id,)
            )
            _audit("REVIEW_REPORT", "report", report_id, note)
            flash("Report marked as under review.", "info")

        else:
            abort(400)

        return redirect(url_for("admin.report_detail", report_id=report_id))

    return render_template("admin/report_detail.html", report=report)


# ----------------------------------------------------------------------
# User management (FR-13, WP-1.7.2)
# ----------------------------------------------------------------------
@bp.route("/users")
@admin_required
def users():
    rows = db.get_db().query(
        """
        SELECT u.*,
               (SELECT COUNT(*) FROM listings l WHERE l.user_id = u.user_id) AS listing_count
        FROM users u ORDER BY u.user_id
        """
    )
    return render_template("admin/users.html", users=rows)


@bp.route("/users/<int:user_id>/status", methods=["POST"])
@admin_required
def set_user_status(user_id):
    """Suspend or re-activate a user account (BR-08 audited)."""
    new_status = request.form.get("status", "")
    if new_status not in ("active", "suspended"):
        abort(400)
    if user_id == current_user()["user_id"]:
        flash("You cannot change the status of your own account.", "warning")
        return redirect(url_for("admin.users"))

    target = db.get_db().query("SELECT * FROM users WHERE user_id = ?", (user_id,), one=True)
    if target is None:
        abort(404)
    db.get_db().execute(
        "UPDATE users SET status = ? WHERE user_id = ?", (new_status, user_id)
    )
    _audit("SET_USER_STATUS", "user", user_id, f"status -> {new_status}")
    flash(f"Account {target['email']} is now {new_status}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def set_user_role(user_id):
    """Grant or revoke administrator rights (protected admin logic, BR-09)."""
    new_role = request.form.get("role", "")
    if new_role not in ("student", "admin"):
        abort(400)
    if user_id == current_user()["user_id"]:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.users"))

    target = db.get_db().query("SELECT * FROM users WHERE user_id = ?", (user_id,), one=True)
    if target is None:
        abort(404)
    db.get_db().execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
    _audit("SET_USER_ROLE", "user", user_id, f"role -> {new_role}")
    flash(f"Role for {target['email']} set to {new_role}.", "success")
    return redirect(url_for("admin.users"))


# ----------------------------------------------------------------------
# Listing management (FR-13, WP-1.7.3)
# ----------------------------------------------------------------------
@bp.route("/listings")
@admin_required
def listings():
    """Every listing on the platform with filters."""
    q = (request.args.get("q") or "").strip()
    status = request.args.get("status", "")
    where, params = ["1=1"], []
    if q:
        where.append("l.title LIKE ?")
        params.append(f"%{q}%")
    if status in ("active", "archived", "sold", "removed"):
        where.append("l.status = ?")
        params.append(status)
    rows = db.get_db().query(
        f"""
        SELECT l.*, c.name AS category_name,
               u.first_name || ' ' || u.last_name AS owner_name
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        JOIN users u ON u.user_id = l.user_id
        WHERE {' AND '.join(where)}
        ORDER BY l.created_at DESC
        """,
        params,
    )
    return render_template("admin/listings.html", listings=rows, q=q, status=status)


@bp.route("/listings/<int:listing_id>/moderate", methods=["POST"])
@admin_required
def moderate_listing(listing_id):
    """Remove / restore / archive a listing as administrator (BR-08 audited)."""
    new_status = request.form.get("status", "")
    if new_status not in ("active", "archived", "removed"):
        abort(400)
    listing = db.get_db().query(
        "SELECT * FROM listings WHERE listing_id = ?", (listing_id,), one=True
    )
    if listing is None:
        abort(404)
    db.get_db().execute(
        "UPDATE listings SET status = ?, updated_at = ? WHERE listing_id = ?",
        (new_status, now(), listing_id),
    )
    _audit("MODERATE_LISTING", "listing", listing_id, f"status -> {new_status}")
    flash(f"Listing \"{listing['title']}\" is now {new_status}.", "success")
    return redirect(url_for("admin.listings"))


# ----------------------------------------------------------------------
# Category management (FR-13, WP-1.7.6)
# ----------------------------------------------------------------------
@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    """Add a new listing category (FR-13)."""
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()[:200]
        if not (2 <= len(name) <= 50):
            flash("Category name must be 2-50 characters.", "danger")
        elif db.get_db().query(
            "SELECT 1 AS x FROM categories WHERE LOWER(name) = LOWER(?)", (name,), one=True
        ):
            flash("A category with this name already exists.", "danger")
        else:
            db.get_db().execute(
                "INSERT INTO categories (name, description, is_archived) VALUES (?, ?, 0)",
                (name, description),
            )
            _audit("ADD_CATEGORY", "category", name, description)
            flash("Category added.", "success")
        return redirect(url_for("admin.categories"))

    rows = db.get_db().query(
        """
        SELECT c.*, (SELECT COUNT(*) FROM listings l WHERE l.category_id = c.category_id)
               AS listing_count
        FROM categories c ORDER BY c.is_archived, c.name
        """
    )
    return render_template("admin/categories.html", categories=rows)


@bp.route("/categories/<int:category_id>/archive", methods=["POST"])
@admin_required
def archive_category(category_id):
    """Archive (hide) or restore a category."""
    target = db.get_db().query(
        "SELECT * FROM categories WHERE category_id = ?", (category_id,), one=True
    )
    if target is None:
        abort(404)
    new_value = 0 if target["is_archived"] else 1
    db.get_db().execute(
        "UPDATE categories SET is_archived = ? WHERE category_id = ?",
        (new_value, category_id),
    )
    _audit("ARCHIVE_CATEGORY" if new_value else "RESTORE_CATEGORY",
           "category", category_id, target["name"])
    flash(f"Category '{target['name']}' {'archived' if new_value else 'restored'}.", "success")
    return redirect(url_for("admin.categories"))


# ----------------------------------------------------------------------
# Logs: audit trail (BR-08) and the email notification log (FR-10)
# ----------------------------------------------------------------------
@bp.route("/logs")
@admin_required
def logs():
    db_conn = db.get_db()
    audit = db_conn.query(
        """
        SELECT a.*, u.first_name || ' ' || u.last_name AS admin_name
        FROM audit_log a JOIN users u ON u.user_id = a.admin_id
        ORDER BY a.audit_id DESC LIMIT 200
        """
    )
    emails = db_conn.query(
        "SELECT * FROM email_log ORDER BY email_id DESC LIMIT 200"
    )
    return render_template("admin/logs.html", audit=audit, emails=emails)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------
def _get_report(report_id):
    return db.get_db().query(
        """
        SELECT r.*, l.title AS listing_title, l.description AS listing_description,
               l.status AS listing_status, l.price AS listing_price,
               l.user_id AS seller_id,
               u.first_name || ' ' || u.last_name AS reporter_name, u.email AS reporter_email
        FROM reports r
        JOIN listings l ON l.listing_id = r.listing_id
        JOIN users u ON u.user_id = r.reporter_id
        WHERE r.report_id = ?
        """,
        (report_id,), one=True,
    )


def _audit(action, entity_type, entity_id, details):
    """Write an administrator action to the audit trail (BR-08)."""
    db.get_db().execute(
        "INSERT INTO audit_log (admin_id, action, entity_type, entity_id, details, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (current_user()["user_id"], action, entity_type, str(entity_id), details, now()),
    )


def _notify_reporter(report, outcome):
    """Tell the reporter that their report has been resolved (FR-10)."""
    send_notification_email(
        report["reporter_email"],
        f"Your report #{report['report_id']} has been {outcome}",
        f"Hi {report['reporter_name']},\n\nYour report about "
        f"\"{report['listing_title']}\" has been {outcome}.\n\n"
        "Thank you for helping keep the marketplace safe.\n",
    )
