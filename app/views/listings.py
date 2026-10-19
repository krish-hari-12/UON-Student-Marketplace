"""
app/views/listings.py
=====================
Listing management routes (FR-04, FR-05) and the listing detail page.

Business rules enforced here:
* BR-02 - a student may create, edit, archive and manage ONLY their own
  listings (ownership is re-checked server-side on every request);
* BR-04 - a listing must contain the minimum required fields before it
  can be published (validated in app/validation.py);
* BR-10 - archived listings stay in the database but are hidden from
  normal browsing.
"""
import os
import uuid

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request,
    url_for,
)

from .. import db
from ..db import now
from ..security import current_user, login_required
from ..validation import validate_listing

bp = Blueprint("listings", __name__)


# ----------------------------------------------------------------------
# Own-listings dashboard (FR-04)
# ----------------------------------------------------------------------
@bp.route("/my-listings")
@login_required
def my_listings():
    """All listings owned by the logged-in user, any status."""
    rows = db.get_db().query(
        """
        SELECT l.*, c.name AS category_name,
               (SELECT COUNT(*) FROM listing_images i
                WHERE i.listing_id = l.listing_id) AS image_count
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        WHERE l.user_id = ?
        ORDER BY l.created_at DESC
        """,
        (current_user()["user_id"],),
    )
    return render_template("listings/my_listings.html", listings=rows)


# ----------------------------------------------------------------------
# Create / edit / status transitions (FR-04)
# ----------------------------------------------------------------------
@bp.route("/listings/new", methods=["GET", "POST"])
@login_required
def create():
    """Post a new listing (BR-04, FR-04)."""
    if request.method == "POST":
        clean, errors = validate_listing(request.form)
        if not errors:
            db_conn = db.get_db()
            listing_id = db_conn.execute(
                """
                INSERT INTO listings (user_id, category_id, title, description,
                                      price, condition, location, status,
                                      created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    current_user()["user_id"], clean["category_id"], clean["title"],
                    clean["description"], clean["price"], clean["condition"],
                    clean["location"], now(), now(),
                ),
            )
            _save_uploaded_images(listing_id)
            flash("Listing published.", "success")
            return redirect(url_for("listings.detail", listing_id=listing_id))
        # fall through: re-render form with the errors dictionary

    form_errors = errors if request.method == "POST" else {}
    categories = db.get_db().query(
        "SELECT category_id, name FROM categories WHERE is_archived = 0 ORDER BY name"
    )
    return render_template(
        "listings/form.html", categories=categories, listing=None,
        errors=form_errors, form=request.form if request.method == "POST" else {},
    ), (400 if request.method == "POST" else 200)


@bp.route("/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit(listing_id):
    """Edit a listing the logged-in user owns (BR-02)."""
    listing = _get_owned_listing(listing_id)
    if listing is None:
        abort(403)  # not the owner -> forbidden (BR-02)

    if request.method == "POST":
        clean, errors = validate_listing(request.form)
        if not errors:
            db.get_db().execute(
                """
                UPDATE listings SET category_id = ?, title = ?, description = ?,
                       price = ?, condition = ?, location = ?, updated_at = ?
                WHERE listing_id = ?
                """,
                (
                    clean["category_id"], clean["title"], clean["description"],
                    clean["price"], clean["condition"], clean["location"],
                    now(), listing_id,
                ),
            )
            _save_uploaded_images(listing_id)
            flash("Listing updated.", "success")
            return redirect(url_for("listings.detail", listing_id=listing_id))

    categories = db.get_db().query(
        "SELECT category_id, name FROM categories WHERE is_archived = 0 ORDER BY name"
    )
    return render_template(
        "listings/form.html", categories=categories, listing=listing,
        errors={}, form=request.form if request.method == "POST" else listing,
    )


@bp.route("/listings/<int:listing_id>/status", methods=["POST"])
@login_required
def set_status(listing_id):
    """Archive / re-activate / mark-sold a listing (owner only, BR-02)."""
    listing = _get_owned_listing(listing_id)
    if listing is None:
        abort(403)

    new_status = request.form.get("status", "")
    if new_status not in ("active", "archived", "sold"):
        abort(400)

    db.get_db().execute(
        "UPDATE listings SET status = ?, updated_at = ? WHERE listing_id = ?",
        (new_status, now(), listing_id),
    )
    flash(f"Listing marked as {new_status}.", "success")
    return redirect(request.form.get("next") or url_for("listings.my_listings"))


@bp.route("/listings/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete(listing_id):
    """Permanently delete the logged-in user's own listing (BR-02)."""
    listing = _get_owned_listing(listing_id)
    if listing is None:
        abort(403)

    db_conn = db.get_db()
    # Remove image files from disk, then the database rows (cascade rules
    # remove favourites / conversations history through FK ON DELETE CASCADE).
    for image in db_conn.query(
        "SELECT file_path FROM listing_images WHERE listing_id = ?", (listing_id,)
    ):
        _remove_image_file(image["file_path"])
    db_conn.execute("DELETE FROM listings WHERE listing_id = ?", (listing_id,))
    flash("Listing deleted.", "success")
    return redirect(url_for("listings.my_listings"))


@bp.route("/listings/<int:listing_id>/images/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_image(listing_id, image_id):
    """Remove one photo from the logged-in user's own listing (BR-02)."""
    if _get_owned_listing(listing_id) is None:
        abort(403)
    image = db.get_db().query(
        "SELECT * FROM listing_images WHERE image_id = ? AND listing_id = ?",
        (image_id, listing_id), one=True,
    )
    if image:
        db.get_db().execute("DELETE FROM listing_images WHERE image_id = ?", (image_id,))
        _remove_image_file(image["file_path"])
        flash("Photo removed.", "success")
    return redirect(url_for("listings.edit", listing_id=listing_id))


# ----------------------------------------------------------------------
# Listing detail page
# ----------------------------------------------------------------------
@bp.route("/listings/<int:listing_id>")
def detail(listing_id):
    """Public listing detail page.

    Removed listings (moderated, BR-10) are hidden from everyone except
    administrators; archived/sold listings stay viewable by direct link
    but show their status.
    """
    listing = db.get_db().query(
        """
        SELECT l.*, c.name AS category_name, u.first_name AS seller_first_name,
               u.created_at AS seller_since
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        JOIN users u ON u.user_id = l.user_id
        WHERE l.listing_id = ?
        """,
        (listing_id,), one=True,
    )
    if listing is None:
        abort(404)

    user = current_user()
    if listing["status"] == "removed" and (user is None or user["role"] != "admin"):
        abort(404)  # moderated content is invisible to normal users (BR-10)

    db_conn = db.get_db()
    images = db_conn.query(
        "SELECT * FROM listing_images WHERE listing_id = ? ORDER BY is_primary DESC, image_id",
        (listing_id,),
    )
    # Can the viewer contact the seller? (logged in, not the owner, active)
    can_contact = (
        user is not None and user["user_id"] != listing["user_id"]
        and listing["status"] == "active"
    )
    already_saved = False
    if user:
        already_saved = bool(db_conn.query(
            "SELECT 1 AS x FROM favourites WHERE user_id = ? AND listing_id = ?",
            (user["user_id"], listing_id), one=True,
        ))

    return render_template(
        "listings/detail.html", listing=listing, images=images,
        can_contact=can_contact, already_saved=already_saved,
    )


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------
def _get_owned_listing(listing_id):
    """Return the listing row when it belongs to the current user, else None."""
    return db.get_db().query(
        "SELECT * FROM listings WHERE listing_id = ? AND user_id = ?",
        (listing_id, current_user()["user_id"]), one=True,
    )


def _save_uploaded_images(listing_id):
    """Store valid uploaded photos for *listing_id* (FR-05).

    Validation: extension allow-list, size limit, randomised filenames and
    a per-listing maximum - see Config in config.py.
    """
    cfg = current_app.config
    files = request.files.getlist("images")
    existing = db.get_db().query(
        "SELECT COUNT(*) AS n FROM listing_images WHERE listing_id = ?", (listing_id,), one=True
    )["n"]
    first = existing == 0  # first stored photo becomes the primary image

    for file in files[: cfg["MAX_IMAGES_PER_LISTING"] - existing]:
        if not file or not file.filename:
            continue
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in cfg["ALLOWED_IMAGE_EXTENSIONS"]:
            flash(f"Skipped {file.filename}: only PNG, JPG, GIF or WEBP images "
                  "are allowed.", "warning")
            continue
        blob = file.read()
        if len(blob) > cfg["MAX_IMAGE_SIZE"]:
            flash(f"Skipped {file.filename}: image exceeds the 5 MB limit.", "warning")
            continue
        if len(blob) == 0:
            continue

        filename = f"{uuid.uuid4().hex}{ext}"  # random name: no user input kept
        path = os.path.join(str(cfg["UPLOAD_FOLDER"]), filename)
        with open(path, "wb") as out:
            out.write(blob)

        db.get_db().execute(
            "INSERT INTO listing_images (listing_id, file_path, is_primary, uploaded_at) "
            "VALUES (?, ?, ?, ?)",
            (listing_id, filename, 1 if first else 0, now()),
        )
        first = False


def _remove_image_file(filename):
    """Best-effort deletion of an image file from the uploads folder."""
    try:
        path = os.path.join(str(current_app.config["UPLOAD_FOLDER"]), filename)
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass  # a stray file must never break the request
