
"""
tests/test_profile.py
=====================
Tests for student profile-photo management.

Covers photo uploads, replacements, validation, resetting to the
default avatar and access restrictions.
"""

import re
from io import BytesIO
from pathlib import Path

from app import db


def get_student(app):
    """Retrieve the seeded student's profile-photo information."""
    with app.app_context():
        return db.get_db().query(
            """
            SELECT user_id, email, profile_photo
            FROM users
            WHERE email = ?
            """,
            ("madhavi@uon.edu.au",),
            one=True,
        )


def get_csrf_token(client, path="/login"):
    """Retrieve a CSRF token from a page accessible to the visitor."""
    response = client.get(path)

    assert response.status_code == 200, (
        f"Could not load {path}. "
        f"Received status code {response.status_code}."
    )

    match = re.search(
        r'name="_csrf"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )

    assert match, f"CSRF token not found on {path}."
    return match.group(1)


def upload_photo(client, filename="avatar.png", content=None):
    """Submit a profile-photo upload."""
    if content is None:
        content = b"\x89PNG\r\n\x1a\nTest profile image"

    token = get_csrf_token(client, "/profile")

    return client.post(
        "/profile/photo",
        data={
            "_csrf": token,
            "profile_photo": (BytesIO(content), filename),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )


def test_profile_photo_upload_success(app, login_student):
    """A student can upload a supported profile photo."""
    response = upload_photo(login_student)

    assert response.status_code == 302

    user = get_student(app)

    assert user["profile_photo"] is not None
    assert user["profile_photo"].endswith(".png")

    photo_path = (
        Path(app.config["PROFILE_UPLOAD_FOLDER"])
        / user["profile_photo"]
    )

    assert photo_path.is_file()


def test_profile_photo_replacement_success(app, login_student):
    """Uploading a new photo replaces the previous photo."""
    first_response = upload_photo(
        login_student,
        filename="first.png",
        content=b"First profile image",
    )

    assert first_response.status_code == 302

    user_before = get_student(app)
    old_filename = user_before["profile_photo"]

    old_photo_path = (
        Path(app.config["PROFILE_UPLOAD_FOLDER"])
        / old_filename
    )

    assert old_photo_path.is_file()

    second_response = upload_photo(
        login_student,
        filename="second.jpg",
        content=b"Second profile image",
    )

    assert second_response.status_code == 302

    user_after = get_student(app)
    new_filename = user_after["profile_photo"]

    assert new_filename != old_filename
    assert new_filename.endswith(".jpg")

    new_photo_path = (
        Path(app.config["PROFILE_UPLOAD_FOLDER"])
        / new_filename
    )

    assert new_photo_path.is_file()
    assert not old_photo_path.exists()


def test_profile_photo_invalid_extension_rejected(app, login_student):
    """Unsupported file extensions must not be saved."""
    response = upload_photo(
        login_student,
        filename="document.pdf",
        content=b"Not an image",
    )

    assert response.status_code == 302

    user = get_student(app)

    assert user["profile_photo"] is None


def test_profile_photo_over_5mb_rejected(app, login_student):
    """Profile photos larger than the configured limit are rejected."""
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = upload_photo(
        login_student,
        filename="large.png",
        content=oversized_content,
    )

    assert response.status_code == 302

    user = get_student(app)

    assert user["profile_photo"] is None


def test_profile_photo_missing_file_rejected(app, login_student):
    """The upload route handles a submission without a selected file."""
    token = get_csrf_token(login_student, "/profile")

    response = login_student.post(
        "/profile/photo",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert response.status_code == 302

    user = get_student(app)

    assert user["profile_photo"] is None


def test_profile_photo_reset_to_default(app, login_student):
    """A student can reset an uploaded photo to the default avatar."""
    upload_response = upload_photo(
        login_student,
        filename="avatar.png",
        content=b"Test profile image",
    )

    assert upload_response.status_code == 302

    user_before = get_student(app)
    old_filename = user_before["profile_photo"]

    old_photo_path = (
        Path(app.config["PROFILE_UPLOAD_FOLDER"])
        / old_filename
    )

    assert old_photo_path.is_file()

    token = get_csrf_token(login_student, "/profile")

    response = login_student.post(
        "/profile/photo/default",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert response.status_code == 302

    user_after = get_student(app)

    assert user_after["profile_photo"] is None
    assert not old_photo_path.exists()


def test_uploaded_profile_photo_can_be_accessed(app, login_student):
    """An uploaded profile photo can be retrieved through its file route."""
    upload_response = upload_photo(
        login_student,
        filename="avatar.png",
        content=b"Test profile image",
    )

    assert upload_response.status_code == 302

    user = get_student(app)
    filename = user["profile_photo"]

    response = login_student.get(
        f"/profile/photos/{filename}"
    )

    assert response.status_code == 200
    assert response.data == b"Test profile image"


def test_unauthenticated_user_cannot_upload_profile_photo(client):
    """A visitor must log in before uploading a profile photo."""
    token = get_csrf_token(client, "/login")

    response = client.post(
        "/profile/photo",
        data={
            "_csrf": token,
            "profile_photo": (
                BytesIO(b"Test image"),
                "avatar.png",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_user_cannot_reset_profile_photo(client):
    """A visitor must log in before resetting a profile photo."""
    token = get_csrf_token(client, "/login")

    response = client.post(
        "/profile/photo/default",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
