"""Provider: rechtsprechung-im-internet.de (official German federal court database)."""

from __future__ import annotations

import io
import logging
import zipfile
from typing import Iterator
from xml.etree import ElementTree as ET

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import CaseProvider, RawCase

logger = logging.getLogger(__name__)

_COURT_CATALOG: dict[str, tuple[str, str]] = {
    "BGH":    ("Bundesgerichtshof",         "bgh"),
    "BVERFG": ("Bundesverfassungsgericht",  "bverfg"),
    "BAG":    ("Bundesarbeitsgericht",      "bag"),
    "BFH":    ("Bundesfinanzhof",           "bfh"),
    "BVERWG": ("Bundesverwaltungsgericht",  "bverwg"),
    "BPATG":  ("Bundespatentgericht",       "bpatg"),
}

_BASE_URL = "https://www.rechtsprechung-im-internet.de"


def _xml_zip_url(slug: str) -> str:
    return f"{_BASE_URL}/{slug}/xml.zip"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _download_zip(url: str) -> bytes:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _extract_laws_cited(normkette_node) -> list[str]:
    if normkette_node is None:
        return []
    try:
        from lex_retriever.cross_reference import extract_references
        raw = "".join(normkette_node.itertext())
        return extract_references(raw)
    except Exception:
        raw = "".join(normkette_node.itertext()).strip()
        return [raw] if raw else []


def _parse_xml(xml_bytes: bytes, court: str, slug: str) -> list[RawCase]:
    cases = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("XML parse error: %s", exc)
        return cases

    for doc in root.findall(".//dokument"):
        az_node    = doc.find("aktenzeichen")
        date_node  = doc.find("entscheidungsdatum")
        type_node  = doc.find("dokumenttyp")
        leitsatz   = doc.find("leitsatz")
        tenor      = doc.find("tenor")
        normkette  = doc.find("normkette")
        doc_id_node = doc.find("doknr")

        az   = az_node.text.strip()   if az_node   is not None and az_node.text   else ""
        date = date_node.text.strip() if date_node is not None and date_node.text else ""
        typ  = type_node.text.strip() if type_node is not None and type_node.text else ""
        laws = _extract_laws_cited(normkette)

        doc_id = doc_id_node.text.strip() if doc_id_node is not None and doc_id_node.text else ""
        url = f"{_BASE_URL}/{slug}/{doc_id}.html" if doc_id else ""

        for chunk_type, node in [("leitsatz", leitsatz), ("tenor", tenor)]:
            if node is None:
                continue
            text = "".join(node.itertext()).strip()
            if not text:
                continue
            cases.append(RawCase(
                court=court,
                az=az,
                date=date,
                type=typ,
                chunk_type=chunk_type,
                text=text,
                laws_cited=laws,
                url=url,
            ))

    return cases


class RechtsprechungImInternetProvider(CaseProvider):
    def fetch_cases(self, court: str) -> Iterator[RawCase]:
        court_upper = court.upper()
        if court_upper not in _COURT_CATALOG:
            raise ValueError(f"Unknown court: {court}. Supported: {list(_COURT_CATALOG)}")

        _, slug = _COURT_CATALOG[court_upper]
        url = _xml_zip_url(slug)
        logger.info("Downloading %s from %s", court_upper, url)

        zip_bytes = _download_zip(url)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
            logger.info("Found %d XML files for %s", len(xml_files), court_upper)
            for name in xml_files:
                xml_bytes = zf.read(name)
                yield from _parse_xml(xml_bytes, court_upper, slug)
