"""Abstract base for court decision providers."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class RawCase:
    court: str
    az: str
    date: str
    type: str
    chunk_type: str    # "leitsatz" | "tenor"
    text: str
    laws_cited: list[str] = field(default_factory=list)
    url: str = ""

    @property
    def id(self) -> str:
        key = f"{self.court}:{self.az}:{self.chunk_type}"
        return hashlib.sha1(key.encode()).hexdigest()


class CaseProvider(ABC):
    @abstractmethod
    def fetch_cases(self, court: str) -> Iterator[RawCase]:
        """Yield RawCase objects for all decisions from the given court."""
