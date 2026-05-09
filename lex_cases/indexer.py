"""Indexer: fetch court decisions from providers and store in LanceDB."""

from __future__ import annotations

import hashlib
import logging
import os

import pyarrow as pa

log = logging.getLogger(__name__)

TABLE_NAME = "german_cases"
_BATCH_SIZE = 16  # Mistral API batch limit (fix d07b0c6 equivalent)
LANCE_PATH = os.environ.get("LANCE_PATH", os.path.join(os.path.dirname(__file__), "..", "lancedb"))

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


def make_case_id(court: str, az: str, chunk_idx: int) -> str:
    return hashlib.sha1(f"{court}|{az}|{chunk_idx}".encode()).hexdigest()


def _open_or_create_table(db, rows_first_batch: list[dict]):
    """Open existing table or create it with the first batch."""
    if TABLE_NAME in db.table_names():
        return db.open_table(TABLE_NAME)
    return db.create_table(TABLE_NAME, data=rows_first_batch)


def index_court(court: str, db_path: str = LANCE_PATH, embedding_config: dict | None = None) -> int:
    """Index all decisions (Leitsatz + Tenor) for a single court.

    Returns number of newly indexed chunks (skips already-indexed ones).
    """
    import lancedb
    from lex_retriever.embeddings import get_embedding_provider
    from .providers.rechtsprechung_im_internet import RechtsprechungImInternetProvider

    try:
        from tqdm import tqdm
    except ImportError:
        def tqdm(it, **kwargs):  # type: ignore[misc]
            return it

    os.makedirs(db_path, exist_ok=True)
    db = lancedb.connect(db_path)
    embedder = get_embedding_provider(embedding_config)

    provider = RechtsprechungImInternetProvider()
    log.info("Fetching %s decisions from provider...", court)
    raw_chunks = provider.fetch_court(court)

    if not raw_chunks:
        log.warning("No chunks returned for %s", court)
        return 0

    existing_ids: set[str] = set()
    if TABLE_NAME in db.table_names():
        table = db.open_table(TABLE_NAME)
        try:
            existing_ids = {
                row["id"]
                for row in table.search()
                         .where(f"court = '{court}'")
                         .select(["id"])
                         .limit(999_999)
                         .to_list()
            }
        except Exception:
            existing_ids = set()

    chunks_to_index = []
    for idx, chunk in enumerate(raw_chunks):
        case_id = make_case_id(chunk["court"], chunk["az"], idx)
        if case_id not in existing_ids:
            chunks_to_index.append({**chunk, "id": case_id})

    if not chunks_to_index:
        log.info("All %d %s chunks already indexed — skipping.", len(raw_chunks), court)
        return 0

    log.info("Indexing %d new chunks for %s (skipping %d already indexed)...",
             len(chunks_to_index), court, len(existing_ids))

    texts = [c["text"] for c in chunks_to_index]
    vectors: list[list[float]] = []
    for i in tqdm(range(0, len(texts), _BATCH_SIZE),
                  desc=f"Embedding {court}", unit="batch"):
        batch = texts[i : i + _BATCH_SIZE]
        vectors.extend(embedder.embed(batch))

    rows = [{**chunk, "vector": list(vec)} for chunk, vec in zip(chunks_to_index, vectors)]

    if TABLE_NAME not in db.table_names():
        table = db.create_table(TABLE_NAME, data=rows[:_BATCH_SIZE])
        for start in range(_BATCH_SIZE, len(rows), _BATCH_SIZE):
            table.add(rows[start : start + _BATCH_SIZE])
    else:
        table = db.open_table(TABLE_NAME)
        for start in range(0, len(rows), _BATCH_SIZE):
            table.add(rows[start : start + _BATCH_SIZE])

    log.info("Indexed %d chunks for %s.", len(rows), court)
    return len(rows)


def index_all_courts(db_path: str = LANCE_PATH, embedding_config: dict | None = None) -> dict[str, int]:
    """Index all 6 federal courts. Returns {court: chunks_indexed}."""
    results = {}
    for court in ["BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"]:
        results[court] = index_court(court, db_path=db_path, embedding_config=embedding_config)
    return results


def get_index_stats(db_path: str = LANCE_PATH) -> dict[str, int]:
    """Return per-court chunk counts from the LanceDB index."""
    try:
        import lancedb
        db = lancedb.connect(db_path)
        if TABLE_NAME not in db.table_names():
            return {}
        table = db.open_table(TABLE_NAME)
        import pandas as pd
        df = table.to_pandas()[["court"]]
        return df["court"].value_counts().to_dict()
    except Exception:
        return {}
