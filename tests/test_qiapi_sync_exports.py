import json
import types

import pytest

from pyQi.QiApi import QiAPI
from pyQi.common import QiAuthentication, QiRecords


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(
        QiAuthentication,
        "qi_login",
        lambda self: types.SimpleNamespace(username="user", password="pass"),
    )
    return QiAPI("user", "example.server", "pass")


def test_search_to_excel_needs_pandas(api, monkeypatch):
    pd = pytest.importorskip("pandas")
    monkeypatch.setattr("pyQi.QiApi.pd", None)

    with pytest.raises(ImportError, match="Pandas library is required"):
        api.search_to_excel("output.xlsx", "Contacts", "id", "1")


def test_search_to_csv_needs_pandas(api, monkeypatch):
    pd = pytest.importorskip("pandas")
    monkeypatch.setattr("pyQi.QiApi.pd", None)

    with pytest.raises(ImportError, match="Pandas library is required"):
        api.search_to_csv("output.csv", "Contacts", "id", "1")


def test_search_to_dict_returns_list_of_dicts(api, monkeypatch):
    def fake_search_to_records(*args, **kwargs):
        api.qi_records = QiRecords(
            {
                "records": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ]
            }
        )
        return api.qi_records.records

    monkeypatch.setattr(api, "search_to_records", fake_search_to_records)

    result = api.search_to_dict("Contacts", "id", "1")

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["name"] == "Bob"


def test_search_to_json_string_returns_json_text(api, monkeypatch):
    def fake_search_to_records(*args, **kwargs):
        api.qi_records = QiRecords({"records": [{"id": 1}]})
        return api.qi_records.records

    monkeypatch.setattr(api, "search_to_records", fake_search_to_records)

    result = api.search_to_json_string("Contacts", "id", "1")

    parsed = json.loads(result)
    assert parsed["records"][0]["id"] == 1
