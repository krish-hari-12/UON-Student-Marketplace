# UoN Student Marketplace — COMP6900 Group 7

A responsive web marketplace prototype for University of Newcastle students:
register with a UoN email, post listings, browse/search, save favourites,
message buyers/sellers and report listings; administrators moderate content,
manage users and categories.

**Full setup + use-case test instructions:** see
`Group7_setup_run_test_guide_ass4.docx` (in the submission package `docs/` folder).

## Quick start (5 steps, ~5 minutes)

```bash
# 1. Extract the project and open a terminal in this folder
# 2. Create a virtual environment
python -m venv venv
#    Windows:  venv\Scripts\activate     macOS/Linux:  source venv/bin/activate
# 3. Install dependencies
pip install -r requirements.txt
# 4. Run the app (creates + seeds the database automatically on first run)
python run.py
# 5. Open http://127.0.0.1:5000 in your browser
```

## Demo accounts

| Email | Password | Role |
|---|---|---|
| admin@uon.edu.au | Admin@123 | administrator |
| madhavi@uon.edu.au | Student@123 | student |
| dhimanshi@uon.edu.au | Student@123 | student |
| hari@uon.edu.au | Student@123 | student |
| akshaya@uon.edu.au | Student@123 | student |
| sankeerth@uon.edu.au | Student@123 | student |

## Project structure

```
run.py                    entry point (python run.py)
config.py                 all configuration (DB backend, uploads, security)
app/
  __init__.py             application factory
  db.py                   data-access layer (SQLite default, MySQL optional)
  security.py             password hashing, sessions, RBAC, CSRF
  validation.py           server-side form validation
  emailer.py              notification emails (SMTP or simulated log)
  views/                  route layer: main, auth, listings, favourites,
                          messages, reports, admin
  templates/              Jinja2 templates (Bootstrap 5, responsive)
  static/                 stylesheet + small JS enhancements
database/
  schema.sql              SQLite schema (DDL)
  seed.sql                demo data
  mysql_schema.sql        optional MySQL DDL (XAMPP/phpMyAdmin)
  mysql_seed.sql          optional MySQL seed data
  init_db.py              recreate the database (python init_db.py --reset)
  generate_seed_images.py regenerate the demo listing photos
uploads/listings/         listing photo storage (demo photos pre-loaded)
tests/                    pytest suite (python -m pytest tests/)
```

## Running the tests

```bash
python -m pytest tests/ -v
```

## Using MySQL instead of SQLite (optional)

1. Start MySQL (e.g. XAMPP) and open phpMyAdmin.
2. Import `database/mysql_schema.sql` then `database/mysql_seed.sql`
   (they create the `uon_marketplace` database).
3. Set environment variables before starting the app:

```
DB_BACKEND=mysql
MYSQL_USER=root
MYSQL_PASSWORD=<your-password>
```

## Resetting the demo data

```bash
cd database && python init_db.py --reset
```
