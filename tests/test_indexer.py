"""Tests for indexer schema, chunk IDs, batching, and checkpoint logic."""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from lex_cases.indexer import (
    _EMBED_BATCH_SIZE,
    _cases_to_rows,
    make_case_id,
)
from lex_cases.providers.base import RawCase


def test_rawcase_id_deterministic():
    case = RawCase(
        court="BGH",
        az="IV ZR 123/24",
        date="2024-11-15",
        type="Urteil",
        chunk_type="leitsatz",
        text="Der Schuldner haftet.",
    )
    expected = hashlib.sha1(b"BGH:IV ZR 123/24:leitsatz").hexdigest()
    assert case.id == expected


def test_rawcase_id_differs_by_chunk_type():
    base = dict(court="BGH", az="IV ZR 1/24", date="2024-01-01", type="Urteil", text="x")
    leitsatz = RawCase(**base, chunk_type="leitsatz")
    tenor = RawCase(**base, chunk_type="tenor")
    assert leitsatz.id != tenor.id


def test_rawcase_defaults():
    case = RawCase(
        court="BAG", az="1 AZR 1/24", date="2024-06-01",
        type="Beschluss", chunk_type="leitsatz", text="Test"
    )
    assert case.laws_cited == []
    assert case.url == ""


def test_embed_batch_size_constant():
    assert _EMBED_BATCH_SIZE == 16


def test_make_case_id_deterministic():
    result = make_case_id("BGH", "IV ZR 123/24", 0)
    expected = hashlib.sha1(b"BGH|IV ZR 123/24|0").hexdigest()
    assert result == expected


def test_make_case_id_differs_by_chunk_idx():
    id0 = make_case_id("BGH", "IV ZR 1/24", 0)
    id1 = make_case_id("BGH", "IV ZR 1/24", 1)
    assert id0 != id1


def test_make_case_id_differs_by_court():
    assert make_case_id("BGH", "1/24", 0) != make_case_id("BAG", "1/24", 0)


def _make_cases(n: int) -> list[RawCase]:
    return [
        RawCase(
            court="BGH",
            az=f"IV ZR {i}/24",
            date="2024-01-01",
            type="Urteil",
            chunk_type="leitsatz",
            text=f"Text {i}",
        )
        for i in range(n)
    ]


@patch("lex_cases.indexer._embed_texts")
def test_checkpoint_skips_existing_ids(mock_embed):
    mock_embed.return_value = [[0.1] * 4]
    cases = _make_cases(3)
    existing = {cases[0].id, cases[1].id}  # first two already indexed
    rows = _cases_to_rows(iter(cases), existing)
    assert len(rows) == 1
    assert rows[0]["az"] == "IV ZR 2/24"


@patch("lex_cases.indexer._embed_texts")
def test_batching_calls_embed_with_batch_size(mock_embed):
    # Capture lengths via side_effect — pending_texts.clear() would mutate call_args refs
    batch_sizes: list[int] = []

    def capture(texts):
        batch_sizes.append(len(texts))
        return [[0.0] * 4] * len(texts)

    mock_embed.side_effect = capture
    cases = _make_cases(_EMBED_BATCH_SIZE * 2)
    _cases_to_rows(iter(cases), set())
    assert mock_embed.call_count == 2
    assert all(s == _EMBED_BATCH_SIZE for s in batch_sizes)


@patch("lex_cases.indexer._embed_texts")
def test_batching_remainder_flushed(mock_embed):
    n = _EMBED_BATCH_SIZE + 5
    batch_sizes: list[int] = []

    def capture(texts):
        batch_sizes.append(len(texts))
        return [[0.0] * 4] * len(texts)

    mock_embed.side_effect = capture
    cases = _make_cases(n)
    rows = _cases_to_rows(iter(cases), set())
    assert len(rows) == n
    assert mock_embed.call_count == 2
    assert batch_sizes[0] == _EMBED_BATCH_SIZE
    assert batch_sizes[1] == 5
