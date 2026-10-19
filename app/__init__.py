"""
UoN Student Marketplace - application package.

``create_app()`` is the application factory: it builds the Flask app,
attaches configuration, initialises the data-access layer and registers
every route blueprint (one per functional area of the marketplace).
"""
from flask import Flask, abort, render_template, request

from config import Config
from . import db
from .security import generate_csrf_token, validate_csrf


def create_app(test_config=None):
    """Create and configure the WSGI application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # ------------------------------------------------------------------
    # Database layer (creates + seeds the SQLite file on first run)
    # ------------------------------------------------------------------
    db.init_app(app)

    # ------------------------------------------------------------------
    # Route blueprints - one per functional area
    # ------------------------------------------------------------------
    from .views import main, auth, listings, favourites, messages, reports, admin

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(listings.bp)
    app.register_blueprint(favourites.bp)
    app.register_blueprint(messages.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(admin.bp, url_prefix="/admin")

    # ------------------------------------------------------------------
    # Server-side security: every POST must carry the session CSRF token
    # ------------------------------------------------------------------
    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            validate_csrf()

    # ------------------------------------------------------------------
    # Template globals and context helpers
    # ------------------------------------------------------------------
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.jinja_env.globals["app_name"] = app.config["APP_NAME"]

    @app.context_processor
    def inject_shared_data():
        """Shared template context: navbar categories + unread message count."""
        from .security import current_user

        categories, unread_count, user = [], 0, None
        try:
            categories = db.get_db().query(
                "SELECT category_id, name FROM categories "
                "WHERE is_archived = 0 ORDER BY name"
            )
            user = current_user()
            if user:
                unread_count = db.get_db().query(
                    """
                    SELECT COUNT(*) AS n
                    FROM messages m
                    JOIN conversations cv ON cv.conversation_id = m.conversation_id
                    JOIN listings l ON l.listing_id = cv.listing_id
                    WHERE (cv.buyer_id = ? OR l.user_id = ?)
                      AND m.sender_id != ? AND m.is_read = 0
                    """,
                    (user["user_id"], user["user_id"], user["user_id"]), one=True,
                )["n"]
        except Exception:
            # Database not initialised yet - render the shell gracefully.
            pass
        return dict(nav_categories=categories, unread_count=unread_count,
                    current_user=user)

    # ------------------------------------------------------------------
    # Friendly error pages (400/403/404/500)
    # ------------------------------------------------------------------
    for code in (400, 403, 404, 500):
        def _handler(e, _code=code):
            return render_template(f"errors/{_code}.html", code=_code), _code
        app.register_error_handler(code, _handler)

    return app
