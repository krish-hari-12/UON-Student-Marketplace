
"""
tests/test_messaging.py
=======================
Tests for buyer-seller messaging.

Covers conversation creation, participant permissions, message
validation, conversation reuse, inbox access and message history.
"""

from app import db


def get_conversation_count(app, listing_id, buyer_id):
    """Count conversations for a particular buyer and listing."""
    with app.app_context():
        result = db.get_db().query(
            """
            SELECT COUNT(*) AS total
            FROM conversations
            WHERE listing_id = ? AND buyer_id = ?
            """,
            (listing_id, buyer_id),
            one=True,
        )

        return result["total"]


def get_user_id(app, email):
    """Retrieve a user's database ID."""
    with app.app_context():
        user = db.get_db().query(
            "SELECT user_id FROM users WHERE email = ?",
            (email,),
            one=True,
        )

        assert user is not None
        return user["user_id"]


def test_contact_creates_conversation(client, login_student, csrf):
    """Contacting an active listing creates a conversation."""
    token = csrf("/listings/3")

    response = login_student.post(
        "/listings/3/contact",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/messages/" in response.headers["Location"]


def test_owner_cannot_message_own_listing(client, login, csrf):
    """A listing owner cannot start a conversation with themselves."""
    response = login(client, "hari@uon.edu.au", "Student@123")

    assert response.status_code == 302

    token = csrf("/listings/3")

    response = client.post(
        "/listings/3/contact",
        data={"_csrf": token},
        follow_redirects=False,
    )

    # The application redirects the owner back to the listing.
    assert response.status_code == 302
    assert "/listings/3" in response.headers["Location"]

    # No conversation should have been created for the owner.
    hari_id = get_user_id(client.application, "hari@uon.edu.au")

    assert get_conversation_count(
        client.application, 3, hari_id
    ) == 0


def test_only_participants_can_read_conversation(
    client, login, csrf
):
    """A student outside a conversation cannot read its messages."""
    response = login(client, "akshaya@uon.edu.au", "Student@123")

    assert response.status_code == 302

    response = client.get("/messages/1")

    assert response.status_code == 403


def test_non_participant_cannot_send_message(client, login, csrf):
    """A non-participant cannot send a message into another conversation."""
    response = login(client, "akshaya@uon.edu.au", "Student@123")

    assert response.status_code == 302

    token = csrf("/login")

    response = client.post(
        "/messages/1",
        data={
            "_csrf": token,
            "body": "This message should not be accepted.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_buyer_and_seller_can_exchange_messages(client, login, csrf):
    """Both conversation participants can send and read messages."""
    # Dhimanshi starts a conversation about Madhavi's listing.
    response = login(
        client, "dhimanshi@uon.edu.au", "Student@123"
    )

    assert response.status_code == 302

    token = csrf("/listings/1")

    response = client.post(
        "/listings/1/contact",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert response.status_code == 302

    conversation_id = response.headers["Location"].rstrip("/").split("/")[-1]

    # The buyer sends the first message.
    token = csrf(f"/messages/{conversation_id}")

    response = client.post(
        f"/messages/{conversation_id}",
        data={
            "_csrf": token,
            "body": "Hello, is the textbook available?",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # The seller logs in and replies.
    response = login(
        client, "madhavi@uon.edu.au", "Student@123"
    )

    assert response.status_code == 302

    token = csrf(f"/messages/{conversation_id}")

    response = client.post(
        f"/messages/{conversation_id}",
        data={
            "_csrf": token,
            "body": "Yes, the textbook is still available.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    # Check that both messages remain in the conversation history.
    page = client.get(
        f"/messages/{conversation_id}"
    ).get_data(as_text=True)

    assert "Hello, is the textbook available?" in page
    assert "Yes, the textbook is still available." in page


def test_empty_message_rejected(client, login_student, csrf):
    """A message containing only whitespace is rejected."""
    token = csrf("/messages/1")

    response = login_student.post(
        "/messages/1",
        data={
            "_csrf": token,
            "body": "   ",
        },
        follow_redirects=True,
    )

    assert b"Message cannot be empty" in response.data


def test_message_over_2000_characters_rejected(
    client, login_student, csrf
):
    """Messages longer than 2,000 characters are rejected."""
    token = csrf("/messages/1")

    response = login_student.post(
        "/messages/1",
        data={
            "_csrf": token,
            "body": "A" * 2001,
        },
        follow_redirects=True,
    )

    assert b"Message is too long" in response.data


def test_existing_conversation_is_reused(
    app, client, login, csrf
):
    """Contacting the same listing again does not create a duplicate."""
    response = login(
        client, "dhimanshi@uon.edu.au", "Student@123"
    )

    assert response.status_code == 302

    buyer_id = get_user_id(
        app, "dhimanshi@uon.edu.au"
    )

    token = csrf("/listings/1")

    first_response = client.post(
        "/listings/1/contact",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert first_response.status_code == 302

    first_location = first_response.headers["Location"]

    token = csrf("/listings/1")

    second_response = client.post(
        "/listings/1/contact",
        data={"_csrf": token},
        follow_redirects=False,
    )

    assert second_response.status_code == 302

    second_location = second_response.headers["Location"]

    assert first_location == second_location

    assert get_conversation_count(
        app, 1, buyer_id
    ) == 1


def test_inbox_requires_login(client):
    """Unauthenticated visitors cannot access the messaging inbox."""
    response = client.get("/messages")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_messages_cannot_be_permanently_deleted(
    client, login_student
):
    """The messaging routes do not provide permanent deletion."""
    response = login_student.delete("/messages/1")

    assert response.status_code == 405
