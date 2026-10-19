#!/usr/bin/env python3
"""
init_db.py
==========
Utility to (re)create the SQLite database from schema.sql + seed.sql.

Usage (from the database folder):
    python init_db.py          # create the DB only if it does not exist
    python init_db.py --reset  # DELETE and rebuild the database from scratch
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "uon_marketplace.db")

if __name__ == "__main__":
    if "--reset" in sys.argv and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database.")
    if os.path.exists(DB_PATH):
        print(f"Database already exists: {DB_PATH} (use --reset to rebuild)")
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    with open(os.path.join(HERE, "seed.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Database created and seeded: {DB_PATH}")
