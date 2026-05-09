from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from .base import CaseProvider

_COURT_CATALOG = {
    "BGH":    ("Bundesgerichtshof",        "bgh"),
    "BVERFG": ("Bundesverfassungsgericht", "bverfg"),
    "BAG":    ("Bundesarbeitsgericht",     "bag"),
    "BFH":    ("Bundesfinanzhof",          "bfh"),
    "BVERWG": ("Bundesverwaltungsgericht", "bverwg"),
    "BPATG":  ("Bundespatentgericht",      "bpatg"),
}


def _xml_zip_url(slug: str) -> str:
    return f"https://www.rechtsprechung-im-internet.de/{slug}/xml.zip"


class RechtsprechungImInternetProvider(CaseProvider):
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_court(self, court: str) -> list[dict]:
        """Download XML-ZIP for a court and return parsed case dicts."""
        raise NotImplementedError("fetch_court — implemented in SUB-3")
