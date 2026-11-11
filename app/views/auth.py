
# Account routes for registration, login, logout and profile management.

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint, current_app, flash, redirect, render_template,
    request, session, url_for, send_from_directory
)

from app import db
from app.db import now
from app.emailer import send_otp_email
from app.otp import generate_otp, verify_otp
from app.security import (
    current_user, hash_password, login_required, login_user,
    logout_user, verify_password
)
from app.validation import (
    validate_password_change, validate_registration, validate_profile
)

bp = Blueprint("auth", __name__)

@bp.route("/register", methods=["GET", "POST"])
def register():
    #Start student registration and send an email verification OTP.
    if request.method == "POST":
        clean, errors = validate_registration(request.form)

        if errors:
            return render_template(
                "auth/register.html", errors=errors, form=request.form
            ), 400

        email = clean["email"]
        otp = generate_otp(email, "registration")

        if otp is None:
            flash("Please wait 60 seconds before requesting another code.", "warning")
            return render_template(
                "auth/register.html", errors={}, form=request.form
            ), 429

        expiry = datetime.now() + timedelta(
            minutes=current_app.config["OTP_EXPIRY_MINUTES"]
        )
        db_conn = db.get_db()

        existing_pending = db_conn.query(
            "SELECT pending_id FROM pending_registrations WHERE email = ?",
            (email,),
            one=True
        )

        registration_data = (
            hash_password(clean["password"]),
            clean["first_name"],
            clean["last_name"],
            clean["phone"],
            expiry.strftime("%Y-%m-%d %H:%M:%S")
        )

        if existing_pending:
            db_conn.execute(
                """
                UPDATE pending_registrations
                SET password_hash = ?, first_name = ?, last_name = ?,
                    phone = ?, expires_at = ?, created_at = ?
                WHERE email = ?
                """,
                registration_data + (now(), email)
            )
        else:
            db_conn.execute(
                """
                INSERT INTO pending_registrations
                    (email, password_hash, first_name, last_name,
                     phone, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (email,) + registration_data + (now(),)
            )

        email_sent = send_otp_email(email, otp, purpose="registration")

        if not email_sent:
            # Remove temporary registration data if email delivery fails.
            db_conn.execute(
                "DELETE FROM pending_registrations WHERE email = ?",
                (email,)
            )
            db_conn.execute(
                """
                DELETE FROM email_otps
                WHERE otp_id = (
                    SELECT otp_id FROM email_otps
                    WHERE email = ? AND purpose = ?
                    ORDER BY otp_id DESC LIMIT 1
                )
                """,
                (email, "registration")
            )

            flash(
                "We couldn't send the verification email. "
                "Please check the email configuration and try again.",
                "danger"
            )
            return render_template(
                "auth/register.html", errors={}, form=request.form
            ), 503

        session["pending_registration_email"] = email
        flash("A 6-digit verification code has been sent to your email.", "success")
        return redirect(url_for("auth.verify_registration"))

    return render_template("auth/register.html", errors={}, form={})


@bp.route("/verify-registration", methods=["GET", "POST"])
def verify_registration():
    #Verify the registration email OTP and create the student account.
    email = session.get("pending_registration_email")

    if not email:
        flash("Please start the registration process first.", "warning")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        db_conn = db.get_db()

        pending = db_conn.query(
            "SELECT * FROM pending_registrations WHERE email = ?",
            (email,),
            one=True
        )

        if pending is None:
            session.pop("pending_registration_email", None)
            flash("Your registration request was not found. Please register again.", "danger")
            return redirect(url_for("auth.register"))

        expiry = datetime.strptime(
            pending["expires_at"], "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() >= expiry:
            db_conn.execute(
                "DELETE FROM pending_registrations WHERE email = ?",
                (email,)
            )
            session.pop("pending_registration_email", None)
            flash("Your verification code has expired. Please register again.", "danger")
            return redirect(url_for("auth.register"))

        if not verify_otp(email, otp, "registration"):
            flash("Invalid or expired verification code. Please try again.", "danger")
            return render_template("auth/verify_otp.html", email=email), 400

        existing_user = db_conn.query(
            "SELECT user_id FROM users WHERE email = ?",
            (email,),
            one=True
        )

        if existing_user:
            db_conn.execute(
                "DELETE FROM pending_registrations WHERE email = ?",
                (email,)
            )
            session.pop("pending_registration_email", None)
            flash("An account with this email already exists. Please log in.", "info")
            return redirect(url_for("auth.login"))

        # Create a student account after successful email verification.
        db_conn.execute(
            """
            INSERT INTO users
                (email, password_hash, first_name, last_name, phone,
                 role, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'student', 'active', ?)
            """,
            (
                email,
                pending["password_hash"],
                pending["first_name"],
                pending["last_name"],
                pending["phone"],
                now()
            )
        )

        # Remove temporary registration details.
        db_conn.execute(
            "DELETE FROM pending_registrations WHERE email = ?",
            (email,)
        )

        session.pop("pending_registration_email", None)
        flash("Email verified! Your account has been created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/verify_otp.html", email=email)


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    #Send a password-reset OTP to a registered user's email.
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()

        if not email:
            flash("Please enter your registered email address.", "danger")
            return render_template("auth/forgot_password.html"), 400

        user = db.get_db().query(
            "SELECT user_id FROM users WHERE email = ?",
            (email,),
            one=True
        )

        if not user:
            flash(
                "No account exists with this email address. Please register first.",
                "danger"
            )
            return render_template("auth/forgot_password.html"), 404

        otp = generate_otp(email, "password_reset")

        if otp is None:
            flash("Please wait 60 seconds before requesting another code.", "warning")
            return render_template("auth/forgot_password.html"), 429

        email_sent = send_otp_email(email, otp, purpose="password reset")

        if email_sent:
            session["pending_password_reset_email"] = email
            flash(
                "Verification code sent successfully. Please check your email.",
                "success"
            )
            return redirect(url_for("auth.verify_reset_otp"))

        # Remove the OTP if email delivery fails.
        db.get_db().execute(
            """
            DELETE FROM email_otps
            WHERE otp_id = (
                SELECT otp_id FROM email_otps
                WHERE email = ? AND purpose = ?
                ORDER BY otp_id DESC LIMIT 1
            )
            """,
            (email, "password_reset")
        )

        flash("Unable to send the verification code. Please try again.", "danger")
        return redirect(url_for("auth.forgot_password"))

    return render_template("auth/forgot_password.html")


@bp.route("/verify-reset-otp", methods=["GET", "POST"])
def verify_reset_otp():
    #Verify the OTP before allowing a password reset.
    email = session.get("pending_password_reset_email")

    if not email:
        flash("Please request a password reset first.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()

        if verify_otp(email, otp, "password_reset"):
            session.pop("pending_password_reset_email", None)
            session["password_reset_verified_email"] = email
            flash("OTP verified successfully. Set your new password.", "success")
            return redirect(url_for("auth.reset_password"))

        flash("Invalid or expired verification code. Please try again.", "danger")
        return render_template("auth/verify_reset_otp.html", email=email), 400

    return render_template("auth/verify_reset_otp.html", email=email)


@bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    #Allow a user to set a new password after OTP verification.
    email = session.get("password_reset_verified_email")

    if not email:
        flash("Please verify your email before resetting your password.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        errors = {}
        min_length = current_app.config["MIN_PASSWORD_LENGTH"]

        if len(password) < min_length:
            errors["password"] = (
                f"Password must contain at least {min_length} characters."
            )

        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return render_template("auth/reset_password.html", errors=errors), 400

        db.get_db().execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (hash_password(password), email)
        )

        session.pop("password_reset_verified_email", None)
        flash("Your password has been reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", errors={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    #Authenticate an existing account.
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = db.get_db().query(
            "SELECT * FROM users WHERE email = ?",
            (email,),
            one=True
        )

        if user is None or not verify_password(password, user["password_hash"]):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=request.form), 401

        if user["status"] != "active":
            flash(
                "This account has been suspended. Contact a marketplace administrator.",
                "danger"
            )
            return render_template("auth/login.html", form=request.form), 403

        login_user(user["user_id"])
        flash(f"Welcome back, {user['first_name']}!", "success")

        next_url = request.args.get("next") or request.form.get("next")

        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)

        return redirect(url_for("main.home"))

    return render_template("auth/login.html", form={})


@bp.route("/logout", methods=["POST"])
def logout():
    #End the session using a POST request.
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    #View and update the logged-in user's own profile.
    user = current_user()

    if request.method == "POST":
        clean, errors = validate_profile(request.form, user["user_id"])

        if errors:
            flash("Please fix the highlighted fields.", "danger")
            return render_template("profile.html", user=user, errors=errors), 400

        db.get_db().execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, phone = ?
            WHERE user_id = ?
            """,
            (clean["first_name"], clean["last_name"], clean["phone"], user["user_id"])
        )

        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("profile.html", user=user, errors={})


@bp.route("/profile/photo", methods=["POST"])
@login_required
def upload_profile_photo():
    #Upload or replace the logged-in user's profile photo.
    user = current_user()
    photo = request.files.get("profile_photo")

    if not photo or not photo.filename:
        flash("Please select a profile photo.", "warning")
        return redirect(url_for("auth.profile"))

    extension = Path(photo.filename).suffix.lower()
    allowed_extensions = current_app.config["ALLOWED_PROFILE_PHOTO_EXTENSIONS"]

    if extension not in allowed_extensions:
        flash("Please upload a PNG, JPG, JPEG or WEBP image.", "danger")
        return redirect(url_for("auth.profile"))

    # Check the uploaded file size.
    photo.stream.seek(0, 2)
    file_size = photo.stream.tell()
    photo.stream.seek(0)

    max_size = current_app.config["MAX_PROFILE_PHOTO_SIZE"]

    if file_size > max_size:
        flash("Profile photos must be 5 MB or smaller.", "danger")
        return redirect(url_for("auth.profile"))

    upload_folder = Path(current_app.config["PROFILE_UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    new_photo_path = upload_folder / filename
    old_filename = user.get("profile_photo")

    try:
        photo.save(new_photo_path)

        db.get_db().execute(
            "UPDATE users SET profile_photo = ? WHERE user_id = ?",
            (filename, user["user_id"])
        )

    except Exception:
        # Remove the new file if the database update fails.
        if new_photo_path.exists():
            new_photo_path.unlink()

        current_app.logger.exception("Failed to update profile photo.")
        flash("Unable to update your profile photo. Please try again.", "danger")
        return redirect(url_for("auth.profile"))

    # Remove the previous image after the new image is saved.
    if old_filename and old_filename != filename:
        old_photo_path = upload_folder / Path(old_filename).name

        try:
            if old_photo_path.is_file():
                old_photo_path.unlink()
        except OSError:
            current_app.logger.exception("Could not remove the previous profile photo.")

    flash("Profile photo updated successfully.", "success")
    return redirect(url_for("auth.profile"))


@bp.route("/profile/photo/default", methods=["POST"])
@login_required
def reset_profile_photo():
    #Reset the logged-in user's profile photo to the default avatar.
    user = current_user()
    old_filename = user.get("profile_photo")

    if not old_filename:
        flash("You are already using the default avatar.", "info")
        return redirect(url_for("auth.profile"))

    db.get_db().execute(
        "UPDATE users SET profile_photo = NULL WHERE user_id = ?",
        (user["user_id"],)
    )

    # Remove the old image file after updating the database.
    upload_folder = Path(current_app.config["PROFILE_UPLOAD_FOLDER"])
    old_photo_path = upload_folder / Path(old_filename).name

    try:
        if old_photo_path.is_file():
            old_photo_path.unlink()
    except OSError:
        current_app.logger.exception("Could not remove the previous profile photo.")

    flash("Your profile photo has been reset to the default avatar.", "success")
    return redirect(url_for("auth.profile"))


@bp.route("/profile/photos/<path:filename>")
def profile_photo_file(filename):
    #Serve profile photos from the profile upload folder.
    upload_folder = current_app.config["PROFILE_UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)


@bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    #Change the account password after checking the current password.
    clean, errors = validate_password_change(request.form)

    if errors:
        for message in errors.values():
            flash(message, "danger")
        return redirect(url_for("auth.profile"))

    db.get_db().execute(
        "UPDATE users SET password_hash = ? WHERE user_id = ?",
        (hash_password(clean["new_password"]), session["user_id"])
    )

    flash("Password changed successfully.", "success")
    return redirect(url_for("auth.profile"))
