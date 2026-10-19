"""
app/db.py
=========
Data-access layer for the UoN Student Marketplace.

This module is the ONLY place in the application that talks to a database
driver directly. It provides:

* ``get_db()``  - a per-request database connection (Flask ``g`` cached)
* ``query()``   - SELECT helper returning plain dictionaries
* ``execute()`` - INSERT/UPDATE/DELETE helper returning the new row id
* ``init_app()``- automatic database creation from ``database/schema.sql``
                  and ``database/seed.sql`` the first time the app runs

SQL statements throughout the application are written with ``?``
placeholders. When the MySQL backend is selected the adapter rewrites them
to ``%s`` (the PyMySQL placeholder) at execution time, so the same
application code runs on SQLite and MySQL.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g

# PyMySQL is imported lazily inside _connect_mysql() so the SQLite-only
# default installation does not require it.


# ----------------------------------------------------------------------
# Connection handling
# ----------------------------------------------------------------------
def _connect_sqlite(config):
    conn = sqlite3.connect(str(config["SQLITE_PATH"]))
    # Return rows as dictionaries so templates can use row["column"].
    conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints (off by default in SQLite).
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _connect_mysql(config):
    import pymysql

    return pymysql.connect(
        host=config["MYSQL_HOST"],
        port=config["MYSQL_PORT"],
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DB"],
        cursorclass=pymysql.cursors.Cursor,
        autocommit=False,
        charset="utf8mb4",
        # Make '||' behave as string concatenation like SQLite/standard SQL.
        init_command="SET SESSION sql_mode=CONCAT(@@sql_mode, ',PIPES_AS_CONCAT')",
    )


class Database:
    """A thin wrapper over a DBAPI connection with dictionary rows."""

    def __init__(self, conn, backend):
        self.conn = conn
        self.backend = backend

    # -- internals ------------------------------------------------------
    def _sql(self, sql):
        """Rewrite '?' placeholders to '%s' when running on MySQL."""
        return sql.replace("?", "%s") if self.backend == "mysql" else sql

    # -- public helpers ---------------------------------------------------
    def query(self, sql, params=(), one=False):
        """Run a SELECT and return a list of dictionaries (or one dict/None)."""
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), tuple(params))
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return rows[0] if (one and rows) else (None if one else rows)

    def execute(self, sql, params=()):
        """Run an INSERT/UPDATE/DELETE, commit, return the new row id."""
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), tuple(params))
        self.conn.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id

    # -- schema scripts ----------------------------------------------------
    def executescript(self, sql_text):
        """Run a multi-statement SQL script (used to load schema/seed files)."""
        if self.backend == "mysql":
            cur = self.conn.cursor()
            for statement in filter(None, (s.strip() for s in sql_text.split(";"))):
                cur.execute(statement)
            self.conn.commit()
            cur.close()
        else:
            self.conn.executescript(sql_text)
            self.conn.commit()


# ----------------------------------------------------------------------
# Flask integration
# ----------------------------------------------------------------------
def get_db():
    """Return the request-scoped :class:`Database`, creating it if needed."""
    if "db" not in g:
        config = current_app.config
        if config["DB_BACKEND"] == "mysql":
            g.db = Database(_connect_mysql(config), "mysql")
        else:
            g.db = Database(_connect_sqlite(config), "sqlite")
    return g.db


def close_db(_exc=None):
    """Teardown handler - close the request connection."""
    db = g.pop("db", None)
    if db is not None:
        db.conn.close()


def init_app(app):
    """Register teardown and make sure the database exists and is seeded."""
    app.teardown_appcontext(close_db)

    if app.config["DB_BACKEND"] == "mysql":
        # MySQL users import database/mysql_schema.sql + mysql_seed.sql
        # themselves (e.g. through phpMyAdmin) - see the setup guide.
        return

    db_path = app.config["SQLITE_PATH"]
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Schema/seed scripts always live in the project's database folder.
        schema_path = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
        seed_path = schema_path.parent / "seed.sql"
        conn = _connect_sqlite(app.config)
        try:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.executescript(seed_path.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()


def now():
    """Current timestamp formatted for storage (portable across backends)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
