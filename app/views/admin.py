
#Administrator dashboard, user management and marketplace moderation.

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app import db
from app.db import now
from app.emailer import send_notification_email
from app.security import admin_required, current_user

bp = Blueprint("admin", __name__)

# Dashboard

# Display platform statistics and recent activity."""
@bp.route("/")
@admin_required
def dashboard():
    db_conn = db.get_db()

    stats = {
        "users": db_conn.query(
            "SELECT COUNT(*) AS n FROM users", one=True
        )["n"],
        "listings": db_conn.query(
            "SELECT COUNT(*) AS n FROM listings WHERE status = 'active'",
            one=True,
        )["n"],
        "open_reports": db_conn.query(
            "SELECT COUNT(*) AS n FROM reports WHERE status = 'open'",
            one=True,
        )["n"],
        "messages": db_conn.query(
            "SELECT COUNT(*) AS n FROM messages", one=True
        )["n"],
    }

    recent_reports = db_conn.query(
        """
        SELECT r.*, l.title AS listing_title
        FROM reports r
        JOIN listings l ON l.listing_id = r.listing_id
        WHERE r.status = 'open'
        ORDER BY r.created_at DESC
        LIMIT 5
        """
    )

    recent_audit = db_conn.query(
        """
        SELECT a.*, u.first_name || ' ' || u.last_name AS admin_name
        FROM audit_log a
        JOIN users u ON u.user_id = a.admin_id
        ORDER BY a.audit_id DESC
        LIMIT 8
        """
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_reports=recent_reports,
        recent_audit=recent_audit,
    )


# Report management
# Display listing reports and their current status.
@bp.route("/reports")
@admin_required
def reports():
    status = request.args.get("status", "")
    params = []
    where = "1=1"

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
        ORDER BY CASE r.status
            WHEN 'open' THEN 0
            WHEN 'in_review' THEN 1
            ELSE 2
        END, r.created_at DESC
        """,
        params,
    )

    return render_template("admin/reports.html", reports=rows, status=status)

#Review a report and update its status.
@bp.route("/reports/<int:report_id>", methods=["GET", "POST"])
@admin_required
def report_detail(report_id):
    db_conn = db.get_db()
    report = _get_report(report_id)

    if report is None:
        abort(404)

    if request.method == "POST":
        action = request.form.get("action", "")
        note = (request.form.get("note") or "").strip()[:500]
        admin_id = current_user()["user_id"]

        if action == "archive_listing":
            # Archive the reported listing without deleting it.
            db_conn.execute(
                """
                UPDATE listings
                SET status = 'archived', updated_at = ?
                WHERE listing_id = ?
                """,
                (now(), report["listing_id"]),
            )

            db_conn.execute(
                """
                UPDATE reports
                SET status = 'resolved', resolved_by = ?,
                    resolved_at = ?, resolution_note = ?
                WHERE report_id = ?
                """,
                (admin_id, now(), note or "Listing archived", report_id),
            )

            _audit(
                "ARCHIVE_LISTING",
                "listing",
                report["listing_id"],
                f"Archived listing for report #{report_id}: {note}",
            )
            _notify_reporter(report, "resolved - the listing was archived")
            flash("Listing archived and report resolved.", "success")

        elif action == "dismiss":
            db_conn.execute(
                """
                UPDATE reports
                SET status = 'dismissed', resolved_by = ?,
                    resolved_at = ?, resolution_note = ?
                WHERE report_id = ?
                """,
                (admin_id, now(), note or "No breach found", report_id),
            )

            _audit("DISMISS_REPORT", "report", report_id, note)
            flash("Report dismissed.", "info")

        elif action == "in_review":
            db_conn.execute(
                "UPDATE reports SET status = 'in_review' WHERE report_id = ?",
                (report_id,),
            )

            _audit("REVIEW_REPORT", "report", report_id, note)
            flash("Report marked as under review.", "info")

        else:
            abort(400)

        return redirect(url_for("admin.report_detail", report_id=report_id))

    return render_template("admin/report_detail.html", report=report)


# User management

#Display registered users and their listing counts.
@bp.route("/users")
@admin_required
def users():
    rows = db.get_db().query(
        """
        SELECT u.*,
               (SELECT COUNT(*) FROM listings l
                WHERE l.user_id = u.user_id) AS listing_count
        FROM users u
        ORDER BY u.user_id
        """
    )

    return render_template("admin/users.html", users=rows)

#Suspend or reactivate a user account.
@bp.route("/users/<int:user_id>/status", methods=["POST"])
@admin_required
def set_user_status(user_id):
    new_status = request.form.get("status", "")

    if new_status not in ("active", "suspended"):
        abort(400)

    if user_id == current_user()["user_id"]:
        flash("You cannot change the status of your own account.", "warning")
        return redirect(url_for("admin.users"))

    db_conn = db.get_db()
    target = db_conn.query(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
        one=True,
    )

    if target is None:
        abort(404)

    old_status = target["status"]

    db_conn.execute(
        "UPDATE users SET status = ? WHERE user_id = ?",
        (new_status, user_id),
    )

    _audit(
        "SET_USER_STATUS",
        "user",
        user_id,
        f"status -> {new_status}",
    )

    # Email the user when their account is newly suspended.
    if new_status == "suspended" and old_status != "suspended":
        subject = "Your UON Student Marketplace Account Has Been Suspended"

        message = (
            f"Hello {target['first_name']},\n\n"
            "Your UON Student Marketplace account has been suspended "
            "by an administrator.\n\n"
            "You will not be able to log in or use marketplace features "
            "while your account is suspended.\n\n"
            "If you believe this suspension was made in error or need "
            "further information, please reply to this email for assistance.\n\n"
            "Regards,\n"
            "UON Student Marketplace Team"
        )

        email_sent = send_notification_email(
            target["email"],
            subject,
            message,
        )

        if email_sent:
            flash(
                f"Account suspended and notification email sent to {target['email']}.",
                "success",
            )
        else:
            flash(
                "Account suspended, but the notification email could not be sent.",
                "warning",
            )
    else:
        flash(
            f"Account {target['email']} is now {new_status}.",
            "success",
        )

    return redirect(url_for("admin.users"))

# Change a user's account role.
@bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def set_user_role(user_id):
    new_role = request.form.get("role", "")

    if new_role not in ("student", "admin"):
        abort(400)

    if user_id == current_user()["user_id"]:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.users"))

    db_conn = db.get_db()
    target = db_conn.query(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
        one=True,
    )

    if target is None:
        abort(404)

    db_conn.execute(
        "UPDATE users SET role = ? WHERE user_id = ?",
        (new_role, user_id),
    )

    _audit("SET_USER_ROLE", "user", user_id, f"role -> {new_role}")
    flash(f"Role for {target['email']} set to {new_role}.", "success")

    return redirect(url_for("admin.users"))


# Listing management

# Display the listings with search and status filters.
@bp.route("/listings")
@admin_required
def listings():
    q = (request.args.get("q") or "").strip()
    status = request.args.get("status", "")
    where = ["1=1"]
    params = []

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

    return render_template(
        "admin/listings.html",
        listings=rows,
        q=q,
        status=status,
    )

# Change a listing's status as an administrator.
@bp.route("/listings/<int:listing_id>/moderate", methods=["POST"])
@admin_required
def moderate_listing(listing_id):
    new_status = request.form.get("status", "")

    if new_status not in ("active", "archived", "sold"):
        abort(400)

    db_conn = db.get_db()
    listing = db_conn.query(
        "SELECT * FROM listings WHERE listing_id = ?",
        (listing_id,),
        one=True,
    )

    if listing is None:
        abort(404)

    db_conn.execute(
        """
        UPDATE listings
        SET status = ?, updated_at = ?
        WHERE listing_id = ?
        """,
        (new_status, now(), listing_id),
    )

    _audit(
        "MODERATE_LISTING",
        "listing",
        listing_id,
        f"status -> {new_status}",
    )

    flash(f"Listing \"{listing['title']}\" is now {new_status}.", "success")
    return redirect(url_for("admin.listings"))


# Category management

# Add and display listing categories.
@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    db_conn = db.get_db()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()[:200]

        if not (2 <= len(name) <= 50):
            flash("Category name must be 2-50 characters.", "danger")
        elif db_conn.query(
            "SELECT 1 AS x FROM categories WHERE LOWER(name) = LOWER(?)",
            (name,),
            one=True,
        ):
            flash("A category with this name already exists.", "danger")
        else:
            db_conn.execute(
                """
                INSERT INTO categories (name, description, is_archived)
                VALUES (?, ?, 0)
                """,
                (name, description),
            )

            _audit("ADD_CATEGORY", "category", name, description)
            flash("Category added.", "success")

        return redirect(url_for("admin.categories"))

    rows = db_conn.query(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM listings l
                WHERE l.category_id = c.category_id) AS listing_count
        FROM categories c
        ORDER BY c.is_archived, c.name
        """
    )

    return render_template("admin/categories.html", categories=rows)

#Archive or restore a category.
@bp.route("/categories/<int:category_id>/archive", methods=["POST"])
@admin_required
def archive_category(category_id):
    db_conn = db.get_db()
    target = db_conn.query(
        "SELECT * FROM categories WHERE category_id = ?",
        (category_id,),
        one=True,
    )

    if target is None:
        abort(404)

    new_value = 0 if target["is_archived"] else 1

    db_conn.execute(
        "UPDATE categories SET is_archived = ? WHERE category_id = ?",
        (new_value, category_id),
    )

    _audit(
        "ARCHIVE_CATEGORY" if new_value else "RESTORE_CATEGORY",
        "category",
        category_id,
        target["name"],
    )

    flash(
        f"Category '{target['name']}' "
        f"{'archived' if new_value else 'restored'}.",
        "success",
    )

    return redirect(url_for("admin.categories"))

# Edit a category's name and description.
@bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category(category_id):
    db_conn = db.get_db()
    category = db_conn.query(
        "SELECT * FROM categories WHERE category_id = ?",
        (category_id,),
        one=True,
    )

    if category is None:
        abort(404)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()[:200]

        if not (2 <= len(name) <= 50):
            flash("Category name must be 2-50 characters.", "danger")

        elif db_conn.query(
            """
            SELECT 1 AS x
            FROM categories
            WHERE LOWER(name) = LOWER(?)
            AND category_id != ?
            """,
            (name, category_id),
            one=True,
        ):
            flash("A category with this name already exists.", "danger")

        else:
            db_conn.execute(
                """
                UPDATE categories
                SET name = ?, description = ?
                WHERE category_id = ?
                """,
                (name, description, category_id),
            )

            _audit(
                "EDIT_CATEGORY",
                "category",
                category_id,
                f"Updated category name to {name}",
            )

            flash("Category updated successfully.", "success")
            return redirect(url_for("admin.categories"))

    return render_template("admin/edit_category.html", category=category)


# Audit and email logs

# Display administrator actions and email records.
@bp.route("/logs")
@admin_required
def logs():
    db_conn = db.get_db()

    audit = db_conn.query(
        """
        SELECT a.*, u.first_name || ' ' || u.last_name AS admin_name
        FROM audit_log a
        JOIN users u ON u.user_id = a.admin_id
        ORDER BY a.audit_id DESC
        LIMIT 200
        """
    )

    emails = db_conn.query(
        "SELECT * FROM email_log ORDER BY email_id DESC LIMIT 200"
    )

    return render_template("admin/logs.html", audit=audit, emails=emails)


#Fetch a report with its listing and reporter details.
def _get_report(report_id):
    return db.get_db().query(
        """
        SELECT r.*, l.title AS listing_title,
               l.description AS listing_description,
               l.status AS listing_status, l.price AS listing_price,
               l.user_id AS seller_id,
               u.first_name || ' ' || u.last_name AS reporter_name,
               u.email AS reporter_email
        FROM reports r
        JOIN listings l ON l.listing_id = r.listing_id
        JOIN users u ON u.user_id = r.reporter_id
        WHERE r.report_id = ?
        """,
        (report_id,),
        one=True,
    )

# Save an administrator action in the audit log.
def _audit(action, entity_type, entity_id, details):
    db.get_db().execute(
        """
        INSERT INTO audit_log
            (admin_id, action, entity_type, entity_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            current_user()["user_id"],
            action,
            entity_type,
            str(entity_id),
            details,
            now(),
        ),
    )

# Email the reporter when their report is resolved.
def _notify_reporter(report, outcome):
    send_notification_email(
        report["reporter_email"],
        f"Your report #{report['report_id']} has been {outcome}",
        f"Hi {report['reporter_name']},\n\n"
        f"Your report about \"{report['listing_title']}\" has been {outcome}.\n\n"
        "Thank you for helping keep the marketplace safe.\n",
    )
