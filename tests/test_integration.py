import pytest

pytestmark = pytest.mark.requires_db


@pytest.mark.requires_db
def test_index_bgh_smoke():
    """Smoke test: index BGH and verify table has rows."""
    pytest.skip("requires_db — run manually after indexing")


@pytest.mark.requires_db
def test_search_returns_results():
    """Integration: search over real BGH index."""
    pytest.skip("requires_db — run manually after indexing")
