"""Tests for the rechtsprechung-im-internet provider XML parser."""

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from lex_cases.providers.rechtsprechung_im_internet import (
    RechtsprechungImInternetProvider,
    _parse_xml,
    _COURT_CATALOG,
)


_FIXTURE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<dokumente>
  <dokument>
    <doknr>BGHR2024001</doknr>
    <aktenzeichen>IV ZR 123/24</aktenzeichen>
    <entscheidungsdatum>2024-11-15</entscheidungsdatum>
    <dokumenttyp>Urteil</dokumenttyp>
    <leitsatz>Der Schuldner haftet nach &#167; 280 BGB.</leitsatz>
    <tenor>Die Revision wird zurueckgewiesen.</tenor>
    <normkette>&#167; 280 BGB &#167; 823 BGB</normkette>
  </dokument>
  <dokument>
    <doknr>BGHR2024002</doknr>
    <aktenzeichen>V ZR 10/24</aktenzeichen>
    <entscheidungsdatum>2024-09-01</entscheidungsdatum>
    <dokumenttyp>Beschluss</dokumenttyp>
    <leitsatz>Ein Beschluss ohne Tenor.</leitsatz>
  </dokument>
</dokumente>
"""


def _make_zip(xml_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("decisions.xml", xml_bytes)
    return buf.getvalue()


def test_parse_xml_leitsatz_and_tenor():
    cases = _parse_xml(_FIXTURE_XML, "BGH", "bgh")
    chunk_types = {c.chunk_type for c in cases}
    assert "leitsatz" in chunk_types
    assert "tenor" in chunk_types


def test_parse_xml_case_fields():
    cases = _parse_xml(_FIXTURE_XML, "BGH", "bgh")
    leitsatz_cases = [c for c in cases if c.chunk_type == "leitsatz"]
    first = next(c for c in leitsatz_cases if c.az == "IV ZR 123/24")
    assert first.court == "BGH"
    assert first.date == "2024-11-15"
    assert first.type == "Urteil"
    assert "280" in first.text


def test_parse_xml_missing_tenor_skipped():
    cases = _parse_xml(_FIXTURE_XML, "BGH", "bgh")
    tenor_cases = [c for c in cases if c.chunk_type == "tenor"]
    azs = {c.az for c in tenor_cases}
    assert "IV ZR 123/24" in azs
    assert "V ZR 10/24" not in azs


def test_court_catalog_has_all_six():
    assert len(_COURT_CATALOG) == 6
    for court in ("BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"):
        assert court in _COURT_CATALOG


def test_unknown_court_raises():
    provider = RechtsprechungImInternetProvider()
    with pytest.raises(ValueError, match="Unknown court"):
        list(provider.fetch_cases("XYZ"))
