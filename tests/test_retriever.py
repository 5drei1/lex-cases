"""Tests for LexCaseRetriever."""

from unittest.mock import MagicMock, patch
import pytest

from lex_cases.retriever import LexCaseRetriever


def _make_mock_row(court="BGH", az="IV ZR 1/24", date="2024-01-15",
                   chunk_type="leitsatz", laws_cited=None, score=0.1):
    return {
        "id":         "abc",
        "court":      court,
        "az":         az,
        "date":       date,
        "type":       "Urteil",
        "chunk_type": chunk_type,
        "text":       "Der Schuldner haftet...",
        "laws_cited": laws_cited or ["§ 280 BGB"],
        "url":        "https://example.com/case",
        "_distance":  score,
    }


def _make_retriever_with_mock_table(rows):
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1] * 10]

    mock_search_result = MagicMock()
    mock_search_result.limit.return_value = mock_search_result
    mock_search_result.where.return_value = mock_search_result
    mock_search_result.to_list.return_value = rows

    mock_table = MagicMock()
    mock_table.search.return_value = mock_search_result

    mock_db = MagicMock()
    mock_db.table_names.return_value = ["german_cases"]
    mock_db.open_table.return_value = mock_table

    r = LexCaseRetriever(db_path="/fake", embedding_provider=mock_embedder)
    r._db = mock_db
    return r, mock_table, mock_embedder


def test_search_returns_results():
    rows = [_make_mock_row()]
    r, _, embedder = _make_retriever_with_mock_table(rows)
    results = r.search("Produzentenhaftung")
    assert len(results) == 1
    assert results[0]["court"] == "BGH"
    assert results[0]["az"] == "IV ZR 1/24"


def test_search_deduplicates_by_az():
    rows = [
        _make_mock_row(chunk_type="leitsatz"),
        _make_mock_row(chunk_type="tenor"),
    ]
    r, _, _ = _make_retriever_with_mock_table(rows)
    results = r.search("query")
    assert len(results) == 1


def test_search_applies_court_filter():
    rows = [_make_mock_row(court="BGH"), _make_mock_row(court="BAG", az="BAG 1/24")]
    r, mock_table, _ = _make_retriever_with_mock_table(rows)
    search_obj = mock_table.search.return_value
    r.search("query", courts=["BGH"])
    search_obj.where.assert_called_once()
    call_arg = search_obj.where.call_args[0][0]
    assert "BGH" in call_arg


def test_search_applies_date_filters():
    rows = [_make_mock_row()]
    r, mock_table, _ = _make_retriever_with_mock_table(rows)
    search_obj = mock_table.search.return_value
    r.search("query", date_from="2024-01-01", date_to="2024-12-31")
    search_obj.where.assert_called_once()
    call_arg = search_obj.where.call_args[0][0]
    assert "2024-01-01" in call_arg
    assert "2024-12-31" in call_arg


def test_search_laws_cited_filter():
    rows = [
        _make_mock_row(az="case1", laws_cited=["§ 280 BGB"]),
        _make_mock_row(az="case2", laws_cited=["§ 823 BGB"]),
    ]
    r, _, _ = _make_retriever_with_mock_table(rows)
    results = r.search("query", laws_cited=["§ 280 BGB"])
    assert len(results) == 1
    assert results[0]["az"] == "case1"


def test_search_result_format():
    rows = [_make_mock_row()]
    r, _, _ = _make_retriever_with_mock_table(rows)
    result = r.search("query")[0]
    for key in ("court", "az", "date", "type", "leitsatz", "laws_cited", "score", "url"):
        assert key in result, f"Missing key: {key}"


def test_get_cases_citing_law_array_has():
    mock_search = MagicMock()
    mock_search.where.return_value = mock_search
    mock_search.limit.return_value = mock_search
    mock_search.to_list.return_value = [_make_mock_row(laws_cited=["§ 280 BGB"])]

    mock_table = MagicMock()
    mock_table.search.return_value = mock_search

    mock_db = MagicMock()
    mock_db.table_names.return_value = ["german_cases"]
    mock_db.open_table.return_value = mock_table

    r = LexCaseRetriever(db_path="/fake", embedding_provider=MagicMock())
    r._db = mock_db

    results = r.get_cases_citing_law("BGB", "§ 280")
    assert len(results) == 1
    mock_search.where.assert_called_once()
    assert "§ 280 BGB" in mock_search.where.call_args[0][0]


def test_retriever_raises_when_no_index():
    mock_db = MagicMock()
    mock_db.table_names.return_value = []
    r = LexCaseRetriever(db_path="/fake", embedding_provider=MagicMock())
    r._db = mock_db
    with pytest.raises(RuntimeError, match="not found"):
        r.search("query")
