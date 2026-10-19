"""Use cases UC-05 to UC-08: create/edit/archive/delete listings (FR-04..05, BR-02/04)."""
import io


def png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (0, 154, 68)).save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_create_listing_success(client, login_student, new_listing):
    page = login_student.get(f"/listings/{new_listing}").get_data(as_text=True)
    assert "Test gaming chair" in page
    assert "88.50" in page


def test_create_listing_missing_fields_rejected(client, login_student, csrf):
    token = csrf("/listings/new")
    response = login_student.post("/listings/new", data={
        "_csrf": token, "title": "abc",  # too short + no description etc.
        "description": "too short", "price": "-5", "category_id": "",
        "condition": "Bogus",
    })
    assert response.status_code == 400


def test_edit_listing_by_owner(client, login_student, new_listing, csrf):
    token = csrf(f"/listings/{new_listing}/edit")
    response = login_student.post(f"/listings/{new_listing}/edit", data={
        "_csrf": token, "title": "Updated chair title",
        "description": "A comfortable gaming chair used for one year, all functions working.",
        "price": "70", "category_id": "1", "condition": "Good", "location": "Callaghan",
    })
    assert response.status_code == 302
    page = login_student.get(f"/listings/{new_listing}").get_data(as_text=True)
    assert "Updated chair title" in page


def test_edit_listing_by_other_user_forbidden(client, login_student, login, new_listing):
    # Dhimanshi (another student) cannot edit Madhavi's listing (BR-02).
    assert login(client, "dhimanshi@uon.edu.au", "Student@123").status_code == 302
    assert client.get(f"/listings/{new_listing}/edit").status_code == 403


def test_archive_hides_listing_from_browse(client, login_student, new_listing, csrf):
    token = csrf("/my-listings")
    login_student.post(f"/listings/{new_listing}/status", data={
        "_csrf": token, "status": "archived"})
    page = login_student.get("/listings").get_data(as_text=True)
    assert "Test gaming chair" not in page  # BR-10: archived hidden from browsing
    mine = login_student.get("/my-listings").get_data(as_text=True)
    assert "Test gaming chair" in mine       # preserved for the owner


def test_image_upload_and_display(client, login_student, csrf):
    token = csrf("/listings/new")
    response = login_student.post("/listings/new", data={
        "_csrf": token, "title": "Photo listing item",
        "description": "A valid description of at least twenty characters.",
        "price": "10", "category_id": "1", "condition": "New", "location": "",
        "images": [(png_bytes(), "photo.png")],
    }, content_type="multipart/form-data", follow_redirects=False)
    assert response.status_code == 302
    listing_id = response.headers["Location"].split("/listings/")[1]
    page = login_student.get(f"/listings/{listing_id}").get_data(as_text=True)
    assert "uploads/" in page


def test_disallowed_file_type_rejected(client, login_student, csrf):
    token = csrf("/listings/new")
    response = login_student.post("/listings/new", data={
        "_csrf": token, "title": "Bad file item",
        "description": "A valid description of at least twenty characters.",
        "price": "10", "category_id": "1", "condition": "New",
        "images": [(io.BytesIO(b"malicious"), "script.exe")],
    }, content_type="multipart/form-data")
    assert response.status_code == 302
    listing_id = response.headers["Location"].split("/listings/")[1]
    page = login_student.get(f"/listings/{listing_id}").get_data(as_text=True)
    assert "uploads/" not in page  # the exe was never stored


def test_delete_listing(client, login_student, new_listing, csrf):
    token = csrf("/my-listings")
    response = login_student.post(f"/listings/{new_listing}/delete", data={"_csrf": token})
    assert response.status_code == 302
    assert login_student.get(f"/listings/{new_listing}").status_code == 404
