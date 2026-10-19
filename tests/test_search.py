"""Use case UC-09: keyword search, category filter and price range (FR-06/07)."""


def test_keyword_search_finds_matching_listing(client):
    page = client.get("/listings?q=laptop").get_data(as_text=True)
    assert "HP laptop" in page
    assert "STAT1070" not in page


def test_keyword_search_no_results(client):
    page = client.get("/listings?q=helicopter").get_data(as_text=True)
    assert "No listings match" in page


def test_category_filter(client):
    page = client.get("/listings?category=5").get_data(as_text=True)  # Textbooks
    assert "STAT1070" in page
    assert "HP laptop" not in page


def test_price_range_filter(client):
    page = client.get("/listings?min_price=100&max_price=200").get_data(as_text=True)
    assert "Mountain bike" in page
    assert "HP laptop" not in page  # $620 outside the range


def test_sort_by_price_ascending(client):
    page = client.get("/listings?sort=price_asc").get_data(as_text=True)
    assert page.index("Free moving boxes") < page.index("Study desk")


def test_home_shows_active_listings_only(client):
    page = client.get("/").get_data(as_text=True)
    assert "Latest listings" in page
