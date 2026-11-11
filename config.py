
"""
Application settings are managed here so they can be changed without
modifying the main application code.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "uon-marketplace-group7-dev-key-change-in-production"
    )
    APP_NAME = "UoN Student Marketplace"

    # SQLite database settings
    DB_BACKEND = "sqlite"
    SQLITE_PATH = BASE_DIR / "database" / "uon_marketplace.db"

    # Security settings
    ALLOWED_EMAIL_DOMAINS = ("uon.edu.au", "newcastle.edu.au")
    MIN_PASSWORD_LENGTH = 8

    # Upload settings
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
    MAX_VIDEO_SIZE = 50 * 1024 * 1024
    MAX_VIDEOS_PER_LISTING = 3
    MAX_IMAGES_PER_LISTING = 5

    # File storage
    UPLOAD_FOLDER = BASE_DIR / "uploads" / "listings"
    PROFILE_UPLOAD_FOLDER = BASE_DIR / "uploads" / "profiles"
    MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
    ALLOWED_PROFILE_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    # Presentation settings
    LISTINGS_PER_PAGE = 9
    LISTING_CONDITIONS = ("New", "Like new", "Good", "Fair", "Needs repair")

    REPORT_REASONS = (
        "Inappropriate content",
        "Scam or fraud",
        "Offensive material",
        "Counterfeit item",
        "Wrong category or spam",
        "Safety concern",
        "Other",
    )

    # Email notification settings
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "jaddaharikrishna36@gmail.com")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "enxlxuqdbruqfgen")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "jaddaharikrishna36@gmail.com")

    # OTP authentication settings
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    OTP_MAX_ATTEMPTS = 5
    OTP_RESEND_COOLDOWN_SECONDS = 60
