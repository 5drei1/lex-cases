"""Integration tests — require a populated LanceDB index."""

import pytest

pytestmark = pytest.mark.requires_db


def test_search_bgh_produzentenhaftung():
    from lex_cases import search_case_law
    results = search_case_law("Produzentenhaftung", courts=["BGH"], top_k=5)
    assert len(results) > 0
    assert all(r["court"] == "BGH" for r in results)


def test_get_cases_citing_paragraph_823():
    from lex_cases import get_cases_citing_law
    results = get_cases_citing_law("BGB", "§ 823")
    assert isinstance(results, list)
