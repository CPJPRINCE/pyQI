import json

import pytest

from pyQi.json_builder import JsonBuilder


def test_json_builder_simple_record():
    data = {"name": "Alice", "email": "alice@example.com"}
    builder = JsonBuilder(data)

    assert builder.records_dict == {
        "record": {"name": "Alice", "email": "alice@example.com"}
    }


def test_json_builder_with_list_field():
    data = {"name": "Alice", "list:status": "active"}
    builder = JsonBuilder(data)

    assert builder.lists_set == {"status"}
    assert builder.records_dict["record"]["name"] == "Alice"


def test_json_builder_with_relationship():
    data = {
        "name": "Alice",
        "relationship:Company:company_name:Acme Inc": "company-value",
    }
    builder = JsonBuilder(data)

    assert "Company" in builder.relations_set
    assert builder.records_dict["record"]["name"] == "Alice"
    assert "relationships" in builder.records_dict
    assert builder.records_dict["relationships"]["Company"]


def test_json_builder_with_multiple_relationships():
    data = {
        "name": "Alice",
        "relationship:Company:company_name:Acme": "c1",
        "relationship:Department:dept_name:Sales": "d1",
    }
    builder = JsonBuilder(data)

    assert len(builder.relations_set) == 2
    assert "Company" in builder.records_dict["relationships"]
    assert "Department" in builder.records_dict["relationships"]


def test_json_builder_record_dict_structure():
    data = {"id": 1, "name": "Post", "created": "2024-01-01"}
    builder = JsonBuilder(data)

    assert "record" in builder.records_dict
    assert builder.records_dict["record"]["id"] == 1
    assert builder.records_dict["record"]["name"] == "Post"
    assert builder.records_dict["record"]["created"] == "2024-01-01"
