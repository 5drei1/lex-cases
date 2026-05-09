"""Provider for rechtsprechung-im-internet.de — official German federal court decisions."""

from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
import zipfile

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import CaseProvider

log = logging.getLogger(__name__)

_COURT_CATALOG: dict[str, tuple[str, str]] = {
    "BGH":    ("Bundesgerichtshof",        "bgh"),
    "BVERFG": ("Bundesverfassungsgericht", "bverfg"),
    "BAG":    ("Bundesarbeitsgericht",     "bag"),
    "BFH":    ("Bundesfinanzhof",          "bfh"),
    "BVERWG": ("Bundesverwaltungsgericht", "bverwg"),
    "BPATG":  ("Bundespatentgericht",      "bpatg"),
}


def _xml_zip_url(slug: str) -> str:
    return f"https://www.rechtsprechung-im-internet.de/{slug}/xml.zip"


def _text(el: ET.Element | None, tag: str) -> str:
    if el is None:
        return ""
    child = el.find(tag)
    if child is None:
        return ""
    return (child.text or "").strip()


def _parse_xml_entry(root: ET.Element, court_code: str) -> list[dict]:
    """Parse a single XML document into 1–2 case dicts (leitsatz + tenor).

    Returns one dict per chunk_type that has non-empty text.
    """
    from lex_retriever.cross_reference import extract_references

    az = _text(root, "aktenzeichen")
    date = _text(root, "entscheidungsdatum")
    doc_type = _text(root, "dokumenttyp")
    doknr = _text(root, "doknr")
    normkette = _text(root, "normkette")

    if doknr:
        url = f"https://www.rechtsprechung-im-internet.de/jportal/?docid={doknr}"
    else:
        url = ""

    refs = extract_references(normkette)
    laws_cited: list[str] = []
    for ref in refs:
        if ref.get("law"):
            laws_cited.append(f"{ref['paragraph']} {ref['law']}")
        else:
            laws_cited.append(ref["paragraph"])

    chunks = []
    for chunk_type, tag in [("leitsatz", "leitsatz"), ("tenor", "tenor")]:
        text = _text(root, tag)
        if not text:
            continue
        chunks.append({
            "court":      court_code,
            "az":         az,
            "date":       date,
            "type":       doc_type,
            "chunk_type": chunk_type,
            "text":       text,
            "laws_cited": laws_cited,
            "url":        url,
        })
    return chunks


class RechtsprechungImInternetProvider(CaseProvider):
    """Downloads and parses XML-ZIP archives from rechtsprechung-im-internet.de."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_court(self, court: str) -> list[dict]:
        """Download XML-ZIP for a court and return list of case chunk dicts."""
        if court not in _COURT_CATALOG:
            raise ValueError(f"Unknown court: {court!r}. Known: {list(_COURT_CATALOG)}")

        _name, slug = _COURT_CATALOG[court]
        url = _xml_zip_url(slug)
        log.info("Downloading %s XML-ZIP from %s", court, url)

        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()

        content = resp.content
        log.info("Downloaded %d bytes for %s", len(content), court)

        results: list[dict] = []
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
            log.info("Found %d XML files in %s archive", len(xml_names), court)
            for xml_name in xml_names:
                try:
                    xml_data = zf.read(xml_name)
                    root = ET.fromstring(xml_data)
                    chunks = _parse_xml_entry(root, court)
                    results.extend(chunks)
                except ET.ParseError as e:
                    log.warning("Skipping malformed XML %s: %s", xml_name, e)
                except Exception as e:
                    log.warning("Error parsing %s: %s", xml_name, e)

        log.info("Parsed %d chunks from %s", len(results), court)
        return results
