"""
tests/conftest.py
=================
Shared pytest fixtures and helpers for the UoN Student Marketplace suite.

Every test runs against a FRESH temporary database (schema + seed data are
loaded exactly like a first production run) so tests are independent.
"""
import re

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    """Application instance wired to a throw-away database + upload folder."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    test_config = {
        "DB_BACKEND": "sqlite",
        "SQLITE_PATH": tmp_path / "test_marketplace.db",
        "UPLOAD_FOLDER": upload_dir,
        "SECRET_KEY": "test-secret-key",
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
    }
    application = create_app(test_config)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


# ----------------------------------------------------------------------
# Helper functions exposed to tests via fixtures
# ----------------------------------------------------------------------
def _csrf_token(client, path="/login"):
    """Fetch a page and extract its CSRF token from the first form."""
    html = client.get(path).get_data(as_text=True)
    match = re.search(r'name="_csrf" value="([^"]+)"', html)
    assert match, f"CSRF token not found on {path}"
    return match.group(1)


@pytest.fixture()
def csrf(client):
    return lambda path="/login": _csrf_token(client, path)


def _login(client, email, password):
    token = _csrf_token(client)
    return client.post("/login", data={
        "_csrf": token, "email": email, "password": password,
    })


@pytest.fixture()
def login(client):
    return _login


@pytest.fixture()
def login_student(client):
    """Log in as a normal student (Madhavi, user_id 2 in the seed data)."""
    response = _login(client, "madhavi@uon.edu.au", "Student@123")
    assert response.status_code == 302
    return client


@pytest.fixture()
def login_admin(client):
    """Log in as the seeded administrator (user_id 1)."""
    response = _login(client, "admin@uon.edu.au", "Admin@123")
    assert response.status_code == 302
    return client


@pytest.fixture()
def new_listing(login_student):
    """Create one valid listing for the logged-in student; return its id."""
    from re import search
    token = _csrf_token(login_student, "/listings/new")
    response = login_student.post("/listings/new", data={
        "_csrf": token,
        "title": "Test gaming chair",
        "description": "A comfortable gaming chair used for one year, all functions working.",
        "price": "88.50",
        "category_id": "1",
        "condition": "Good",
        "location": "Callaghan",
    })
    assert response.status_code == 302
    match = search(r"/listings/(\d+)", response.headers["Location"])
    return int(match.group(1))
