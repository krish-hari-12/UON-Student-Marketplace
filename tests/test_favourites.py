"""Use case UC-10: save and remove favourites (FR-08, BR-03)."""


def test_favourite_requires_login(client):
    assert client.post("/listings/1/favourite").status_code == 400  # CSRF guard rejects the bare POST
    assert client.get("/favourites").status_code == 302


def test_toggle_adds_then_removes(client, login_student, csrf):
    token = csrf("/listings/1")
    response = login_student.post("/listings/1/favourite", data={
        "_csrf": token, "next": "/favourites"}, follow_redirects=True)
    assert b"Saved to favourites" in response.data
    page = login_student.get("/favourites").get_data(as_text=True)
    assert "STAT1070" in page

    token = csrf("/listings/1")
    response = login_student.post("/listings/1/favourite", data={
        "_csrf": token, "next": "/favourites"}, follow_redirects=True)
    assert b"Removed from favourites" in response.data
    page = login_student.get("/favourites").get_data(as_text=True)
    assert "STAT1070" not in page


def test_seed_favourites_visible(client, login_student):
    # Madhavi has 2 seeded favourites (laptop + monitor)
    page = login_student.get("/favourites").get_data(as_text=True)
    assert "HP laptop" in page and "27-inch monitor" in page
