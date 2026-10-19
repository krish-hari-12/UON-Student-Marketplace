"""Use cases UC-12/UC-13: reporting + administration (FR-11..14, BR-06..10)."""
from app import db


def test_student_can_report_listing(client, login_student, csrf):
    token = csrf("/listings/10/report")
    response = login_student.post("/listings/10/report", data={
        "_csrf": token, "reason": "Scam or fraud",
        "details": "The scooter price looks too good to be true."}, follow_redirects=True)
    assert b"submitted for review" in response.data


def test_short_report_details_rejected(client, login_student, csrf):
    token = csrf("/listings/10/report")
    response = login_student.post("/listings/10/report", data={
        "_csrf": token, "reason": "Other", "details": "bad"})
    assert response.status_code == 400


def test_duplicate_open_report_blocked(client, login_student, csrf):
    token = csrf("/listings/10/report")
    login_student.post("/listings/10/report", data={
        "_csrf": token, "reason": "Other", "details": "First report with details here."})
    response = login_student.post("/listings/10/report", data={
        "_csrf": token, "reason": "Other", "details": "Second duplicate report attempt."})
    assert response.status_code == 400
    assert b"already have an open report" in response.data


def test_student_cannot_access_admin(client, login_student):
    assert login_student.get("/admin/").status_code == 403
    assert login_student.get("/admin/users").status_code == 403
    assert login_student.get("/admin/reports").status_code == 403


def test_student_cannot_promote_self(client, app, login_student, csrf):
    # BR-09: role changes exist only behind admin-protected routes.
    with app.app_context():
        user_id = db.get_db().query(
            "SELECT user_id FROM users WHERE email = 'madhavi@uon.edu.au'", one=True
        )["user_id"]
    token = csrf("/listings/1")
    response = login_student.post(f"/admin/users/{user_id}/role", data={
        "_csrf": token, "role": "admin"})
    assert response.status_code == 403
    with app.app_context():
        role = db.get_db().query(
            "SELECT role FROM users WHERE user_id = ?", (user_id,), one=True)["role"]
    assert role == "student"


def test_admin_dashboard_and_reports_review(client, app, login_admin):
    assert b"Administration dashboard" in login_admin.get("/admin/").data
    page = login_admin.get("/admin/reports").get_data(as_text=True)
    assert "Safety concern" in page  # seeded open report


def test_admin_remove_listing_and_audit_trail(client, app, login_admin, csrf, login):
    token = csrf("/admin/reports")
    response = login_admin.post("/admin/reports/1", data={
        "_csrf": token, "action": "remove_listing", "note": "breach confirmed"})
    assert response.status_code == 302
    with app.app_context():
        status = db.get_db().query(
            "SELECT status FROM listings WHERE listing_id = 10", one=True)["status"]
        audit = db.get_db().query(
            "SELECT * FROM audit_log WHERE action = 'REMOVE_LISTING'", one=True)
    assert status == "removed"            # BR-07 action applied
    assert audit is not None              # BR-08: audited

    # BR-10: removed listings are invisible to normal users (404),
    # but remain reviewable by the administrator (who is logged in here).
    assert login_admin.get("/listings/10").status_code == 200   # admin review view
    login(client, "dhimanshi@uon.edu.au", "Student@123")        # switch to normal user
    assert client.get("/listings/10").status_code == 404


def test_admin_dismiss_report(client, app, login_admin, csrf):
    token = csrf("/admin/reports")
    response = login_admin.post("/admin/reports/2", data={
        "_csrf": token, "action": "dismiss", "note": "not a breach"})
    assert response.status_code == 302
    with app.app_context():
        status = db.get_db().query(
            "SELECT status FROM reports WHERE report_id = 2", one=True)["status"]
    assert status == "dismissed"


def test_admin_user_management(client, app, login_admin, csrf):
    token = csrf("/admin/users")
    response = login_admin.post("/admin/users/2/status", data={
        "_csrf": token, "status": "suspended"})
    assert response.status_code == 302
    with app.app_context():
        status = db.get_db().query(
            "SELECT status FROM users WHERE user_id = 2", one=True)["status"]
    assert status == "suspended"
    # restore for other tests' isolation (each test has a fresh DB anyway)
    login_admin.post("/admin/users/2/status", data={
        "_csrf": csrf("/admin/users"), "status": "active"})


def test_admin_category_management(client, app, login_admin, csrf):
    token = csrf("/admin/categories")
    response = login_admin.post("/admin/categories", data={
        "_csrf": token, "name": "Sports equipment", "description": "Balls, bats and gym gear"})
    assert response.status_code == 302
    page = login_admin.get("/admin/categories").get_data(as_text=True)
    assert "Sports equipment" in page
    # duplicates rejected
    response = login_admin.post("/admin/categories", data={
        "_csrf": csrf("/admin/categories"), "name": "Sports equipment", "description": ""})
    assert response.status_code == 302  # flash message, no duplicate row
    with app.app_context():
        n = db.get_db().query(
            "SELECT COUNT(*) AS n FROM categories WHERE name = 'Sports equipment'",
            one=True)["n"]
    assert n == 1
