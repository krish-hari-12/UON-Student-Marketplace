# UON Student Marketplace application package.
# The create_app() function creates the Flask application, loads configuration,initialises the database and registers the blueprints for each marketplace feature.

from flask import Flask, render_template, request
from config import Config
from . import db
from .security import generate_csrf_token, validate_csrf


def create_app(test_config=None):
    #Create and configure the Flask application.
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Initialise the database.
    db.init_app(app)

    # Register application blueprints.
    from .views import admin, auth, favourites, listings, main, messages, reports, support

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(listings.bp)
    app.register_blueprint(favourites.bp)
    app.register_blueprint(messages.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(admin.bp, url_prefix="/admin")
    app.register_blueprint(support.bp)

    # Protect POST requests with CSRF validation.
    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            validate_csrf()

    # Make shared values available to templates.
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.jinja_env.globals["app_name"] = app.config["APP_NAME"]

    @app.context_processor
    def inject_shared_data():
        #Provide navigation categories and unread message count.
        from .security import current_user

        categories = []
        unread_count = 0
        user = None

        try:
            database = db.get_db()
            categories = database.query(
                """
                SELECT
                    c.category_id,
                    c.name,
                    c.description,
                    COUNT(l.listing_id) AS listing_count
                FROM categories AS c
                LEFT JOIN listings AS l
                    ON c.category_id = l.category_id
                    AND l.status = 'active'
                WHERE c.is_archived = 0
                GROUP BY c.category_id, c.name, c.description
                ORDER BY c.name
                """
            )

            user = current_user()
            if user:
                result = database.query(
                    """
                    SELECT COUNT(*) AS n
                    FROM messages AS m
                    JOIN conversations AS cv
                        ON cv.conversation_id = m.conversation_id
                    JOIN listings AS l
                        ON l.listing_id = cv.listing_id
                    WHERE (cv.buyer_id = ? OR l.user_id = ?)
                      AND m.sender_id != ?
                      AND m.is_read = 0
                    """,
                    (user["user_id"], user["user_id"], user["user_id"]),
                    one=True,
                )
                unread_count = result["n"]

        except Exception:
            # Allow templates to render if the database is unavailable.
            pass

        return {
            "nav_categories": categories,
            "unread_count": unread_count,
            "current_user": user,
        }

    # Register custom error pages.
    for error_code in (400, 403, 404, 500):
        def handle_error(error, code=error_code):
            return render_template(f"errors/{code}.html", code=code), code

        app.register_error_handler(error_code, handle_error)

    return app
