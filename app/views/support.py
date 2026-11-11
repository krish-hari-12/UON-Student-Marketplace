
#Handle student support tickets and administrator replies.

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from app import db
from app.db import now
from app.emailer import send_notification_email
from app.security import current_user, login_required, admin_required

bp = Blueprint("support", __name__)

#Display support tickets belonging to the logged-in user."""
@bp.route("/support")
@login_required
def tickets():
    user = current_user()
    tickets = db.get_db().query(
        """
        SELECT *
        FROM support_tickets
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["user_id"],),
    )

    return render_template("support/tickets.html", tickets=tickets)

#Allow a logged-in user to create a support ticket.
@bp.route("/support/new", methods=["GET", "POST"])
@login_required
def create_ticket():
    if request.method == "POST":
        user = current_user()

        category = (request.form.get("category") or "").strip()
        subject = (request.form.get("subject") or "").strip()
        description = (request.form.get("description") or "").strip()

        allowed_categories = (
            "Account",
            "Login",
            "Listings",
            "Messages",
            "Other",
        )

        if category not in allowed_categories:
            flash("Please select a valid support category.", "danger")
        elif not (5 <= len(subject) <= 120):
            flash("Subject must be between 5 and 120 characters.", "danger")
        elif not (10 <= len(description) <= 3000):
            flash(
                "Description must be between 10 and 3000 characters.",
                "danger",
            )
        else:
            timestamp = now()

            # Save the new support ticket.
            db.get_db().execute(
                """
                INSERT INTO support_tickets (
                    user_id, category, subject, description,
                    status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 'open', ?, ?)
                """,
                (
                    user["user_id"],
                    category,
                    subject,
                    description,
                    timestamp,
                    timestamp,
                ),
            )

            # Notify active administrators about the new ticket.
            admin_users = db.get_db().query(
                """
                SELECT email
                FROM users
                WHERE role = 'admin' AND status = 'active'
                """
            )

            email_subject = "UON Student Marketplace - New Support Ticket"

            email_body = f"""
Hello Administrator,

A new support ticket has been submitted.

Ticket Category: {category}
Subject: {subject}

Student: {user['first_name']} {user['last_name']}
Student Email: {user['email']}

Description:
{description}

Please log in to the administrator dashboard to review
and respond to this ticket.

UON Student Marketplace
"""

            for admin in admin_users:
                send_notification_email(
                    admin["email"],
                    email_subject,
                    email_body,
                )

            flash(
                "Your support ticket has been submitted successfully.",
                "success",
            )
            return redirect(url_for("support.tickets"))

    return render_template("support/create_ticket.html")

# Display a ticket and allow its owner to send messages.
@bp.route("/support/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_detail(ticket_id):
    user = current_user()

    # Users can only access their own support tickets.
    ticket = db.get_db().query(
        """
        SELECT *
        FROM support_tickets
        WHERE ticket_id = ? AND user_id = ?
        """,
        (ticket_id, user["user_id"]),
        one=True,
    )

    if ticket is None:
        abort(404)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()

        if not (1 <= len(body) <= 3000):
            flash("Message must be between 1 and 3000 characters.", "danger")
        elif ticket["status"] == "resolved":
            flash(
                "This ticket is resolved. You cannot send another message.",
                "warning",
            )
        else:
            timestamp = now()

            # Save the student's reply.
            db.get_db().execute(
                """
                INSERT INTO support_messages (
                    ticket_id, sender_id, body, sent_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (ticket_id, user["user_id"], body, timestamp),
            )

            db.get_db().execute(
                """
                UPDATE support_tickets
                SET updated_at = ?
                WHERE ticket_id = ? AND user_id = ?
                """,
                (timestamp, ticket_id, user["user_id"]),
            )

            flash("Your message has been sent.", "success")
            return redirect(
                url_for("support.ticket_detail", ticket_id=ticket_id)
            )

    messages = db.get_db().query(
        """
        SELECT sm.message_id, sm.body, sm.sent_at, sm.sender_id,
               u.first_name, u.last_name, u.role
        FROM support_messages sm
        JOIN users u ON u.user_id = sm.sender_id
        WHERE sm.ticket_id = ?
        ORDER BY sm.sent_at ASC, sm.message_id ASC
        """,
        (ticket_id,),
    )

    return render_template(
        "support/ticket_detail.html",
        ticket=ticket,
        messages=messages,
    )

# Display all student support tickets for administrators.
@bp.route("/admin/support")
@admin_required
def admin_tickets():
    tickets = db.get_db().query(
        """
        SELECT st.ticket_id, st.category, st.subject, st.status,
               st.created_at, st.updated_at,
               u.first_name, u.last_name, u.email
        FROM support_tickets st
        JOIN users u ON u.user_id = st.user_id
        ORDER BY CASE st.status
            WHEN 'open' THEN 1
            WHEN 'in_progress' THEN 2
            WHEN 'resolved' THEN 3
            ELSE 4
        END, st.created_at DESC
        """
    )

    return render_template(
        "support/admin_tickets.html",
        tickets=tickets,
    )

# Allow administrators to view, reply to and update support tickets.
@bp.route("/admin/support/<int:ticket_id>", methods=["GET", "POST"])
@admin_required
def admin_ticket_detail(ticket_id):
    db_conn = db.get_db()

    ticket = db_conn.query(
        """
        SELECT st.*, u.first_name, u.last_name, u.email
        FROM support_tickets st
        JOIN users u ON u.user_id = st.user_id
        WHERE st.ticket_id = ?
        """,
        (ticket_id,),
        one=True,
    )

    if ticket is None:
        abort(404)

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "reply":
            body = (request.form.get("body") or "").strip()

            if not (1 <= len(body) <= 3000):
                flash(
                    "Reply must be between 1 and 3000 characters.",
                    "danger",
                )
            elif ticket["status"] == "resolved":
                flash(
                    "This ticket is resolved. Reopen it before replying.",
                    "warning",
                )
            else:
                user = current_user()
                timestamp = now()

                # Save the administrator's reply.
                db_conn.execute(
                    """
                    INSERT INTO support_messages (
                        ticket_id, sender_id, body, sent_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (ticket_id, user["user_id"], body, timestamp),
                )

                db_conn.execute(
                    """
                    UPDATE support_tickets
                    SET updated_at = ?
                    WHERE ticket_id = ?
                    """,
                    (timestamp, ticket_id),
                )

                # Notify the student about the reply.
                email_subject = (
                    "UON Student Marketplace - Support Ticket Reply"
                )

                email_body = f"""
Hello {ticket['first_name']},

The support team has replied to your support ticket.

Ticket ID: #{ticket_id}
Subject: {ticket['subject']}

Admin Reply:
{body}

Please log in to UON Student Marketplace to view
the complete conversation and respond if necessary.

UON Student Marketplace
"""

                send_notification_email(
                    ticket["email"],
                    email_subject,
                    email_body,
                )

                flash(
                    "Your reply has been sent successfully.",
                    "success",
                )

        elif action == "status":
            new_status = request.form.get("status", "").strip()

            allowed_statuses = (
                "open",
                "in_progress",
                "resolved",
            )

            if new_status not in allowed_statuses:
                flash("Invalid ticket status.", "danger")
            else:
                db_conn.execute(
                    """
                    UPDATE support_tickets
                    SET status = ?, updated_at = ?
                    WHERE ticket_id = ?
                    """,
                    (new_status, now(), ticket_id),
                )

                flash(
                    "Ticket status updated successfully.",
                    "success",
                )
        else:
            flash("Invalid action.", "danger")

        return redirect(
            url_for(
                "support.admin_ticket_detail",
                ticket_id=ticket_id,
            )
        )

    messages = db_conn.query(
        """
        SELECT sm.message_id, sm.body, sm.sent_at, sm.sender_id,
               u.first_name, u.last_name, u.role
        FROM support_messages sm
        JOIN users u ON u.user_id = sm.sender_id
        WHERE sm.ticket_id = ?
        ORDER BY sm.sent_at ASC, sm.message_id ASC
        """,
        (ticket_id,),
    )

    return render_template(
        "support/admin_ticket_detail.html",
        ticket=ticket,
        messages=messages,
    )
