
"""Use case UC-09: keyword search, category filter and price range (FR-06/07)."""


def test_keyword_search_finds_matching_listing(client):
    response = client.get("/listings?q=laptop")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "HP laptop" in page
    assert "STAT1070" not in page


def test_keyword_search_no_results(client):
    response = client.get("/listings?q=helicopter")

    assert response.status_code == 200
    assert "No listings match" in response.get_data(as_text=True)


def test_category_filter(client):
    response = client.get("/listings?category=5")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "STAT1070" in page
    assert "HP laptop" not in page


def test_price_range_filter(client):
    response = client.get("/listings?min_price=100&max_price=200")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Mountain bike" in page
    assert "HP laptop" not in page


def test_sort_by_price_ascending(client):
    response = client.get("/listings?sort=price_asc")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Free moving boxes" in page
    assert "Study desk" in page
    assert page.index("Free moving boxes") < page.index("Study desk")


def test_home_shows_active_listings_only(client):
    response = client.get("/")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Latest listings" in page
