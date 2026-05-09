"""Tests for retriever search logic with a mock LanceDB table."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lex_cases.retriever import LexCaseRetriever


def _mock_df():
    return pd.DataFrame([
        {
            "court": "BGH", "az": "IV ZR 1/24", "date": "2024-01-01",
            "type": "Urteil", "chunk_type": "leitsatz",
            "text": "Produzentenhaftung nach § 823 BGB.",
            "laws_cited": ["§ 823 BGB", "§ 280 BGB"],
            "url": "https://example.com/1",
            "_distance": 0.1,
        },
        {
            "court": "BAG", "az": "1 AZR 5/24", "date": "2024-03-01",
            "type": "Urteil", "chunk_type": "leitsatz",
            "text": "Arbeitsrecht Kuendigung.",
            "laws_cited": ["§ 1 KSchG"],
            "url": "https://example.com/2",
            "_distance": 0.4,
        },
    ])


def _make_mock_table(df):
    mock_query = MagicMock()
    mock_query.metric.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.to_pandas.return_value = df

    mock_table = MagicMock()
    mock_table.search.return_value = mock_query
    mock_table.to_pandas.return_value = df
    return mock_table


@patch("lex_cases.retriever._embed", return_value=[0.1] * 384)
@patch("lex_cases.retriever._get_table")
@patch("lex_cases.retriever._get_db")
def test_search_returns_results(mock_db, mock_table_fn, mock_embed):
    df = _mock_df()
    mock_table_fn.return_value = _make_mock_table(df)
    retriever = LexCaseRetriever()
    results = retriever.search("Produzentenhaftung", top_k=10)
    assert len(results) == 2
    assert results[0]["court"] in ("BGH", "BAG")


@patch("lex_cases.retriever._embed", return_value=[0.1] * 384)
@patch("lex_cases.retriever._get_table")
@patch("lex_cases.retriever._get_db")
def test_search_filter_by_court(mock_db, mock_table_fn, mock_embed):
    df = _mock_df()
    mock_table_fn.return_value = _make_mock_table(df)
    retriever = LexCaseRetriever()
    results = retriever.search("Haftung", courts=["BGH"], top_k=10)
    assert all(r["court"] == "BGH" for r in results)


@patch("lex_cases.retriever._get_table")
@patch("lex_cases.retriever._get_db")
def test_get_cases_citing_law(mock_db, mock_table_fn):
    df = _mock_df()
    mock_table = MagicMock()
    mock_table.to_pandas.return_value = df
    mock_table_fn.return_value = mock_table
    retriever = LexCaseRetriever()
    results = retriever.get_cases_citing_law("BGB", "§ 823")
    assert any(r["az"] == "IV ZR 1/24" for r in results)


@patch("lex_cases.retriever._embed", return_value=[0.1] * 384)
@patch("lex_cases.retriever._get_table")
@patch("lex_cases.retriever._get_db")
def test_search_result_has_required_keys(mock_db, mock_table_fn, mock_embed):
    df = _mock_df()
    mock_table_fn.return_value = _make_mock_table(df)
    retriever = LexCaseRetriever()
    results = retriever.search("test")
    for r in results:
        for key in ("court", "az", "date", "type", "leitsatz", "laws_cited", "score", "url"):
            assert key in r
