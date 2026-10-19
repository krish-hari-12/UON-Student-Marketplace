"""
app/views/auth.py
=================
Account routes: registration (FR-01), login/logout (FR-02) and profile
management including password change (FR-03).

Business rules enforced here:
* BR-01 - only approved UoN student email addresses can register;
* BR-03 - a user may update only their own profile;
* BR-09 - registration always creates a plain 'student' account.
"""
from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for,
)

from .. import db
from ..db import now
from ..security import (
    current_user, hash_password, login_required, login_user, logout_user,
    verify_password,
)
from ..validation import validate_password_change, validate_registration, validate_profile

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a new student account (BR-01, FR-01)."""
    if request.method == "POST":
        clean, errors = validate_registration(request.form)
        if errors:
            return render_template("auth/register.html", errors=errors, form=request.form), 400

        db_conn = db.get_db()
        db_conn.execute(
            """
            INSERT INTO users (email, password_hash, first_name, last_name, phone,
                               role, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'student', 'active', ?)
            """,
            (
                clean["email"], hash_password(clean["password"]),
                clean["first_name"], clean["last_name"], clean["phone"], now(),
            ),
        )
        flash("Registration successful - please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", errors={}, form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing account (FR-02)."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = db.get_db().query(
            "SELECT * FROM users WHERE email = ?", (email,), one=True
        )

        if user is None or not verify_password(password, user["password_hash"]):
            # Generic message: do not reveal whether the email exists.
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=request.form), 401

        if user["status"] != "active":
            flash("This account has been suspended. Contact a marketplace administrator.",
                  "danger")
            return render_template("auth/login.html", form=request.form), 403

        login_user(user["user_id"])
        flash(f"Welcome back, {user['first_name']}!", "success")

        next_url = request.args.get("next") or request.form.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)  # open-redirect guard
        return redirect(url_for("main.home"))

    return render_template("auth/login.html", form={})


@bp.route("/logout", methods=["POST"])
def logout():
    """End the session (FR-02). POST-only so a link cannot log users out."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update the logged-in user's own profile (BR-03, FR-03)."""
    user = current_user()

    if request.method == "POST":
        clean, errors = validate_profile(request.form, user["user_id"])
        if errors:
            flash("Please fix the highlighted fields.", "danger")
            return render_template("profile.html", user=user, errors=errors), 400

        db.get_db().execute(
            "UPDATE users SET first_name = ?, last_name = ?, phone = ? WHERE user_id = ?",
            (clean["first_name"], clean["last_name"], clean["phone"], user["user_id"]),
        )
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("profile.html", user=user, errors={})


@bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    """Change the account password (current password required)."""
    clean, errors = validate_password_change(request.form)
    if errors:
        for message in errors.values():
            flash(message, "danger")
        return redirect(url_for("auth.profile"))

    db.get_db().execute(
        "UPDATE users SET password_hash = ? WHERE user_id = ?",
        (hash_password(clean["new_password"]), session["user_id"]),
    )
    flash("Password changed successfully.", "success")
    return redirect(url_for("auth.profile"))
