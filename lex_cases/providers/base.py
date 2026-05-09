from abc import ABC, abstractmethod


class CaseProvider(ABC):
    @abstractmethod
    def fetch_court(self, court: str) -> list[dict]:
        """Return list of case dicts for the given court.

        Each dict has keys: court, az, date, type, chunk_type, text, laws_cited, url.
        (id and vector are set by the indexer.)
        """
        ...
