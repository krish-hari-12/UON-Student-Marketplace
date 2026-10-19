"""
app/validation.py
=================
Server-side input validation.

Every form in the application is validated here before any database
operation, independent of the client-side (HTML5) checks, so that the
system stays correct even when requests are crafted manually.

Each validator returns a tuple ``(clean_data, errors)`` where *errors* is a
dictionary mapping field name -> human readable message.
"""
import re

from .db import get_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{6,20}$")


# ----------------------------------------------------------------------
# Registration / profile validation (FR-01, FR-03)
# ----------------------------------------------------------------------
def validate_registration(form):
    """Validate the registration form including the approved-UoN-email rule."""
    clean, errors = {}, {}

    clean["first_name"] = _text(form.get("first_name"), 2, 50)
    if not clean["first_name"]:
        errors["first_name"] = "First name is required (2-50 characters)."

    clean["last_name"] = _text(form.get("last_name"), 2, 50)
    if not clean["last_name"]:
        errors["last_name"] = "Last name is required (2-50 characters)."

    email = (form.get("email") or "").strip().lower()
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    elif not email.endswith(tuple(form_app_domains())):
        errors["email"] = (
            "Registration is limited to approved UoN student email addresses "
            "(@uon.edu.au or @newcastle.edu.au)."
        )
    elif get_db().query(
        "SELECT user_id FROM users WHERE email = ?", (email,), one=True
    ):
        errors["email"] = "An account with this email already exists."
    else:
        clean["email"] = email

    password = form.get("password") or ""
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters long."
    clean["password"] = password

    if form.get("confirm_password") != password:
        errors["confirm_password"] = "Passwords do not match."

    phone = (form.get("phone") or "").strip()
    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Phone number may contain digits, spaces and + - ( )."
    clean["phone"] = phone

    return clean, errors


def validate_profile(form, user_id):
    """Validate the editable profile fields (names and phone)."""
    clean, errors = {}, {}

    clean["first_name"] = _text(form.get("first_name"), 2, 50)
    if not clean["first_name"]:
        errors["first_name"] = "First name is required (2-50 characters)."

    clean["last_name"] = _text(form.get("last_name"), 2, 50)
    if not clean["last_name"]:
        errors["last_name"] = "Last name is required (2-50 characters)."

    phone = (form.get("phone") or "").strip()
    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Phone number may contain digits, spaces and + - ( )."
    clean["phone"] = phone

    return clean, errors


def validate_password_change(form):
    """Validate a change-of-password request (current password required)."""
    from .security import verify_password

    clean, errors = {}, {}
    user = get_db().query(
        "SELECT * FROM users WHERE user_id = ?",
        (_current_user_id(),),
        one=True,
    )

    current = form.get("current_password") or ""
    if not user or not verify_password(current, user["password_hash"]):
        errors["current_password"] = "Your current password is incorrect."

    new = form.get("new_password") or ""
    if len(new) < 8:
        errors["new_password"] = "New password must be at least 8 characters long."
    clean["new_password"] = new

    if form.get("confirm_password") != new:
        errors["confirm_password"] = "Passwords do not match."

    return clean, errors


# ----------------------------------------------------------------------
# Listing validation (BR-04, FR-04)
# ----------------------------------------------------------------------
def validate_listing(form):
    """Validate listing fields. BR-04: title, description, price, category
    and condition are the minimum required fields."""
    clean, errors = {}, {}

    clean["title"] = _text(form.get("title"), 5, 100)
    if not clean["title"]:
        errors["title"] = "Title is required (5-100 characters)."

    clean["description"] = _text(form.get("description"), 20, 2000)
    if not clean["description"]:
        errors["description"] = "Description is required (20-2000 characters)."

    # Price: non-negative number with at most 2 decimal places; 0 = free.
    price_raw = (form.get("price") or "").strip().replace("$", "")
    try:
        price = round(float(price_raw), 2)
        if price < 0 or price > 100000:
            raise ValueError
        clean["price"] = price
    except (TypeError, ValueError):
        errors["price"] = "Enter a valid price between 0 and 100000 (0 = free)."

    category_id = form.get("category_id", "")
    category = get_db().query(
        "SELECT category_id FROM categories WHERE category_id = ? AND is_archived = 0",
        (category_id,),
        one=True,
    )
    if not category:
        errors["category_id"] = "Choose a valid category."
    else:
        clean["category_id"] = int(category_id)

    from config import Config

    condition = form.get("condition", "")
    if condition not in Config.LISTING_CONDITIONS:
        errors["condition"] = "Choose a valid condition."
    else:
        clean["condition"] = condition

    clean["location"] = _text(form.get("location"), 0, 120)
    return clean, errors


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def _text(value, min_len, max_len):
    """Strip and length-check free text; returns '' when below min_len."""
    value = (value or "").strip()
    if min_len <= len(value) <= max_len:
        return value
    return ""


def _current_user_id():
    from flask import session

    return session.get("user_id")


def form_app_domains():
    """Read the approved email domains from the live app config."""
    from flask import current_app

    return current_app.config["ALLOWED_EMAIL_DOMAINS"]
