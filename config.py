"""
config.py
=========
Application configuration for the UoN Student Marketplace.

All tunable settings live here so that behaviour can be changed without
touching application code. Sensitive values (secret key, SMTP password)
can be overridden with environment variables.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration used by the application factory (see app/__init__.py)."""

    # ------------------------------------------------------------------
    # Flask core settings
    # ------------------------------------------------------------------
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "uon-marketplace-group7-dev-key-change-in-production"
    )
    APP_NAME = "UoN Student Marketplace"

    # ------------------------------------------------------------------
    # Database settings
    #   DB_BACKEND = 'sqlite'  -> zero-install default, file database
    #   DB_BACKEND = 'mysql'   -> optional MySQL server (e.g. XAMPP)
    # The same SQL runs on both backends (see app/db.py for the adapter).
    # ------------------------------------------------------------------
    DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")
    SQLITE_PATH = BASE_DIR / "database" / "uon_marketplace.db"

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "uon_marketplace")

    # ------------------------------------------------------------------
    # Security settings
    # ------------------------------------------------------------------
    # Business Rule BR-01: only approved UoN student email addresses may
    # register. Both current UoN student/staff domains are accepted.
    ALLOWED_EMAIL_DOMAINS = ("uon.edu.au", "newcastle.edu.au")

    # Password policy (minimum length enforced in app/validation.py)
    MIN_PASSWORD_LENGTH = 8

    # Maximum accepted upload size for the whole request (8 MB)
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    # Per-image limit and permitted extensions for listing photos
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    MAX_IMAGES_PER_LISTING = 3

    # ------------------------------------------------------------------
    # File storage
    # ------------------------------------------------------------------
    UPLOAD_FOLDER = BASE_DIR / "uploads" / "listings"

    # ------------------------------------------------------------------
    # Presentation settings
    # ------------------------------------------------------------------
    LISTINGS_PER_PAGE = 9  # listings shown per page on browse/search

    # Listing condition values shown in the post-ad form (data dictionary
    # is mirrored in database/schema.sql CHECK constraints)
    LISTING_CONDITIONS = ("New", "Like new", "Good", "Fair", "Needs repair")

    # Report reasons offered on the report-a-listing form
    REPORT_REASONS = (
        "Inappropriate content",
        "Scam or fraud",
        "Offensive material",
        "Counterfeit item",
        "Wrong category or spam",
        "Safety concern",
        "Other",
    )

    # ------------------------------------------------------------------
    # Email notifications (FR-10)
    # When SMTP settings are blank the application runs in "simulated
    # email" mode: notification emails are recorded in the email_log
    # table (visible under Admin -> Email Log) instead of being sent.
    # ------------------------------------------------------------------
    SMTP_HOST = os.environ.get("SMTP_HOST", "")     # e.g. smtp.gmail.com
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "no-reply@uon.edu.au")
