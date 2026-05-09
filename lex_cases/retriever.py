from __future__ import annotations

from .indexer import TABLE_NAME


class LexCaseRetriever:
    def __init__(self, db_path: str = "lancedb", embedding_provider=None):
        self._db_path = db_path
        self._embedding_provider = embedding_provider
        self._db = None
        self._embedder = None

    def _get_db(self):
        if self._db is None:
            import lancedb
            self._db = lancedb.connect(self._db_path)
        return self._db

    def _get_embedder(self):
        if self._embedder is None:
            if self._embedding_provider is not None:
                self._embedder = self._embedding_provider
            else:
                from lex_retriever.embeddings import get_embedding_provider
                self._embedder = get_embedding_provider()
        return self._embedder

    def search(
        self,
        query: str,
        courts: list[str] | None = None,
        laws_cited: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Semantic search over Leitsätze."""
        raise NotImplementedError("search — implemented in SUB-4")

    def get_case_fulltext(self, url: str) -> str:
        """Live HTTP fetch of Tatbestand + Entscheidungsgründe."""
        raise NotImplementedError("get_case_fulltext — implemented in SUB-4")

    def get_cases_citing_law(self, law: str, paragraph: str) -> list[dict]:
        """Filter by laws_cited containing e.g. '§ 823 BGB'."""
        raise NotImplementedError("get_cases_citing_law — implemented in SUB-4")
