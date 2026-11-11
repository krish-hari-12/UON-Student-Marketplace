
# Listing management routes and listing detail page.

import os
import uuid

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for
)

from app import db
from app.db import now
from app.security import current_user, login_required
from app.validation import validate_listing


bp = Blueprint("listings", __name__)


@bp.route("/my-listings")
@login_required
def my_listings():
    # Display all listings owned by the logged-in user.
    rows = db.get_db().query(
        """
        SELECT l.*, c.name AS category_name,
            (
                SELECT i.file_path
                FROM listing_images i
                WHERE i.listing_id = l.listing_id
                  AND i.is_archived = 0
                ORDER BY i.is_primary DESC, i.image_id ASC
                LIMIT 1
            ) AS image_path,
            (
                SELECT COUNT(*)
                FROM listing_images i
                WHERE i.listing_id = l.listing_id
                  AND i.is_archived = 0
            ) AS image_count
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        WHERE l.user_id = ?
        ORDER BY l.created_at DESC
        """,
        (current_user()["user_id"],)
    )

    return render_template(
        "listings/my_listings.html",
        listings=rows
    )


@bp.route("/listings/new", methods=["GET", "POST"])
@login_required
def create():
    # Create a new listing.
    if request.method == "POST":
        clean, errors = validate_listing(request.form)

        if not errors:
            db_conn = db.get_db()

            listing_id = db_conn.execute(
                """
                INSERT INTO listings
                    (user_id, category_id, title, description, price,
                     condition, location, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    current_user()["user_id"],
                    clean["category_id"],
                    clean["title"],
                    clean["description"],
                    clean["price"],
                    clean["condition"],
                    clean["location"],
                    now(),
                    now()
                )
            )

            _save_uploaded_images(listing_id)
            _save_uploaded_videos(listing_id)

            flash("Listing published.", "success")

            return redirect(
                url_for("listings.detail", listing_id=listing_id)
            )

    categories = db.get_db().query(
        """
        SELECT category_id, name
        FROM categories
        WHERE is_archived = 0
        ORDER BY name
        """
    )

    return render_template(
        "listings/form.html",
        categories=categories,
        listing=None,
        images=[],
        errors=errors if request.method == "POST" else {},
        form=request.form if request.method == "POST" else {}
    ), (400 if request.method == "POST" else 200)


@bp.route("/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit(listing_id):
    # Edit a listing owned by the logged-in user.
    listing = _get_owned_listing(listing_id)

    if listing is None:
        abort(403)

    if request.method == "POST":
        clean, errors = validate_listing(request.form)

        if not errors:
            db.get_db().execute(
                """
                UPDATE listings
                SET category_id = ?, title = ?, description = ?,
                    price = ?, condition = ?, location = ?, updated_at = ?
                WHERE listing_id = ?
                """,
                (
                    clean["category_id"],
                    clean["title"],
                    clean["description"],
                    clean["price"],
                    clean["condition"],
                    clean["location"],
                    now(),
                    listing_id
                )
            )

            # Replace existing photos only when the checkbox is selected.
            replace_images = (
                request.form.get("replace_images") == "1"
            )

            _save_uploaded_images(
                listing_id,
                replace_existing=replace_images
            )

            _save_uploaded_videos(listing_id)

            flash("Listing updated.", "success")

            return redirect(
                url_for("listings.detail", listing_id=listing_id)
            )

    categories = db.get_db().query(
        """
        SELECT category_id, name
        FROM categories
        WHERE is_archived = 0
        ORDER BY name
        """
    )

    # Retrieve only active photos for the edit page.
    images = db.get_db().query(
        """
        SELECT *
        FROM listing_images
        WHERE listing_id = ?
          AND is_archived = 0
        ORDER BY is_primary DESC, image_id
        """,
        (listing_id,)
    )

    listing["image_count"] = len(images)

    return render_template(
        "listings/form.html",
        categories=categories,
        listing=listing,
        images=images,
        errors=errors if request.method == "POST" else {},
        form=request.form if request.method == "POST" else listing
    )


@bp.route("/listings/<int:listing_id>/images/archive", methods=["POST"])
@login_required
def archive_images(listing_id):
    # Archive selected photos belonging to the current user's listing.
    listing = _get_owned_listing(listing_id)

    if listing is None:
        abort(403)

    selected_ids = request.form.getlist("image_ids")

    # Validate the selected image IDs.
    try:
        image_ids = list({
            int(image_id)
            for image_id in selected_ids
            if image_id
        })
    except (TypeError, ValueError):
        abort(400)

    if not image_ids or any(image_id <= 0 for image_id in image_ids):
        flash("Please select at least one photo to archive.", "warning")
        return redirect(
            url_for("listings.edit", listing_id=listing_id)
        )

    db_conn = db.get_db()
    placeholders = ",".join("?" for _ in image_ids)

    # Archive only selected active photos belonging to this listing.
    db_conn.execute(
        f"""
        UPDATE listing_images
        SET is_archived = 1,
            is_primary = 0
        WHERE listing_id = ?
          AND is_archived = 0
          AND image_id IN ({placeholders})
        """,
        (listing_id, *image_ids)
    )

    # Make another active photo primary if the previous primary was archived.
    db_conn.execute(
        """
        UPDATE listing_images
        SET is_primary = 1
        WHERE image_id = (
            SELECT image_id
            FROM listing_images
            WHERE listing_id = ?
              AND is_archived = 0
            ORDER BY image_id
            LIMIT 1
        )
        AND listing_id = ?
          AND is_archived = 0
          AND NOT EXISTS (
              SELECT 1
              FROM listing_images
              WHERE listing_id = ?
                AND is_archived = 0
                AND is_primary = 1
          )
        """,
        (listing_id, listing_id, listing_id)
    )

    flash("Selected photos archived successfully.", "success")

    return redirect(
        url_for("listings.edit", listing_id=listing_id)
    )


@bp.route("/listings/<int:listing_id>/status", methods=["POST"])
@login_required
def set_status(listing_id):
    # Archive, reactivate or mark a listing as sold.
    listing = _get_owned_listing(listing_id)

    if listing is None:
        abort(403)

    new_status = request.form.get("status", "")

    if new_status not in ("active", "archived", "sold"):
        abort(400)

    db.get_db().execute(
        """
        UPDATE listings
        SET status = ?, updated_at = ?
        WHERE listing_id = ?
        """,
        (new_status, now(), listing_id)
    )

    flash(f"Listing marked as {new_status}.", "success")

    return redirect(
        request.form.get("next")
        or url_for("listings.my_listings")
    )


@bp.route("/listings/<int:listing_id>")
def detail(listing_id):
    # Display listing details.
    listing = db.get_db().query(
        """
        SELECT l.*, c.name AS category_name,
               u.first_name AS seller_first_name,
               u.created_at AS seller_since
        FROM listings l
        JOIN categories c ON c.category_id = l.category_id
        JOIN users u ON u.user_id = l.user_id
        WHERE l.listing_id = ?
        """,
        (listing_id,),
        one=True
    )

    if listing is None:
        abort(404)

    user = current_user()

    if listing["status"] == "removed" and (
        user is None or user["role"] != "admin"
    ):
        abort(404)

    db_conn = db.get_db()

    # Display only active photos.
    images = db_conn.query(
        """
        SELECT *
        FROM listing_images
        WHERE listing_id = ?
          AND is_archived = 0
        ORDER BY is_primary DESC, image_id
        """,
        (listing_id,)
    )

    videos = db_conn.query(
        """
        SELECT *
        FROM listing_videos
        WHERE listing_id = ?
        ORDER BY video_id
        """,
        (listing_id,)
    )

    can_contact = (
        user is not None
        and user["user_id"] != listing["user_id"]
        and listing["status"] == "active"
    )

    already_saved = False

    if user:
        already_saved = bool(
            db_conn.query(
                """
                SELECT 1 AS x
                FROM favourites
                WHERE user_id = ? AND listing_id = ?
                """,
                (user["user_id"], listing_id),
                one=True
            )
        )

    return render_template(
        "listings/detail.html",
        listing=listing,
        images=images,
        videos=videos,
        can_contact=can_contact,
        already_saved=already_saved
    )


def _get_owned_listing(listing_id):
    # Return a listing only when it belongs to the current user.
    return db.get_db().query(
        """
        SELECT *
        FROM listings
        WHERE listing_id = ? AND user_id = ?
        """,
        (listing_id, current_user()["user_id"]),
        one=True
    )


def _save_uploaded_images(listing_id, replace_existing=False):
    # Save listing photos and optionally archive existing photos.
    cfg = current_app.config
    db_conn = db.get_db()

    files = [
        file for file in request.files.getlist("images")
        if file and file.filename
    ]

    # Retrieve only currently active photo records.
    existing_images = db_conn.query(
        """
        SELECT image_id, file_path
        FROM listing_images
        WHERE listing_id = ?
          AND is_archived = 0
        """,
        (listing_id,)
    )

    valid_files = []

    # Validate selected photos before changing existing photo records.
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()

        if ext not in cfg["ALLOWED_IMAGE_EXTENSIONS"]:
            flash(
                f"Skipped {file.filename}: only PNG, JPG, GIF or WEBP images are allowed.",
                "warning"
            )
            continue

        blob = file.read()

        if len(blob) > cfg["MAX_IMAGE_SIZE"]:
            flash(
                f"Skipped {file.filename}: image exceeds the 5 MB limit.",
                "warning"
            )
            continue

        if blob:
            valid_files.append((ext, blob))

    # Do not archive existing photos if no valid replacements were selected.
    if replace_existing:
        if not valid_files:
            flash(
                "No valid replacement photos were selected. "
                "Existing photos have been kept.",
                "warning"
            )
            return

        if len(valid_files) > cfg["MAX_IMAGES_PER_LISTING"]:
            flash(
                "You can select a maximum of 5 photos. "
                "Existing photos have been kept.",
                "warning"
            )
            return

    else:
        # Calculate how many additional photos can be uploaded.
        remaining = max(
            0,
            cfg["MAX_IMAGES_PER_LISTING"] - len(existing_images)
        )

        if remaining == 0 and valid_files:
            flash(
                "This listing already has the maximum of 5 photos.",
                "warning"
            )
            return

        if len(valid_files) > remaining:
            flash(
                f"Only {remaining} additional photo(s) can be uploaded.",
                "warning"
            )

            valid_files = valid_files[:remaining]

    if not valid_files:
        return

    # Save new image files.
    saved_files = []

    for ext, blob in valid_files:
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(str(cfg["UPLOAD_FOLDER"]), filename)

        with open(path, "wb") as output_file:
            output_file.write(blob)

        saved_files.append(filename)

    # Archive old photo records instead of permanently deleting them.
    if replace_existing:
        db_conn.execute(
            """
            UPDATE listing_images
            SET is_archived = 1,
                is_primary = 0
            WHERE listing_id = ?
              AND is_archived = 0
            """,
            (listing_id,)
        )

    # Insert the new photos as active records.
    for index, filename in enumerate(saved_files):
        db_conn.execute(
            """
            INSERT INTO listing_images
                (listing_id, file_path, is_primary, is_archived, uploaded_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (
                listing_id,
                filename,
                1 if index == 0 else 0,
                now()
            )
        )


def _save_uploaded_videos(listing_id):
    # Save valid listing videos.
    cfg = current_app.config
    files = request.files.getlist("videos")

    existing = db.get_db().query(
        """
        SELECT COUNT(*) AS n
        FROM listing_videos
        WHERE listing_id = ?
        """,
        (listing_id,),
        one=True
    )["n"]

    remaining = cfg["MAX_VIDEOS_PER_LISTING"] - existing

    if remaining <= 0:
        if any(file and file.filename for file in files):
            flash(
                "Maximum of 3 videos allowed per listing.",
                "warning"
            )
        return

    for file in files[:remaining]:
        if not file or not file.filename:
            continue

        ext = os.path.splitext(file.filename)[1].lower()

        if ext not in cfg["ALLOWED_VIDEO_EXTENSIONS"]:
            flash(
                f"Skipped {file.filename}: unsupported video format.",
                "warning"
            )
            continue

        blob = file.read()

        if len(blob) > cfg["MAX_VIDEO_SIZE"]:
            flash(
                f"Skipped {file.filename}: video exceeds the 50 MB limit.",
                "warning"
            )
            continue

        if not blob:
            continue

        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(str(cfg["UPLOAD_FOLDER"]), filename)

        with open(path, "wb") as output_file:
            output_file.write(blob)

        db.get_db().execute(
            """
            INSERT INTO listing_videos
                (listing_id, file_path, uploaded_at)
            VALUES (?, ?, ?)
            """,
            (listing_id, filename, now())
        )
