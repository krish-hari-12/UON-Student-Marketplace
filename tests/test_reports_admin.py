
"""
tests/test_reports_admin.py
===========================
Tests for student reporting and administrator functionality.

Covers report submission, report validation, administrator permissions,
listing moderation, user management, category management and audit logs.
"""

from app import db


def get_user(app, email):
    """Retrieve a user record using their email address."""
    with app.app_context():
        return db.get_db().query(
            "SELECT * FROM users WHERE email = ?",
            (email,),
            one=True,
        )


def get_report(app, report_id):
    """Retrieve a report record by its ID."""
    with app.app_context():
        return db.get_db().query(
            "SELECT * FROM reports WHERE report_id = ?",
            (report_id,),
            one=True,
        )


def get_listing(app, listing_id):
    """Retrieve a listing record by its ID."""
    with app.app_context():
        return db.get_db().query(
            "SELECT * FROM listings WHERE listing_id = ?",
            (listing_id,),
            one=True,
        )


def get_category(app, category_id):
    """Retrieve a category record by its ID."""
    with app.app_context():
        return db.get_db().query(
            "SELECT * FROM categories WHERE category_id = ?",
            (category_id,),
            one=True,
        )


def get_audit_count(app, action, entity_id=None):
    """Count audit records for an administrator action."""
    with app.app_context():
        if entity_id is None:
            result = db.get_db().query(
                "SELECT COUNT(*) AS total FROM audit_log WHERE action = ?",
                (action,),
                one=True,
            )
        else:
            result = db.get_db().query(
                """
                SELECT COUNT(*) AS total
                FROM audit_log
                WHERE action = ? AND entity_id = ?
                """,
                (action, str(entity_id)),
                one=True,
            )

        return result["total"]


# ---------------------------------------------------------
# Student listing reports
# ---------------------------------------------------------

def test_student_can_report_listing(client, login_student, csrf):
    """A student can submit a valid listing report."""
    token = csrf("/listings/10/report")

    response = login_student.post(
        "/listings/10/report",
        data={
            "_csrf": token,
            "reason": "Scam or fraud",
            "details": "The scooter price looks too good to be true.",
        },
        follow_redirects=True,
    )

    assert b"submitted for review" in response.data


def test_short_report_details_rejected(client, login_student, csrf):
    """Report details shorter than 10 characters are rejected."""
    token = csrf("/listings/10/report")

    response = login_student.post(
        "/listings/10/report",
        data={
            "_csrf": token,
            "reason": "Other",
            "details": "bad",
        },
    )

    assert response.status_code == 400


def test_invalid_report_reason_rejected(client, login_student, csrf):
    """A report must use one of the configured report reasons."""
    token = csrf("/listings/10/report")

    response = login_student.post(
        "/listings/10/report",
        data={
            "_csrf": token,
            "reason": "Invalid reason",
            "details": "This listing appears to contain misleading information.",
        },
    )

    assert response.status_code == 400


def test_duplicate_open_report_blocked(client, login_student, csrf):
    """A student cannot submit multiple open reports for one listing."""
    token = csrf("/listings/10/report")

    login_student.post(
        "/listings/10/report",
        data={
            "_csrf": token,
            "reason": "Other",
            "details": "First report with sufficient details.",
        },
    )

    response = login_student.post(
        "/listings/10/report",
        data={
            "_csrf": csrf("/listings/10/report"),
            "reason": "Other",
            "details": "Second duplicate report attempt.",
        },
    )

    assert response.status_code == 400
    assert b"already have an open report" in response.data


def test_removed_listing_cannot_be_reported(
    app, client, login_student, csrf
):
    """A removed listing cannot receive a new report."""
    with app.app_context():
        db.get_db().execute(
            "UPDATE listings SET status = 'removed' WHERE listing_id = ?",
            (10,),
        )

    token = csrf("/login")

    response = login_student.post(
        "/listings/10/report",
        data={
            "_csrf": token,
            "reason": "Other",
            "details": "This listing should no longer be reportable.",
        },
    )

    assert response.status_code == 404


def test_report_requires_login(client):
    """Unauthenticated visitors cannot submit listing reports."""
    response = client.get("/listings/10/report")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------
# Administrator access and permissions
# ---------------------------------------------------------

def test_student_cannot_access_admin(client, login_student):
    """Normal students cannot access administrator pages."""
    assert login_student.get("/admin/").status_code == 403
    assert login_student.get("/admin/users").status_code == 403
    assert login_student.get("/admin/reports").status_code == 403
    assert login_student.get("/admin/categories").status_code == 403


def test_student_cannot_change_own_role(
    app, client, login_student, csrf
):
    """A student cannot access the administrator role-management action."""
    student = get_user(app, "madhavi@uon.edu.au")
    student_id = student["user_id"]

    token = csrf("/profile")

    response = login_student.post(
        f"/admin/users/{student_id}/role",
        data={
            "_csrf": token,
            "role": "admin",
        },
    )

    assert response.status_code == 403

    updated_student = get_user(app, "madhavi@uon.edu.au")

    assert updated_student["role"] == "student"


def test_admin_cannot_suspend_own_account(
    app, client, login_admin, csrf
):
    """An administrator cannot suspend their own account."""
    admin = get_user(app, "admin@uon.edu.au")
    admin_id = admin["user_id"]

    token = csrf("/admin/users")

    response = login_admin.post(
        f"/admin/users/{admin_id}/status",
        data={
            "_csrf": token,
            "status": "suspended",
        },
    )

    assert response.status_code == 302

    updated_admin = get_user(app, "admin@uon.edu.au")

    assert updated_admin["status"] == "active"


def test_admin_cannot_change_own_role(
    app, login_admin, csrf
):
    """An administrator cannot demote or change their own role."""
    admin = get_user(app, "admin@uon.edu.au")
    admin_id = admin["user_id"]

    token = csrf("/admin/users")

    response = login_admin.post(
        f"/admin/users/{admin_id}/role",
        data={
            "_csrf": token,
            "role": "student",
        },
    )

    assert response.status_code == 302

    updated_admin = get_user(app, "admin@uon.edu.au")

    assert updated_admin["role"] == "admin"


def test_admin_dashboard_and_reports_review(
    client, login_admin
):
    """An administrator can view the dashboard and reports."""
    response = login_admin.get("/admin/")

    assert response.status_code == 200
    assert b"Administration dashboard" in response.data

    page = login_admin.get("/admin/reports").get_data(as_text=True)

    assert "Safety concern" in page


# ---------------------------------------------------------
# Report moderation
# ---------------------------------------------------------

def test_admin_archive_listing_and_audit_trail(
    app, login_admin, csrf
):
    """Archiving a reported listing resolves the report and records an audit."""
    token = csrf("/admin/reports")

    response = login_admin.post(
        "/admin/reports/1",
        data={
            "_csrf": token,
            "action": "archive_listing",
            "note": "Confirmed marketplace policy breach.",
        },
    )

    assert response.status_code == 302

    listing = get_listing(app, 10)
    report = get_report(app, 1)

    assert listing is not None
    assert listing["status"] == "archived"

    assert report["status"] == "resolved"
    assert report["resolution_note"] == (
        "Confirmed marketplace policy breach."
    )

    assert get_audit_count(
        app, "ARCHIVE_LISTING", 10
    ) >= 1


def test_archived_listing_is_not_deleted(app, login_admin, csrf):
    """Administrator moderation retains the listing in the database."""
    token = csrf("/admin/reports")

    response = login_admin.post(
        "/admin/reports/1",
        data={
            "_csrf": token,
            "action": "archive_listing",
            "note": "Archive for review.",
        },
    )

    assert response.status_code == 302

    listing = get_listing(app, 10)

    assert listing is not None
    assert listing["status"] == "archived"


def test_admin_dismiss_report(app, login_admin, csrf):
    """An administrator can dismiss a report."""
    token = csrf("/admin/reports")

    response = login_admin.post(
        "/admin/reports/2",
        data={
            "_csrf": token,
            "action": "dismiss",
            "note": "No breach found.",
        },
    )

    assert response.status_code == 302

    report = get_report(app, 2)

    assert report["status"] == "dismissed"
    assert report["resolution_note"] == "No breach found."

    assert get_audit_count(
        app, "DISMISS_REPORT", 2
    ) >= 1


def test_admin_can_mark_report_in_review(
    app, login_admin, csrf
):
    """An administrator can move a report into the in-review state."""
    token = csrf("/admin/reports")

    response = login_admin.post(
        "/admin/reports/1",
        data={
            "_csrf": token,
            "action": "in_review",
            "note": "Investigating the listing.",
        },
    )

    assert response.status_code == 302

    report = get_report(app, 1)

    assert report["status"] == "in_review"

    assert get_audit_count(
        app, "REVIEW_REPORT", 1
    ) >= 1


def test_invalid_report_action_rejected(
    login_admin, csrf
):
    """Unsupported administrator report actions return HTTP 400."""
    token = csrf("/admin/reports")

    response = login_admin.post(
        "/admin/reports/1",
        data={
            "_csrf": token,
            "action": "permanently_delete",
            "note": "Invalid action.",
        },
    )

    assert response.status_code == 400


# ---------------------------------------------------------
# User management
# ---------------------------------------------------------

def test_admin_can_suspend_and_reactivate_user(
    app, login_admin, csrf
):
    """An administrator can suspend and reactivate a student."""
    student = get_user(app, "madhavi@uon.edu.au")
    student_id = student["user_id"]

    token = csrf("/admin/users")

    response = login_admin.post(
        f"/admin/users/{student_id}/status",
        data={
            "_csrf": token,
            "status": "suspended",
        },
    )

    assert response.status_code == 302
    assert get_user(app, "madhavi@uon.edu.au")["status"] == "suspended"

    token = csrf("/admin/users")

    response = login_admin.post(
        f"/admin/users/{student_id}/status",
        data={
            "_csrf": token,
            "status": "active",
        },
    )

    assert response.status_code == 302
    assert get_user(app, "madhavi@uon.edu.au")["status"] == "active"

    assert get_audit_count(
        app, "SET_USER_STATUS", student_id
    ) >= 2


def test_invalid_user_status_rejected(
    app, login_admin, csrf
):
    """Only active and suspended are accepted account statuses."""
    student = get_user(app, "madhavi@uon.edu.au")

    token = csrf("/admin/users")

    response = login_admin.post(
        f"/admin/users/{student['user_id']}/status",
        data={
            "_csrf": token,
            "status": "deleted",
        },
    )

    assert response.status_code == 400

    assert get_user(app, "madhavi@uon.edu.au")["status"] == "active"


def test_admin_can_change_another_users_role(
    app, login_admin, csrf
):
    """An administrator can change another user's role."""
    student = get_user(app, "madhavi@uon.edu.au")
    student_id = student["user_id"]

    token = csrf("/admin/users")

    response = login_admin.post(
        f"/admin/users/{student_id}/role",
        data={
            "_csrf": token,
            "role": "admin",
        },
    )

    assert response.status_code == 302

    assert get_user(app, "madhavi@uon.edu.au")["role"] == "admin"

    assert get_audit_count(
        app, "SET_USER_ROLE", student_id
    ) >= 1


# ---------------------------------------------------------
# Listing moderation
# ---------------------------------------------------------

def test_admin_can_moderate_listing_status(
    app, login_admin, csrf
):
    """An administrator can archive, reactivate and mark a listing sold."""
    statuses = ["archived", "active", "sold"]

    for status in statuses:
        token = csrf("/admin/listings")

        response = login_admin.post(
            "/admin/listings/10/moderate",
            data={
                "_csrf": token,
                "status": status,
            },
        )

        assert response.status_code == 302
        assert get_listing(app, 10)["status"] == status

    assert get_audit_count(
        app, "MODERATE_LISTING", 10
    ) >= 3


def test_invalid_listing_moderation_status_rejected(
    app, login_admin, csrf
):
    """Unsupported listing statuses cannot be applied by administrators."""
    token = csrf("/admin/listings")

    response = login_admin.post(
        "/admin/listings/10/moderate",
        data={
            "_csrf": token,
            "status": "deleted",
        },
    )

    assert response.status_code == 400

    assert get_listing(app, 10)["status"] == "active"


# ---------------------------------------------------------
# Category management
# ---------------------------------------------------------

def test_admin_category_management(
    app, login_admin, csrf
):
    """An administrator can create a category and duplicate names are rejected."""
    token = csrf("/admin/categories")

    response = login_admin.post(
        "/admin/categories",
        data={
            "_csrf": token,
            "name": "Sports equipment",
            "description": "Balls, bats and gym gear",
        },
    )

    assert response.status_code == 302

    page = login_admin.get(
        "/admin/categories"
    ).get_data(as_text=True)

    assert "Sports equipment" in page

    # Attempt to create a duplicate category.
    token = csrf("/admin/categories")

    response = login_admin.post(
        "/admin/categories",
        data={
            "_csrf": token,
            "name": "Sports equipment",
            "description": "",
        },
    )

    assert response.status_code == 302

    with app.app_context():
        result = db.get_db().query(
            """
            SELECT COUNT(*) AS total
            FROM categories
            WHERE name = 'Sports equipment'
            """,
            one=True,
        )

    assert result["total"] == 1


def test_admin_can_archive_and_restore_category(
    app, login_admin, csrf
):
    """An administrator can archive and restore a category without deleting it."""
    with app.app_context():
        category = db.get_db().query(
            "SELECT category_id FROM categories LIMIT 1",
            one=True,
        )

    category_id = category["category_id"]

    token = csrf("/admin/categories")

    response = login_admin.post(
        f"/admin/categories/{category_id}/archive",
        data={"_csrf": token},
    )

    assert response.status_code == 302

    assert get_category(app, category_id)["is_archived"] == 1

    # The same route restores an already archived category.
    token = csrf("/admin/categories")

    response = login_admin.post(
        f"/admin/categories/{category_id}/archive",
        data={"_csrf": token},
    )

    assert response.status_code == 302

    restored = get_category(app, category_id)

    assert restored is not None
    assert restored["is_archived"] == 0

    assert get_audit_count(
        app, "ARCHIVE_CATEGORY", category_id
    ) >= 1

    assert get_audit_count(
        app, "RESTORE_CATEGORY", category_id
    ) >= 1


def test_admin_can_edit_category(app, login_admin, csrf):
    """An administrator can update an existing category."""
    with app.app_context():
        category = db.get_db().query(
            "SELECT category_id FROM categories LIMIT 1",
            one=True,
        )

    category_id = category["category_id"]

    token = csrf("/admin/categories")

    response = login_admin.post(
        f"/admin/categories/{category_id}/edit",
        data={
            "_csrf": token,
            "name": "Updated test category",
            "description": "Updated category description.",
        },
    )

    assert response.status_code == 302

    updated = get_category(app, category_id)

    assert updated["name"] == "Updated test category"
    assert updated["description"] == "Updated category description."

    assert get_audit_count(
        app, "EDIT_CATEGORY", category_id
    ) >= 1


def test_student_cannot_modify_category(client, login_student, csrf):
    """A student cannot create or archive marketplace categories."""
    token = csrf("/profile")

    response = login_student.post(
        "/admin/categories",
        data={
            "_csrf": token,
            "name": "Unauthorized category",
            "description": "Should not be created.",
        },
    )

    assert response.status_code == 403
