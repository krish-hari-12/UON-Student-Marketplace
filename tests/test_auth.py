
"""Tests for registration, email verification, authentication and profile management."""

from app import db


def test_registration_with_uon_email_succeeds(client, csrf, monkeypatch):
    """A valid UoN registration creates a pending account and sends an OTP."""
    captured = {}

    def fake_send_otp(email, otp, purpose="email verification"):
        captured["email"] = email
        captured["otp"] = otp
        return True

    monkeypatch.setattr("app.views.auth.send_otp_email", fake_send_otp)

    token = csrf("/register")
    response = client.post(
        "/register",
        data={
            "_csrf": token,
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@uon.edu.au",
            "password": "Password1",
            "confirm_password": "Password1",
            "phone": "+61 400 000 000",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/verify-registration")
    assert captured["email"] == "test.user@uon.edu.au"

    # The account must remain pending until the email address is verified.
    with client.application.app_context():
        pending = db.get_db().query(
            "SELECT * FROM pending_registrations WHERE email = ?",
            ("test.user@uon.edu.au",),
            one=True,
        )
        user = db.get_db().query(
            "SELECT user_id FROM users WHERE email = ?",
            ("test.user@uon.edu.au",),
            one=True,
        )

    assert pending is not None
    assert user is None


def test_registration_completes_after_valid_otp(client, csrf, monkeypatch):
    """A valid registration OTP creates an active student account."""
    captured = {}

    def fake_send_otp(email, otp, purpose="email verification"):
        captured["otp"] = otp
        return True

    monkeypatch.setattr("app.views.auth.send_otp_email", fake_send_otp)

    token = csrf("/register")
    response = client.post(
        "/register",
        data={
            "_csrf": token,
            "first_name": "Test",
            "last_name": "Student",
            "email": "verified.student@uon.edu.au",
            "password": "Password1",
            "confirm_password": "Password1",
            "phone": "",
        },
    )

    assert response.status_code == 302

    token = csrf("/verify-registration")
    response = client.post(
        "/verify-registration",
        data={
            "_csrf": token,
            "otp": captured["otp"],
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.application.app_context():
        user = db.get_db().query(
            """
            SELECT email, role, status
            FROM users
            WHERE email = ?
            """,
            ("verified.student@uon.edu.au",),
            one=True,
        )

        pending = db.get_db().query(
            "SELECT pending_id FROM pending_registrations WHERE email = ?",
            ("verified.student@uon.edu.au",),
            one=True,
        )

    assert user is not None
    assert user["role"] == "student"
    assert user["status"] == "active"
    assert pending is None


def test_registration_rejects_non_uon_email(client, csrf):
    """Registration must use an approved university email address."""
    token = csrf("/register")

    response = client.post(
        "/register",
        data={
            "_csrf": token,
            "first_name": "Test",
            "last_name": "User",
            "email": "test@gmail.com",
            "password": "Password1",
            "confirm_password": "Password1",
            "phone": "",
        },
    )

    assert response.status_code == 400
    assert b"approved UoN student email" in response.data


def test_registration_rejects_duplicate_email(client, csrf):
    """An existing account cannot register again with the same email."""
    token = csrf("/register")

    response = client.post(
        "/register",
        data={
            "_csrf": token,
            "first_name": "Madhavi",
            "last_name": "Again",
            "email": "madhavi@uon.edu.au",
            "password": "Password1",
            "confirm_password": "Password1",
            "phone": "",
        },
    )

    assert response.status_code == 400
    assert b"already exists" in response.data


def test_registration_rejects_short_password(client, csrf):
    """Registration rejects passwords below the configured minimum length."""
    token = csrf("/register")

    response = client.post(
        "/register",
        data={
            "_csrf": token,
            "first_name": "Test",
            "last_name": "User",
            "email": "short.pw@uon.edu.au",
            "password": "abc",
            "confirm_password": "abc",
            "phone": "",
        },
    )

    assert response.status_code == 400


def test_registration_rejects_invalid_otp(client, csrf, monkeypatch):
    """An incorrect OTP must not create a student account."""
    monkeypatch.setattr(
        "app.views.auth.send_otp_email",
        lambda email, otp, purpose="email verification": True,
    )

    token = csrf("/register")
    response = client.post(
        "/register",
        data={
            "_csrf": token,
            "first_name": "Test",
            "last_name": "Student",
            "email": "invalid.otp@uon.edu.au",
            "password": "Password1",
            "confirm_password": "Password1",
            "phone": "",
        },
    )

    assert response.status_code == 302

    token = csrf("/verify-registration")
    response = client.post(
        "/verify-registration",
        data={"_csrf": token, "otp": "000000"},
    )

    assert response.status_code == 400

    with client.application.app_context():
        user = db.get_db().query(
            "SELECT user_id FROM users WHERE email = ?",
            ("invalid.otp@uon.edu.au",),
            one=True,
        )

    assert user is None


def test_login_success(client, login):
    """An active student can log in with valid credentials."""
    response = login(client, "madhavi@uon.edu.au", "Student@123")

    assert response.status_code == 302


def test_login_wrong_password_rejected(client, login):
    """An incorrect password must not authenticate the user."""
    response = login(client, "madhavi@uon.edu.au", "WrongPassword")

    assert response.status_code == 401
    assert b"Invalid email or password" in response.data


def test_suspended_account_cannot_log_in(client, app, login):
    """Suspended accounts must not be allowed to log in."""
    with app.app_context():
        db.get_db().execute(
            """
            UPDATE users
            SET status = 'suspended'
            WHERE email = ?
            """,
            ("sankeerth@uon.edu.au",),
        )

    response = login(client, "sankeerth@uon.edu.au", "Student@123")

    assert response.status_code == 403
    assert b"suspended" in response.data


def test_logout_clears_session(client, login_student, csrf):
    """Logging out ends the session and protects the logout request with CSRF."""
    token = csrf("/profile")

    response = client.post(
        "/logout",
        data={"_csrf": token},
    )

    assert response.status_code == 302

    profile = client.get("/profile", follow_redirects=False)
    assert profile.status_code == 302


def test_profile_page_requires_login(client):
    """Unauthenticated visitors cannot access profile information."""
    response = client.get("/profile")

    assert response.status_code == 302


def test_profile_update(client, login_student, csrf):
    """A student can update their own profile information."""
    token = csrf("/profile")

    response = login_student.post(
        "/profile",
        data={
            "_csrf": token,
            "first_name": "Madhavi",
            "last_name": "Latha",
            "phone": "+61 499 888 777",
        },
    )

    assert response.status_code == 302

    with login_student.application.app_context():
        user = db.get_db().query(
            """
            SELECT first_name, last_name, phone
            FROM users
            WHERE email = ?
            """,
            ("madhavi@uon.edu.au",),
            one=True,
        )

    assert user["first_name"] == "Madhavi"
    assert user["last_name"] == "Latha"
    assert user["phone"] == "+61 499 888 777"


def test_password_change_rejects_wrong_current_password(
    login_student, csrf
):
    """A password cannot be changed without the correct current password."""
    token = csrf("/profile")

    response = login_student.post(
        "/profile/password",
        data={
            "_csrf": token,
            "current_password": "WrongPassword",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123",
        },
        follow_redirects=True,
    )

    assert b"current password is incorrect" in response.data


def test_password_change_success(login_student, csrf, login):
    """A student can change their password after verifying the current one."""
    token = csrf("/profile")

    response = login_student.post(
        "/profile/password",
        data={
            "_csrf": token,
            "current_password": "Student@123",
            "new_password": "NewPass123",
            "confirm_password": "NewPass123",
        },
        follow_redirects=True,
    )

    assert b"Password changed successfully" in response.data

    # Verify that the new password works for a fresh login.
    login_response = login(
        login_student,
        "madhavi@uon.edu.au",
        "NewPass123",
    )

    assert login_response.status_code == 302


def test_forgot_password_rejects_unknown_email(client, csrf):
    """Password reset requests must use an existing registered account."""
    token = csrf("/forgot-password")

    response = client.post(
        "/forgot-password",
        data={
            "_csrf": token,
            "email": "unknown@uon.edu.au",
        },
    )

    assert response.status_code == 404
    assert b"No account exists" in response.data


def test_password_reset_with_valid_otp(
    client, csrf, monkeypatch
):
    """A verified password-reset OTP allows the student to set a new password."""
    captured = {}

    def fake_send_otp(email, otp, purpose="email verification"):
        captured["otp"] = otp
        return True

    monkeypatch.setattr("app.views.auth.send_otp_email", fake_send_otp)

    token = csrf("/forgot-password")
    response = client.post(
        "/forgot-password",
        data={
            "_csrf": token,
            "email": "madhavi@uon.edu.au",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/verify-reset-otp")

    token = csrf("/verify-reset-otp")
    response = client.post(
        "/verify-reset-otp",
        data={
            "_csrf": token,
            "otp": captured["otp"],
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/reset-password")

    token = csrf("/reset-password")
    response = client.post(
        "/reset-password",
        data={
            "_csrf": token,
            "password": "ResetPass123",
            "confirm_password": "ResetPass123",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    login_response = client.post(
        "/login",
        data={
            "_csrf": csrf("/login"),
            "email": "madhavi@uon.edu.au",
            "password": "ResetPass123",
        },
    )

    assert login_response.status_code == 302


def test_password_reset_rejects_invalid_otp(
    client, csrf, monkeypatch
):
    """An incorrect password-reset OTP must not allow a password change."""
    monkeypatch.setattr(
        "app.views.auth.send_otp_email",
        lambda email, otp, purpose="email verification": True,
    )

    token = csrf("/forgot-password")
    response = client.post(
        "/forgot-password",
        data={
            "_csrf": token,
            "email": "madhavi@uon.edu.au",
        },
    )

    assert response.status_code == 302

    token = csrf("/verify-reset-otp")
    response = client.post(
        "/verify-reset-otp",
        data={
            "_csrf": token,
            "otp": "000000",
        },
    )

    assert response.status_code == 400
    assert b"Invalid or expired verification code" in response.data
