#security utilities.
#Handles password hashing, user sessions, access control and CSRF protection.

import secrets
from functools import wraps
from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


# Password handling
def hash_password(password):
    """Generate a secure password hash."""
    return generate_password_hash(password)


def verify_password(password, password_hash):
    """Check whether the password matches the stored hash."""
    return check_password_hash(password_hash, password)


# Session handling
def login_user(user_id):
    #Store the authenticated user's ID in the session.
    session.clear()
    session["user_id"] = user_id
    session.permanent = True


def logout_user():
    #Clear all session data.
    session.clear()


def current_user():
    #Return the logged-in user or None if no user is authenticated.
    if "user_id" not in session:
        return None

    if not hasattr(g, "_current_user"):
        g._current_user = get_db_user(session["user_id"])

        # Log out users whose accounts are no longer active.
        if g._current_user and g._current_user["status"] != "active":
            logout_user()
            g._current_user = None

    return g._current_user


def get_db_user(user_id):
    #Retrieve a user record from the database.
    from .db import get_db

    return get_db().query(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
        one=True,
    )


# Access control
def login_required(view):
    #Allow access only to authenticated users.
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    #Allow access only to administrators.
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()

        if user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))

        if user["role"] != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# CSRF protection
def generate_csrf_token():
    #Generate a CSRF token and store it in the session.
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)

    return session["_csrf_token"]


def validate_csrf():
    #Validate the CSRF token submitted with a POST request.
    token = request.form.get("_csrf", "")
    expected_token = session.get("_csrf_token", "")

    if not token or not expected_token or not secrets.compare_digest(token, expected_token):
        abort(400, description="Invalid or missing CSRF token.")
