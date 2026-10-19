#!/usr/bin/env python3
"""
run.py
======
Entry point for the UoN Student Marketplace.

Usage:
    python run.py            -> serve on http://127.0.0.1:5000
    FLASK_DEBUG=1 python run.py   -> serve with auto-reload / debug pages

The first run automatically creates and seeds the SQLite database
(database/uon_marketplace.db) from database/schema.sql + seed.sql.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True shows interactive error pages: convenient while marking a
    # demo, disable in real deployments (FLASK_DEBUG unset by default).
    app.run(host="127.0.0.1", port=5000, debug=__import__("os").environ.get("FLASK_DEBUG") == "1")
