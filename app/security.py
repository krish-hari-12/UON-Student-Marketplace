"""
app/security.py
===============
Security utilities: password hashing, session authentication, role-based
access-control decorators and CSRF protection.

Implements the server-side security requirements from the scoping report:
* passwords are never stored in plain text (PBKDF2-SHA256 via Werkzeug);
* every protected route checks the session server-side (FR-14);
* administrators-only routes are guarded by ``admin_required`` (BR-07);
* every state-changing POST request requires a valid CSRF token (BR-09).
"""
import secrets
from functools import wraps

from flask import abort, g, redirect, request, session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

# ----------------------------------------------------------------------
# Password handling
# ----------------------------------------------------------------------
def hash_password(password):
    """Return a salted PBKDF2-SHA256 hash for *password*."""
    return generate_password_hash(password)


def verify_password(password, password_hash):
    """Constant-time check of *password* against a stored hash."""
    return check_password_hash(password_hash, password)


# ----------------------------------------------------------------------
# Session helpers
# ----------------------------------------------------------------------
def login_user(user_id):
    """Store the authenticated user id in the (signed) session cookie."""
    session.clear()                       # prevent session fixation
    session["user_id"] = user_id
    session.permanent = True


def logout_user():
    """Remove all session data."""
    session.clear()


def current_user():
    """Return the logged-in user as a dict (fresh from the DB) or None.

    The user record is re-fetched on every request so that role changes or
    suspensions take effect immediately (BR-01 / BR-09).
    """
    if "user_id" not in session:
        return None
    if not hasattr(g, "_current_user"):
        g._current_user = get_db_user(session["user_id"])
        # A suspended account is logged out automatically.
        if g._current_user and g._current_user["status"] != "active":
            logout_user()
            g._current_user = None
    return g._current_user


def get_db_user(user_id):
    """Fetch one user row from the database (or None)."""
    # Imported here to avoid a circular import with app.db at module load.
    from .db import get_db

    return get_db().query("SELECT * FROM users WHERE user_id = ?", (user_id,), one=True)


# ----------------------------------------------------------------------
# Access-control decorators (FR-14)
# ----------------------------------------------------------------------
def login_required(view):
    """Decorator: redirect anonymous users to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Decorator: only administrators may call this view (BR-07, FR-14)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if user["role"] != "admin":
            abort(403)  # students can never reach admin-only functions
        return view(*args, **kwargs)

    return wrapped


# ----------------------------------------------------------------------
# CSRF protection
# ----------------------------------------------------------------------
def generate_csrf_token():
    """Return (creating if necessary) the CSRF token stored in the session."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf():
    """Reject POST requests whose CSRF token does not match the session."""
    token = request.form.get("_csrf", "")
    expected = session.get("_csrf_token", "")
    if not token or not expected or not secrets.compare_digest(token, expected):
        abort(400, description="Invalid or missing CSRF token.")
