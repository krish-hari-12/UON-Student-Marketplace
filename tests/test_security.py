
"""Security-focused tests: CSRF, password storage, injection and open redirect."""

import re

from app import db


def test_post_without_csrf_token_rejected(client):
    response = client.post(
        "/login",
        data={
            "email": "x@uon.edu.au",
            "password": "y",
        },
    )

    assert response.status_code == 400


def test_passwords_are_never_stored_in_plain_text(client, app):
    with app.app_context():
        row = db.get_db().query(
            "SELECT password_hash FROM users WHERE email = ?",
            ("madhavi@uon.edu.au",),
            one=True,
        )

    assert row is not None
    assert row["password_hash"].startswith(("pbkdf2:", "scrypt:"))
    assert "Student@123" not in row["password_hash"]


def test_sql_injection_in_search_is_safe(client):
    payload = "' OR 1=1 --"

    response = client.get(
        "/listings",
        query_string={"q": payload},
    )

    assert response.status_code == 200
    assert "No listings match" in response.get_data(as_text=True)


def test_open_redirect_blocked(client, csrf):
    token = csrf("/login")

    response = client.post(
        "/login?next=//evil.example.com",
        data={
            "_csrf": token,
            "email": "madhavi@uon.edu.au",
            "password": "Student@123",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/")
    assert "evil.example.com" not in response.headers["Location"]


def test_csrf_token_rotates_on_login(client, csrf):
    # Get the CSRF token before authentication.
    token_before_login = csrf("/login")

    assert re.fullmatch(r"[0-9a-f]{64}", token_before_login)

    # Log in using the existing token.
    response = client.post(
        "/login",
        data={
            "_csrf": token_before_login,
            "email": "madhavi@uon.edu.au",
            "password": "Student@123",
        },
    )

    assert response.status_code == 302

    # Login clears the previous session token.
    with client.session_transaction() as session:
        assert "user_id" in session
        assert "_csrf_token" not in session

    # A new token should be generated on the authenticated page.
    token_after_login = csrf("/profile")

    assert re.fullmatch(r"[0-9a-f]{64}", token_after_login)
    assert token_before_login != token_after_login
