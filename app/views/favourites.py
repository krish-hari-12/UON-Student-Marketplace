"""
app/views/favourites.py
=======================
Save / remove favourite listings (FR-08).

Business rules:
* BR-03 - favourites belong to the logged-in account only.
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import db
from ..db import now
from ..security import current_user, login_required

bp = Blueprint("favourites", __name__)


@bp.route("/listings/<int:listing_id>/favourite", methods=["POST"])
@login_required
def toggle(listing_id):
    """Add or remove a listing from the user's favourites (one POST = toggle)."""
    db_conn = db.get_db()
    listing = db_conn.query(
        "SELECT listing_id FROM listings WHERE listing_id = ? AND status != 'removed'",
        (listing_id,), one=True,
    )
    if listing is None:
        abort(404)

    saved = db_conn.query(
        "SELECT 1 AS x FROM favourites WHERE user_id = ? AND listing_id = ?",
        (current_user()["user_id"], listing_id), one=True,
    )
    if saved:
        db_conn.execute(
            "DELETE FROM favourites WHERE user_id = ? AND listing_id = ?",
            (current_user()["user_id"], listing_id),
        )
        flash("Removed from favourites.", "info")
    else:
        db_conn.execute(
            "INSERT INTO favourites (user_id, listing_id, created_at) VALUES (?, ?, ?)",
            (current_user()["user_id"], listing_id, now()),
        )
        flash("Saved to favourites.", "success")
    return redirect(request.form.get("next") or url_for("main.home"))


@bp.route("/favourites")
@login_required
def index():
    """The logged-in user's favourites page."""
    rows = db.get_db().query(
        """
        SELECT l.listing_id, l.title, l.price, l.condition, l.status,
               c.name AS category_name,
               (SELECT file_path FROM listing_images i WHERE i.listing_id = l.listing_id
                ORDER BY i.is_primary DESC, i.image_id LIMIT 1) AS image_path
        FROM favourites f
        JOIN listings l ON l.listing_id = f.listing_id
        JOIN categories c ON c.category_id = l.category_id
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
        """,
        (current_user()["user_id"],),
    )
    return render_template("favourites.html", listings=rows)
