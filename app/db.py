#database module.
#This module handles SQLite database connections, queries and initialisation.


import sqlite3
from datetime import datetime
from pathlib import Path
from flask import current_app, g


# Connect to the SQLite database.
def _connect_sqlite(config):
    conn = sqlite3.connect(str(config["SQLITE_PATH"]))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class Database:
    #Handle database queries and operations.
    def __init__(self, conn):
        self.conn = conn

    def query(self, sql, params=(), one=False):
        """Run a SELECT query and return dictionary results."""
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        columns = [column[0] for column in cur.description] if cur.description else []
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()

        return rows[0] if (one and rows) else (None if one else rows)

    def execute(self, sql, params=()):
        #Run an INSERT, UPDATE or DELETE query.
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        self.conn.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id

    def executescript(self, sql_text):
        #Execute a SQL script containing multiple statements.
        self.conn.executescript(sql_text)
        self.conn.commit()


# Get the database connection for the current request.
def get_db():
    #Create a database connection if one does not already exist.
    if "db" not in g:
        g.db = Database(_connect_sqlite(current_app.config))

    return g.db


# Close the database connection after the request.
def close_db(_exc=None):
    #Close the current database connection.
    database = g.pop("db", None)

    if database is not None:
        database.conn.close()


# Initialise the database when the application starts.
def init_app(app):
    #Register database cleanup and initialise required tables.
    app.teardown_appcontext(close_db)

    db_path = app.config["SQLITE_PATH"]

    # Create and seed the database if it does not exist.
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

        schema_path = (
            Path(__file__).resolve().parent.parent
            / "database"
            / "schema.sql"
        )
        seed_path = schema_path.parent / "seed.sql"

        conn = _connect_sqlite(app.config)
        try:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.executescript(seed_path.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    # Add required tables and columns to existing databases.
    conn = _connect_sqlite(app.config)

    try:
        # Add the profile photo column if it is missing.
        user_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }

        if "profile_photo" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")

        # Store OTPs for registration and password reset.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_otps (
                otp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                purpose TEXT NOT NULL
                    CHECK (purpose IN ('registration', 'password_reset')),
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                is_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_otps_email_purpose
            ON email_otps (email, purpose, is_used)
        """)

        # Store temporary registration details.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_registrations (
                pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_registrations_email
            ON pending_registrations (email)
        """)

        # Store customer support tickets.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL
                    REFERENCES users(user_id),
                category TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_progress', 'resolved')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Store messages between users and administrators.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL
                    REFERENCES support_tickets(ticket_id)
                    ON DELETE CASCADE,
                sender_id INTEGER NOT NULL
                    REFERENCES users(user_id),
                body TEXT NOT NULL,
                sent_at TEXT NOT NULL
            )
        """)

        # Create indexes for support ticket queries.
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_support_tickets_user
            ON support_tickets(user_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_support_tickets_status
            ON support_tickets(status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_support_messages_ticket
            ON support_messages(ticket_id)
        """)

        # Store videos attached to marketplace listings.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listing_videos (
                video_id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL
                    REFERENCES listings(listing_id)
                    ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_listing
            ON listing_videos(listing_id)
        """)

        conn.commit()

    finally:
        conn.close()


# Return the current timestamp.
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
