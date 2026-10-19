"""
app/views/main.py
=================
Public marketplace pages: home page, browse/search (FR-06, FR-07) and
listing images served from the uploads folder.
"""
from flask import Blueprint, abort, current_app, render_template, request, send_from_directory

from ..db import get_db

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    """Landing page: hero, category shortcuts and the newest listings."""
    db = get_db()
    latest = db.query(
        """
        SELECT l.listing_id, l.title, l.price, l.condition, l.location, l.created_at,
               c.name AS category_name,
               (SELECT file_path FROM listing_images i WHERE i.listing_id = l.listing_id
                ORDER BY i.is_primary DESC, i.image_id LIMIT 1) AS image_path
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        WHERE l.status = 'active'
        ORDER BY l.created_at DESC
        LIMIT 6
        """
    )
    return render_template("home.html", latest=latest)


@bp.route("/listings")
def browse():
    """Browse + search page with keyword, category, price, condition,
    location and sorting filters (FR-06, FR-07)."""
    db = get_db()

    # ---- read filters from the query string --------------------------------
    q = (request.args.get("q") or "").strip()
    category_id = request.args.get("category", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    condition = request.args.get("condition", type=str)
    location = (request.args.get("location") or "").strip()
    sort = request.args.get("sort", "newest")
    page = max(request.args.get("page", 1, type=int), 1)

    where, params = ["l.status = 'active'"], []
    if q:
        where.append("(l.title LIKE ? OR l.description LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if category_id:
        where.append("l.category_id = ?")
        params.append(category_id)
    if min_price is not None:
        where.append("l.price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("l.price <= ?")
        params.append(max_price)
    if condition:
        where.append("l.condition = ?")
        params.append(condition)
    if location:
        where.append("l.location LIKE ?")
        params.append(f"%{location}%")

    order = {
        "price_asc": "l.price ASC",
        "price_desc": "l.price DESC",
        "oldest": "l.created_at ASC",
    }.get(sort, "l.created_at DESC")

    where_sql = " AND ".join(where)
    per_page = current_app.config["LISTINGS_PER_PAGE"]

    total = db.query(
        f"SELECT COUNT(*) AS n FROM listings l WHERE {where_sql}", params, one=True
    )["n"]
    rows = db.query(
        f"""
        SELECT l.listing_id, l.title, l.price, l.condition, l.location, l.created_at,
               c.name AS category_name,
               (SELECT file_path FROM listing_images i WHERE i.listing_id = l.listing_id
                ORDER BY i.is_primary DESC, i.image_id LIMIT 1) AS image_path
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ? OFFSET ?
        """,
        params + [per_page, (page - 1) * per_page],
    )

    pages = max((total + per_page - 1) // per_page, 1)
    return render_template(
        "listings/browse.html",
        listings=rows, total=total, page=page, pages=pages,
        # echo filters back to the form
        q=q, category_id=category_id, min_price=min_price, max_price=max_price,
        condition=condition, location=location, sort=sort,
    )


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve listing images from the runtime uploads folder."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
