"""Tests for indexer schema, chunk IDs, and batching logic."""

import hashlib

import pytest

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
    from lex_cases.indexer import _EMBED_BATCH_SIZE
    assert _EMBED_BATCH_SIZE == 16
