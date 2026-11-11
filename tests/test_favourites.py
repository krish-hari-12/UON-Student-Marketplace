
"""
tests/test_favourites.py
========================
Tests for saving and removing marketplace favourites.

Covers login protection, adding and removing favourites,
user-specific visibility, duplicate prevention and invalid listings.
"""

from app import db
from app.db import now


def get_favourite_count(app, user_id, listing_id):
    """Return the number of saved records for a user and listing."""
    with app.app_context():
        result = db.get_db().query(
            """
            SELECT COUNT(*) AS total
            FROM favourites
            WHERE user_id = ? AND listing_id = ?
            """,
            (user_id, listing_id),
            one=True,
        )

        return result["total"]


def get_user_id(app, email):
    """Retrieve a user's database ID using their email address."""
    with app.app_context():
        user = db.get_db().query(
            "SELECT user_id FROM users WHERE email = ?",
            (email,),
            one=True,
        )

        assert user is not None, f"Test user {email} was not found."
        return user["user_id"]


def test_favourite_requires_login(client):
    """Visitors cannot access or modify favourites without logging in."""
    response = client.post("/listings/1/favourite")

    # The CSRF guard rejects a POST without a valid token.
    assert response.status_code == 400

    assert client.get("/favourites").status_code == 302


def test_toggle_adds_then_removes(client, login_student, csrf):
    """A student can add a listing to favourites and remove it again."""
    token = csrf("/listings/1")

    response = login_student.post(
        "/listings/1/favourite",
        data={
            "_csrf": token,
            "next": "/favourites",
        },
        follow_redirects=True,
    )

    assert b"Saved to favourites" in response.data

    page = login_student.get("/favourites").get_data(as_text=True)
    assert "STAT1070" in page

    token = csrf("/listings/1")

    response = login_student.post(
        "/listings/1/favourite",
        data={
            "_csrf": token,
            "next": "/favourites",
        },
        follow_redirects=True,
    )

    assert b"Removed from favourites" in response.data

    page = login_student.get("/favourites").get_data(as_text=True)
    assert "STAT1070" not in page


def test_seed_favourites_visible(client, login_student):
    """The student's existing seeded favourites are displayed."""
    page = login_student.get("/favourites").get_data(as_text=True)

    assert "HP laptop" in page
    assert "27-inch monitor" in page


def test_favourite_is_saved_only_once(app, client, login_student, csrf):
    """Adding a favourite creates one database record."""
    token = csrf("/listings/1")

    response = login_student.post(
        "/listings/1/favourite",
        data={
            "_csrf": token,
            "next": "/favourites",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    user_id = get_user_id(app, "madhavi@uon.edu.au")

    count = get_favourite_count(app, user_id, 1)

    assert count == 1


def test_favourites_are_private_to_each_user(
    app, client, login_student
):
    """A student cannot see another user's saved favourites."""
    student_id = get_user_id(app, "madhavi@uon.edu.au")

    # Select another seeded account.
    with app.app_context():
        other_user = db.get_db().query(
            """
            SELECT user_id
            FROM users
            WHERE user_id != ?
            LIMIT 1
            """,
            (student_id,),
            one=True,
        )

        assert other_user is not None, "A second test user is required."

        # Save listing 1 for the other user only.
        db.get_db().execute(
            """
            INSERT INTO favourites (user_id, listing_id, created_at)
            VALUES (?, ?, ?)
            """,
            (other_user["user_id"], 1, now()),
        )

    # Madhavi should not see another user's saved listing.
    page = login_student.get("/favourites").get_data(as_text=True)

    assert "STAT1070" not in page


def test_nonexistent_listing_cannot_be_favourited(client, login_student, csrf):
    """Trying to favourite a listing that does not exist returns 404."""
    token = csrf("/login")

    response = login_student.post(
        "/listings/999999/favourite",
        data={
            "_csrf": token,
            "next": "/favourites",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_removing_favourite_does_not_delete_listing(
    app, login_student, csrf
):
    """Removing a favourite must not delete the marketplace listing."""
    token = csrf("/listings/1")

    response = login_student.post(
        "/listings/1/favourite",
        data={
            "_csrf": token,
            "next": "/favourites",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Toggle again to remove the favourite association.
    token = csrf("/listings/1")

    response = login_student.post(
        "/listings/1/favourite",
        data={
            "_csrf": token,
            "next": "/favourites",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # The original listing must remain in the database.
    with app.app_context():
        listing = db.get_db().query(
            "SELECT listing_id FROM listings WHERE listing_id = ?",
            (1,),
            one=True,
        )

    assert listing is not None
