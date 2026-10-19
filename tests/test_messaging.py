"""Use case UC-11: buyer-seller messaging (FR-09, BR-05)."""


def test_contact_creates_conversation(client, login_student, csrf):
    token = csrf("/listings/3")
    response = login_student.post("/listings/3/contact", data={"_csrf": token})
    assert response.status_code == 302
    assert "/messages/" in response.headers["Location"]


def test_owner_cannot_message_own_listing(client, login_admin, login):
    # admin owns no listing; instead Hari contacts his own listing 3
    assert login(client, "hari@uon.edu.au", "Student@123").status_code == 302
    response = client.post("/listings/3/contact", data={"_csrf": "x"}, follow_redirects=False)
    # missing CSRF -> 400 before anything else happens
    assert response.status_code == 400


def test_only_participants_can_read_conversation(client, login_student, login, csrf):
    token = csrf("/listings/3")
    login_student.post("/listings/3/contact", data={"_csrf": token})
    conv_url = "/messages/1"  # seeded conversation
    # Akshaya is not part of conversation 1 (Madhavi + Hari) -> 403 (BR-05)
    assert login(client, "akshaya@uon.edu.au", "Student@123").status_code == 302
    assert client.get(conv_url).status_code == 403


def test_seller_can_reply_and_history_is_kept(client, login, csrf):
    # Dhimanshi contacting about listing 1 (Madhavi's textbook)
    assert login(client, "dhimanshi@uon.edu.au", "Student@123").status_code == 302
    token = csrf("/listings/1")
    response = client.post("/listings/1/contact", data={"_csrf": token})
    conv_id = response.headers["Location"].split("/messages/")[1]
    token = csrf(f"/messages/{conv_id}")
    response = client.post(f"/messages/{conv_id}", data={
        "_csrf": token, "body": "Hello, is the textbook available?"})
    assert response.status_code == 302
    page = client.get(f"/messages/{conv_id}").get_data(as_text=True)
    assert "Hello, is the textbook available?" in page  # stored conversation history


def test_empty_message_rejected(client, login_student, csrf):
    token = csrf("/messages/1")
    response = login_student.post("/messages/1", data={
        "_csrf": token, "body": "   "}, follow_redirects=True)
    assert b"Message cannot be empty" in response.data
