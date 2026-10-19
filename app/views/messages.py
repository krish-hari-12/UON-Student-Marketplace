"""
app/views/messages.py
=====================
Buyer-seller messaging linked to listings (FR-09).

Business rules:
* BR-05 - only the buyer and the seller of a conversation may read or
  send messages inside it; access is re-checked on every request;
* FR-10 - a notification email is sent (or simulated) when a message
  arrives for the other party.
"""
from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)

from .. import db
from ..db import now
from ..emailer import send_notification_email
from ..security import current_user, login_required

bp = Blueprint("messages", __name__)


@bp.route("/listings/<int:listing_id>/contact", methods=["POST"])
@login_required
def start_conversation(listing_id):
    """Open (or return to) the buyer's conversation about this listing."""
    db_conn = db.get_db()
    listing = db_conn.query(
        """
        SELECT listing_id, user_id, title FROM listings
        WHERE listing_id = ? AND status = 'active'
        """,
        (listing_id,), one=True,
    )
    if listing is None:
        abort(404)
    if listing["user_id"] == current_user()["user_id"]:
        flash("You cannot message yourself about your own listing.", "warning")
        return redirect(url_for("listings.detail", listing_id=listing_id))

    existing = db_conn.query(
        """
        SELECT conversation_id FROM conversations
        WHERE listing_id = ? AND buyer_id = ?
        """,
        (listing_id, current_user()["user_id"]), one=True,
    )
    if existing is None:
        conversation_id = db_conn.execute(
            "INSERT INTO conversations (listing_id, buyer_id, created_at) VALUES (?, ?, ?)",
            (listing_id, current_user()["user_id"], now()),
        )
    else:
        conversation_id = existing["conversation_id"]
    return redirect(url_for("messages.thread", conversation_id=conversation_id))


@bp.route("/messages")
@login_required
def inbox():
    """All conversations where the user is the buyer or the seller."""
    user_id = current_user()["user_id"]
    rows = db.get_db().query(
        """
        SELECT cv.conversation_id, cv.created_at,
               l.title AS listing_title, l.listing_id,
               buyer.user_id AS buyer_id, buyer.first_name AS buyer_name,
               seller.user_id AS seller_id, seller.first_name AS seller_name,
               (SELECT body FROM messages m WHERE m.conversation_id = cv.conversation_id
                ORDER BY m.message_id DESC LIMIT 1) AS last_message,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = cv.conversation_id
                AND m.sender_id != ? AND m.is_read = 0) AS unread
        FROM conversations cv
        JOIN listings l ON l.listing_id = cv.listing_id
        JOIN users buyer ON buyer.user_id = cv.buyer_id
        JOIN users seller ON seller.user_id = l.user_id
        WHERE cv.buyer_id = ? OR seller.user_id = ?
        ORDER BY cv.conversation_id DESC
        """,
        (user_id, user_id, user_id),
    )
    return render_template("messages/inbox.html", conversations=rows)


@bp.route("/messages/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def thread(conversation_id):
    """View one conversation and send messages (BR-05)."""
    db_conn = db.get_db()
    user_id = current_user()["user_id"]

    conversation = db_conn.query(
        """
        SELECT cv.*, l.title AS listing_title, l.user_id AS seller_id,
               l.status AS listing_status, buyer.first_name AS buyer_name
        FROM conversations cv
        JOIN listings l ON l.listing_id = cv.listing_id
        JOIN users buyer ON buyer.user_id = cv.buyer_id
        WHERE cv.conversation_id = ?
        """,
        (conversation_id,), one=True,
    )
    # BR-05: authorisation - only the buyer or the seller may open the thread.
    if conversation is None or user_id not in (conversation["buyer_id"], conversation["seller_id"]):
        abort(403)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Message cannot be empty.", "danger")
        elif len(body) > 2000:
            flash("Message is too long (max 2000 characters).", "danger")
        else:
            db_conn.execute(
                "INSERT INTO messages (conversation_id, sender_id, body, sent_at, is_read) "
                "VALUES (?, ?, ?, ?, 0)",
                (conversation_id, user_id, body, now()),
            )
            # Notify the other party by email (FR-10).
            other_id = (conversation["seller_id"]
                        if user_id == conversation["buyer_id"] else conversation["buyer_id"])
            other = db_conn.query(
                "SELECT email, first_name FROM users WHERE user_id = ?", (other_id,), one=True
            )
            if other:
                send_notification_email(
                    other["email"],
                    f"New message - {conversation['listing_title']}",
                    f"Hi {other['first_name']},\n\nYou have a new message about "
                    f"\"{conversation['listing_title']}\" on the UoN Student Marketplace.\n\n"
                    f"Log in to read and reply: http://127.0.0.1:5000/messages/{conversation_id}\n",
                )
            return redirect(url_for("messages.thread", conversation_id=conversation_id))

    # Mark messages sent by the other party as read when opening the thread.
    db_conn.execute(
        "UPDATE messages SET is_read = 1 WHERE conversation_id = ? AND sender_id != ?",
        (conversation_id, user_id),
    )
    messages = db_conn.query(
        """
        SELECT m.*, u.first_name AS sender_name
        FROM messages m JOIN users u ON u.user_id = m.sender_id
        WHERE m.conversation_id = ? ORDER BY m.message_id
        """,
        (conversation_id,),
    )
    return render_template(
        "messages/thread.html", conversation=conversation, messages=messages
    )
