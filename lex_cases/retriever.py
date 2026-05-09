"""Retriever: semantic search + on-demand fulltext fetch for German court decisions."""

from __future__ import annotations

import logging
from functools import lru_cache

from .indexer import TABLE_NAME, LANCE_PATH

log = logging.getLogger(__name__)


class LexCaseRetriever:
    def __init__(self, db_path: str = LANCE_PATH, embedding_provider=None):
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

    def _get_table(self):
        db = self._get_db()
        if TABLE_NAME not in db.table_names():
            raise RuntimeError(
                f"LanceDB table '{TABLE_NAME}' not found. "
                "Run: python -m lex_cases index-all"
            )
        return db.open_table(TABLE_NAME)

    def search(
        self,
        query: str,
        courts: list[str] | None = None,
        laws_cited: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Semantic search over Leitsätze and Tenor in the LanceDB index."""
        embedder = self._get_embedder()
        query_vec = embedder.embed([query])[0]

        table = self._get_table()
        search = table.search(query_vec).limit(top_k * 4)

        filters: list[str] = []
        if courts:
            quoted = ", ".join(f"'{c}'" for c in courts)
            filters.append(f"court IN ({quoted})")
        if date_from:
            filters.append(f"date >= '{date_from}'")
        if date_to:
            filters.append(f"date <= '{date_to}'")

        if filters:
            search = search.where(" AND ".join(filters))

        raw_results = search.to_list()

        if laws_cited:
            filtered = []
            for row in raw_results:
                row_laws = row.get("laws_cited") or []
                if any(lc in row_laws for lc in laws_cited):
                    filtered.append(row)
            raw_results = filtered

        seen_az: set[str] = set()
        output: list[dict] = []
        for row in raw_results:
            az = row.get("az", "")
            if az in seen_az:
                continue
            seen_az.add(az)

            leitsatz = ""
            if row.get("chunk_type") == "leitsatz":
                leitsatz = row.get("text", "")

            output.append({
                "court":      row.get("court", ""),
                "az":         az,
                "date":       row.get("date", ""),
                "type":       row.get("type", ""),
                "leitsatz":   leitsatz,
                "laws_cited": row.get("laws_cited") or [],
                "score":      float(row.get("_distance", 0.0)),
                "url":        row.get("url", ""),
            })
            if len(output) >= top_k:
                break

        return output

    def get_case_fulltext(self, url: str) -> str:
        """Live HTTP fetch of Tatbestand + Entscheidungsgründe from rechtsprechung-im-internet.de."""
        import requests
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def _fetch(u: str) -> str:
            resp = requests.get(u, timeout=30, headers={"Accept": "text/xml, text/html"})
            resp.raise_for_status()
            return resp.text

        raw = _fetch(url)

        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(raw)
            parts = []
            for tag in ("tatbestand", "entscheidungsgruende", "gruende"):
                el = root.find(tag)
                if el is not None and el.text:
                    parts.append(el.text.strip())
            if parts:
                return "\n\n".join(parts)
        except ET.ParseError:
            pass

        from html.parser import HTMLParser

        class _Extractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self._capture = False
                self._parts: list[str] = []

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                cls = attrs_dict.get("class", "")
                if any(k in cls for k in ("tatbestand", "gruende", "entscheidungsgruende")):
                    self._capture = True

            def handle_data(self, data):
                if self._capture:
                    self._parts.append(data)

            def result(self) -> str:
                return "\n".join(self._parts).strip()

        parser = _Extractor()
        parser.feed(raw)
        text = parser.result()
        return text if text else raw

    def get_cases_citing_law(self, law: str, paragraph: str) -> list[dict]:
        """Return all indexed cases whose laws_cited contains '<paragraph> <law>'."""
        search_str = f"{paragraph} {law}".strip()
        table = self._get_table()

        try:
            rows = (
                table.search()
                     .where(f"array_has(laws_cited, '{search_str}')")
                     .limit(999_999)
                     .to_list()
            )
        except Exception:
            all_rows = table.to_pandas().to_dict("records")
            rows = [r for r in all_rows if search_str in (r.get("laws_cited") or [])]

        return [
            {
                "court":      r.get("court", ""),
                "az":         r.get("az", ""),
                "date":       r.get("date", ""),
                "type":       r.get("type", ""),
                "leitsatz":   r.get("text", "") if r.get("chunk_type") == "leitsatz" else "",
                "laws_cited": r.get("laws_cited") or [],
                "score":      1.0,
                "url":        r.get("url", ""),
            }
            for r in rows
        ]
