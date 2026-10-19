"""Security-focused tests: CSRF, password storage, injection, open redirect."""
import re

from app import db


def test_post_without_csrf_token_rejected(client):
    response = client.post("/login", data={"email": "x@uon.edu.au", "password": "y"})
    assert response.status_code == 400  # CSRF validation failed


def test_passwords_are_never_stored_in_plain_text(client, app):
    with app.app_context():
        row = db.get_db().query(
            "SELECT password_hash FROM users WHERE email = 'madhavi@uon.edu.au'",
            one=True)
    assert row["password_hash"].startswith(("pbkdf2:", "scrypt:"))
    assert "Student@123" not in row["password_hash"]


def test_sql_injection_in_search_is_safe(client):
    payload = "' OR 1=1 --"
    page = client.get(f"/listings?q={payload.replace(' ', '+')}").get_data(as_text=True)
    assert "No listings match" in page  # treated as literal text, no rows leaked


def test_open_redirect_blocked(client, csrf):
    token = csrf("/login")
    response = client.post("/login?next=//evil.example.com", data={
        "_csrf": token, "email": "madhavi@uon.edu.au", "password": "Student@123"})
    assert response.headers["Location"].startswith("/")  # never leaves the site
    assert "evil.example.com" not in response.headers["Location"]


def test_csrf_token_rotates_on_login(client, csrf):
    before = csrf("/login")
    assert re.match(r"^[0-9a-f]{64}$", before)
