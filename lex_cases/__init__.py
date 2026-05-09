"""lex-cases: semantic search over indexed German federal court decisions."""

from .tool import search_case_law, get_case_fulltext, get_cases_citing_law
from .indexer import index_court, index_all_courts

__all__ = [
    "search_case_law",
    "get_case_fulltext",
    "get_cases_citing_law",
    "index_court",
    "index_all_courts",
]
__version__ = "0.1.0"
