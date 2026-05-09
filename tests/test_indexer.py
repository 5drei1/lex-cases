import pyarrow as pa
import pytest
from lex_cases.indexer import _CASE_SCHEMA, TABLE_NAME, make_case_id


def test_schema_fields():
    field_names = {f.name for f in _CASE_SCHEMA}
    required = {"id", "court", "az", "date", "type", "chunk_type", "text", "laws_cited", "url", "vector"}
    assert required == field_names


def test_schema_vector_type():
    vector_field = next(f for f in _CASE_SCHEMA if f.name == "vector")
    assert pa.types.is_list(vector_field.type)
    assert vector_field.type.value_type == pa.float32()


def test_schema_laws_cited_type():
    field = next(f for f in _CASE_SCHEMA if f.name == "laws_cited")
    assert pa.types.is_list(field.type)
    assert field.type.value_type == pa.string()


def test_make_case_id_deterministic():
    id1 = make_case_id("BGH", "IV ZR 123/24", 0)
    id2 = make_case_id("BGH", "IV ZR 123/24", 0)
    assert id1 == id2
    assert len(id1) == 40  # SHA1 hex


def test_make_case_id_unique_chunk_idx():
    id_leitsatz = make_case_id("BGH", "IV ZR 123/24", 0)
    id_tenor = make_case_id("BGH", "IV ZR 123/24", 1)
    assert id_leitsatz != id_tenor


def test_make_case_id_unique_court():
    id_bgh = make_case_id("BGH", "IV ZR 123/24", 0)
    id_bag = make_case_id("BAG", "IV ZR 123/24", 0)
    assert id_bgh != id_bag


def test_table_name():
    assert TABLE_NAME == "german_cases"
