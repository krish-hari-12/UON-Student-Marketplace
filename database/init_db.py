
#!/usr/bin/env python3
"""
UON Student Marketplace - Database Initialisation

Creates a SQLite database using schema.sql and seed.sql.

Usage:
    python init_db.py
    python init_db.py --db-path test_uon_marketplace.db
    python init_db.py --db-path test_uon_marketplace.db --reset
"""

import argparse
import sqlite3
from pathlib import Path


DATABASE_DIR = Path(__file__).resolve().parent

SCHEMA_FILE = DATABASE_DIR / "schema.sql"
SEED_FILE = DATABASE_DIR / "seed.sql"
DEFAULT_DB = DATABASE_DIR / "uon_marketplace.db"

EXPECTED_TABLES = {
    "users",
    "categories",
    "listings",
    "listing_images",
    "favourites",
    "conversations",
    "messages",
    "reports",
    "audit_log",
    "email_log",
    "email_otps",
    "pending_registrations",
    "support_tickets",
    "support_messages",
    "listing_videos",
}


def initialise_database(db_path, reset=False):
    """Create and initialise the SQLite database."""

    db_path = Path(db_path).resolve()

    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(
            f"Database schema not found: {SCHEMA_FILE}"
        )

    if not SEED_FILE.exists():
        raise FileNotFoundError(
            f"Database seed file not found: {SEED_FILE}"
        )

    if db_path.exists():
        if not reset:
            print(f"Database already exists: {db_path}")
            print("Use --reset only if you intentionally want to rebuild it.")
            return

        db_path.unlink()
        print("Existing database removed.")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        with open(SCHEMA_FILE, encoding="utf-8") as file:
            conn.executescript(file.read())

        with open(SEED_FILE, encoding="utf-8") as file:
            conn.executescript(file.read())

        # Check that all expected application tables exist.
        result = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )

        actual_tables = {
            row[0] for row in result.fetchall()
            if not row[0].startswith("sqlite_")
        }

        missing_tables = EXPECTED_TABLES - actual_tables

        if missing_tables:
            raise RuntimeError(
                f"Missing database tables: {sorted(missing_tables)}"
            )

        # Check foreign-key integrity.
        foreign_key_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            raise RuntimeError(
                f"Foreign-key errors found: {foreign_key_errors}"
            )

        conn.commit()

        print("Database initialised successfully.")
        print(f"Database location: {db_path}")
        print(f"Application tables created: {len(actual_tables)}")
        print("All expected tables are present.")
        print("Foreign-key integrity check passed.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialise the UON Student Marketplace database."
    )

    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB),
        help="Path where the SQLite database should be created."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the specified database."
    )

    args = parser.parse_args()

    initialise_database(
        db_path=args.db_path,
        reset=args.reset
    )
