"""Tests for the rechtsprechung-im-internet.de provider."""

import io
import xml.etree.ElementTree as ET
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from lex_cases.providers.base import CaseProvider
from lex_cases.providers.rechtsprechung_im_internet import (
    RechtsprechungImInternetProvider,
    _COURT_CATALOG,
    _xml_zip_url,
    _parse_xml_entry,
)

# Minimal well-formed XML fixture matching the real schema
_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<document>
  <doknr>BGHR2024001234</doknr>
  <gericht>Bundesgerichtshof</gericht>
  <entscheidungsdatum>2024-03-15</entscheidungsdatum>
  <aktenzeichen>IV ZR 123/24</aktenzeichen>
  <dokumenttyp>Urteil</dokumenttyp>
  <leitsatz>Der Schuldner haftet gemäß § 280 BGB auf Schadensersatz.</leitsatz>
  <tenor>Die Revision wird zurückgewiesen.</tenor>
  <normkette>§ 280 BGB, § 823 BGB</normkette>
</document>
"""


def _make_zip(xml_content: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bgh_2024_001.xml", xml_content)
    return buf.getvalue()


def test_court_catalog_has_all_courts():
    expected = {"BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"}
    assert set(_COURT_CATALOG.keys()) == expected


def test_court_catalog_has_slugs():
    for code, (name, slug) in _COURT_CATALOG.items():
        assert slug, f"{code} slug must be non-empty"
        assert name, f"{code} name must be non-empty"


def test_xml_zip_url():
    assert _xml_zip_url("bgh") == "https://www.rechtsprechung-im-internet.de/bgh/xml.zip"


def test_provider_inherits_abc():
    assert issubclass(RechtsprechungImInternetProvider, CaseProvider)


def test_parse_xml_entry_leitsatz_and_tenor():
    root = ET.fromstring(_SAMPLE_XML)
    chunks = _parse_xml_entry(root, "BGH")
    chunk_types = {c["chunk_type"] for c in chunks}
    assert "leitsatz" in chunk_types
    assert "tenor" in chunk_types


def test_parse_xml_entry_fields():
    root = ET.fromstring(_SAMPLE_XML)
    chunks = _parse_xml_entry(root, "BGH")
    leitsatz = next(c for c in chunks if c["chunk_type"] == "leitsatz")
    assert leitsatz["court"] == "BGH"
    assert leitsatz["az"] == "IV ZR 123/24"
    assert leitsatz["date"] == "2024-03-15"
    assert leitsatz["type"] == "Urteil"
    assert "Der Schuldner" in leitsatz["text"]
    assert "BGHR2024001234" in leitsatz["url"]


def test_parse_xml_entry_laws_cited():
    root = ET.fromstring(_SAMPLE_XML)
    chunks = _parse_xml_entry(root, "BGH")
    leitsatz = next(c for c in chunks if c["chunk_type"] == "leitsatz")
    laws = leitsatz["laws_cited"]
    assert any("280" in l for l in laws), f"Expected § 280 in laws_cited, got: {laws}"
    assert any("823" in l for l in laws), f"Expected § 823 in laws_cited, got: {laws}"


def test_parse_xml_entry_skips_empty_chunks():
    xml_no_tenor = _SAMPLE_XML.replace("<tenor>Die Revision wird zurückgewiesen.</tenor>", "<tenor/>")
    root = ET.fromstring(xml_no_tenor)
    chunks = _parse_xml_entry(root, "BGH")
    assert all(c["chunk_type"] != "tenor" for c in chunks)


def test_fetch_court_retry_on_failure():
    """Provider retries on HTTP errors — mock fails twice then succeeds."""
    provider = RechtsprechungImInternetProvider()
    zip_bytes = _make_zip(_SAMPLE_XML)

    call_count = 0

    def _fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            from requests.exceptions import ConnectionError
            raise ConnectionError("Simulated network error")
        resp = MagicMock()
        resp.raise_for_status = lambda: None
        resp.content = zip_bytes
        return resp

    with patch("lex_cases.providers.rechtsprechung_im_internet.requests.get", side_effect=_fake_get):
        chunks = provider.fetch_court("BGH")

    assert call_count == 3
    assert len(chunks) > 0


def test_fetch_court_unknown_court():
    provider = RechtsprechungImInternetProvider()
    with pytest.raises(ValueError, match="Unknown court"):
        provider.fetch_court("INVALID")
