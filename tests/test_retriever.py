import pytest
from unittest.mock import MagicMock, patch
from lex_cases.retriever import LexCaseRetriever


def test_retriever_init():
    r = LexCaseRetriever(db_path="lancedb", embedding_provider=MagicMock())
    assert r._db_path == "lancedb"


# Full search/filter tests added in SUB-4 after implementation
