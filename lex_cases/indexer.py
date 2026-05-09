import hashlib
import logging

import pyarrow as pa

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

_BATCH_SIZE = 16
log = logging.getLogger(__name__)


def make_case_id(court: str, az: str, chunk_idx: int) -> str:
    return hashlib.sha1(f"{court}|{az}|{chunk_idx}".encode()).hexdigest()


def index_court(court: str, db_path: str = "lancedb") -> None:
    """Index all decisions (Leitsatz + Tenor) for a single court."""
    raise NotImplementedError("index_court — implemented in SUB-2")


def index_all_courts(db_path: str = "lancedb") -> None:
    """Index all 6 federal courts."""
    for court in ["BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"]:
        index_court(court, db_path)
