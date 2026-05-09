"""Indexer: download, parse, embed, and store court decisions in LanceDB."""

from __future__ import annotations

import hashlib
import logging
from typing import Iterator

import pyarrow as pa
from tqdm import tqdm

from .providers.base import CaseProvider, RawCase
from .providers.rechtsprechung_im_internet import RechtsprechungImInternetProvider

logger = logging.getLogger(__name__)

TABLE_NAME = "german_cases"

_CASE_SCHEMA = pa.schema([
    pa.field("id",         pa.string()),
    pa.field("court",      pa.string()),
    pa.field("az",         pa.string()),
    pa.field("date",       pa.string()),
    pa.field("type",       pa.string()),
    pa.field("chunk_type", pa.string()),
    pa.field("text",       pa.string()),
    pa.field("laws_cited", pa.list_(pa.string())),
    pa.field("url",        pa.string()),
    pa.field("vector",     pa.list_(pa.float32())),
])

_EMBED_BATCH_SIZE = 16  # mirrors lex-retriever Mistral batching fix d07b0c6


def make_case_id(court: str, az: str, chunk_idx: int) -> str:
    return hashlib.sha1(f"{court}|{az}|{chunk_idx}".encode()).hexdigest()


def _get_db(db_path: str = "lancedb"):
    import lancedb
    return lancedb.connect(db_path)


def _get_table(db):
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        return db.create_table(TABLE_NAME, schema=_CASE_SCHEMA)


def _get_provider() -> CaseProvider:
    return RechtsprechungImInternetProvider()


def _embed_texts(texts: list[str]) -> list[list[float]]:
    from lex_retriever.embeddings import get_embedding_provider
    provider = get_embedding_provider()
    vectors = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i:i + _EMBED_BATCH_SIZE]
        vectors.extend(provider.embed(batch))
    return vectors


def _existing_ids(table) -> set[str]:
    try:
        rows = table.to_pandas(columns=["id"])
        return set(rows["id"].tolist())
    except Exception:
        return set()


def _cases_to_rows(cases: Iterator[RawCase], existing: set[str]) -> list[dict]:
    rows: list[dict] = []
    pending_texts: list[str] = []
    pending_meta: list[dict] = []

    def _flush() -> None:
        if not pending_texts:
            return
        vectors = _embed_texts(pending_texts)
        for meta, vec in zip(pending_meta, vectors):
            rows.append({**meta, "vector": vec})
        pending_texts.clear()
        pending_meta.clear()

    for case in tqdm(cases, desc="Indexing chunks", unit="chunk"):
        if case.id in existing:
            continue
        pending_texts.append(case.text)
        pending_meta.append({
            "id":         case.id,
            "court":      case.court,
            "az":         case.az,
            "date":       case.date,
            "type":       case.type,
            "chunk_type": case.chunk_type,
            "text":       case.text,
            "laws_cited": case.laws_cited,
            "url":        case.url,
        })
        if len(pending_texts) >= _EMBED_BATCH_SIZE:
            _flush()

    _flush()
    return rows


def index_court(court: str, db_path: str = "lancedb") -> int:
    """Download, embed, and index all decisions for one court. Returns rows added."""
    db = _get_db(db_path)
    table = _get_table(db)
    existing = _existing_ids(table)
    provider = _get_provider()

    logger.info("Indexing %s (existing=%d)", court, len(existing))
    cases = provider.fetch_cases(court)
    rows = _cases_to_rows(cases, existing)

    if rows:
        table.add(rows)
        logger.info("Added %d rows for %s", len(rows), court)
    else:
        logger.info("No new rows for %s", court)

    return len(rows)


def index_all_courts(db_path: str = "lancedb") -> dict[str, int]:
    """Index all supported courts. Returns {court: rows_added}."""
    from .providers.rechtsprechung_im_internet import _COURT_CATALOG
    results = {}
    for court in _COURT_CATALOG:
        results[court] = index_court(court, db_path)
    return results


def index_status(db_path: str = "lancedb") -> dict[str, int]:
    """Return count of indexed entries per court."""
    db = _get_db(db_path)
    try:
        table = db.open_table(TABLE_NAME)
        df = table.to_pandas(columns=["court"])
        return df["court"].value_counts().to_dict()
    except Exception:
        return {}
