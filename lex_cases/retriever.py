"""Retriever: semantic search and on-demand fulltext fetch for court decisions."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_TABLE_NAME = "german_cases"
_EMBED_BATCH_SIZE = 16


def _get_db():
    import lancedb
    return lancedb.connect("lancedb")


def _get_table(db):
    return db.open_table(_TABLE_NAME)


def _embed(text: str) -> list[float]:
    from lex_retriever.embeddings import get_embedding_provider
    return get_embedding_provider().embed([text])[0]


class LexCaseRetriever:
    def search(
        self,
        query: str,
        courts: list[str] | None = None,
        laws_cited: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Semantic search over indexed Leitsätze."""
        db = _get_db()
        table = _get_table(db)
        vector = _embed(query)

        results = (
            table.search(vector)
            .metric("cosine")
            .limit(top_k * 4)
            .to_pandas()
        )

        if courts:
            courts_upper = [c.upper() for c in courts]
            results = results[results["court"].isin(courts_upper)]

        if laws_cited:
            def _has_law(row_laws):
                return any(law in row_laws for law in laws_cited)
            results = results[results["laws_cited"].apply(_has_law)]

        if date_from:
            results = results[results["date"] >= date_from]
        if date_to:
            results = results[results["date"] <= date_to]

        results = results.head(top_k)

        out = []
        for _, row in results.iterrows():
            out.append({
                "court":      row["court"],
                "az":         row["az"],
                "date":       row["date"],
                "type":       row["type"],
                "leitsatz":   row["text"],
                "laws_cited": list(row["laws_cited"]),
                "score":      float(1.0 - row.get("_distance", 0.0)),
                "url":        row["url"],
            })
        return out

    def get_case_fulltext(self, url: str) -> str:
        """Fetch and parse full case text (Tatbestand + Gründe) on demand."""
        import requests
        from lxml import etree

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        tree = etree.fromstring(resp.content)
        sections = []
        for tag in ("tatbestand", "entscheidungsgruende", "gruende"):
            nodes = tree.findall(f".//{tag}")
            for node in nodes:
                text = "".join(node.itertext()).strip()
                if text:
                    sections.append(text)

        if not sections:
            # fallback: strip all tags
            sections = [" ".join(tree.itertext()).strip()]

        return "\n\n".join(sections)

    def get_cases_citing_law(self, law: str, paragraph: str) -> list[dict]:
        """Return all indexed decisions that cite a specific law paragraph."""
        db = _get_db()
        table = _get_table(db)

        search_term = f"{paragraph} {law}".strip()
        df = table.to_pandas()
        mask = df["laws_cited"].apply(
            lambda laws: any(search_term in l or law in l for l in laws)
        )
        df = df[mask]

        out = []
        for _, row in df.iterrows():
            out.append({
                "court":      row["court"],
                "az":         row["az"],
                "date":       row["date"],
                "type":       row["type"],
                "leitsatz":   row["text"],
                "laws_cited": list(row["laws_cited"]),
                "score":      1.0,
                "url":        row["url"],
            })
        return out
