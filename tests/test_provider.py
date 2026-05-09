import pytest
from lex_cases.providers.rechtsprechung_im_internet import _COURT_CATALOG, _xml_zip_url
from lex_cases.providers.base import CaseProvider
from lex_cases.providers.rechtsprechung_im_internet import RechtsprechungImInternetProvider


def test_court_catalog_has_all_courts():
    expected = {"BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"}
    assert set(_COURT_CATALOG.keys()) == expected


def test_xml_zip_url():
    url = _xml_zip_url("bgh")
    assert url == "https://www.rechtsprechung-im-internet.de/bgh/xml.zip"


def test_provider_inherits_abc():
    assert issubclass(RechtsprechungImInternetProvider, CaseProvider)


# XML parsing tests with fixture added in SUB-3
