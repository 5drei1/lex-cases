"""Agent-callable interface for lex-cases. See AGENT.md for full documentation."""

from __future__ import annotations

from .retriever import LexCaseRetriever

_retriever = LexCaseRetriever()


def search_case_law(
    query: str,
    courts: list[str] | None = None,
    laws_cited: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Semantic search over indexed German court decisions.

    Returns list of dicts with keys: court, az, date, type, leitsatz,
    laws_cited, score, url.
    """
    return _retriever.search(
        query,
        courts=courts,
        laws_cited=laws_cited,
        date_from=date_from,
        date_to=date_to,
        top_k=top_k,
    )


def get_case_fulltext(url: str) -> str:
    """Fetch and parse the full decision text (Tatbestand + Gründe) on demand.

    url must be a rechtsprechung-im-internet.de URL from a search result.
    """
    return _retriever.get_case_fulltext(url)


def get_cases_citing_law(law: str, paragraph: str) -> list[dict]:
    """Return all indexed decisions that cite a specific law paragraph.

    Example: get_cases_citing_law("BGB", "§ 823")
    """
    return _retriever.get_cases_citing_law(law, paragraph)
