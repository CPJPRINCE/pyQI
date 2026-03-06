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


def test_call_url_iter_with_pagination_merges_records(api, monkeypatch):
    calls = []
    api.offset = 0

    def fake_call_url(url, method="get", data=None):
        calls.append(url)
        if "_offset/500" in url:
            api.json_data = {"count": 600, "records": [{"id": 2}]}
        else:
            api.json_data = {"count": 600, "records": [{"id": 1}]}

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    result = api._call_url_iter("https://example/get/Table", "get", None)

    assert len(calls) == 2
    assert result["records"] == [{"id": 1}, {"id": 2}]


def test_lookup_table_id_uses_cached_types_data(api, monkeypatch):
    api.types_data = json.dumps(
        {
            "Contacts": {
                "id": 999,
                "fields": []
            }
        }
    )

    get_types_called = False

    def fake_get_types():
        nonlocal get_types_called
        get_types_called = True
        return api.types_data

    monkeypatch.setattr(api, "get_types", fake_get_types)

    result = api.lookup_table_id("Contacts")

    assert result == 999
    assert not get_types_called


def test_lookup_table_id_fetches_types_when_none(api, monkeypatch):
    def fake_get_types():
        api.types_data = json.dumps({"Contacts": {"id": 123}})
        return api.types_data

    monkeypatch.setattr(api, "get_types", fake_get_types)

    result = api.lookup_table_id("Contacts")

    assert result == 123


def test_lookup_list_builds_case_insensitive_map(api, monkeypatch):
    api.types_data = json.dumps(
        {
            "Contacts": {
                "fields": [
                    {"name": "status", "source_table": "StatusList"},
                    {"name": "name", "source_table": None},
                ]
            }
        }
    )

    def fake_get_list(list_name):
        assert list_name == "StatusList"
        api.list_data = json.dumps(
            {
                "records": [
                    {"name": "Active", "id": 100},
                    {"name": "Inactive", "id": 200},
                ]
            }
        )
        return api.list_data

    monkeypatch.setattr(api, "get_list", fake_get_list)

    api.lookup_list("Contacts", "status")

    assert api.list_dict == {"active": 100, "inactive": 200}


def test_lookup_lists_raises_for_missing_list_values(api, monkeypatch):
    pd = pytest.importorskip("pandas")

    api.types_data = json.dumps({"Contacts": {"fields": []}})
    api.df = pd.DataFrame({"list:status": ["active", "missing"]})
    api.column_headers = list(api.df.columns.values)

    def fake_lookup_list(table, field_name):
        api.list_dict = {"active": 100}

    monkeypatch.setattr(api, "lookup_list", fake_lookup_list)

    with pytest.raises(ValueError, match="do not match any entries"):
        api.lookup_lists("Contacts")


def test_update_from_file_raises_without_id_and_lookup_field(api, monkeypatch):
    class DummyFrame:
        def __init__(self):
            self.columns = types.SimpleNamespace(values=["name"])

        def to_dict(self, orient):
            return [{"name": "NoId"}]

    api.df = DummyFrame()

    def fake_read_source(file):
        return None

    def fake_lookup_table_id(table):
        return 123

    monkeypatch.setattr(api, "_read_source", fake_read_source)
    monkeypatch.setattr(api, "lookup_table_id", fake_lookup_table_id)

    with pytest.raises(ValueError, match="No id data has been detected"):
        api.update_from_file("dummy.xlsx", "Contacts")


def test_delete_from_file_raises_without_id_and_lookup_field(api, monkeypatch):
    class DummyFrame:
        def to_dict(self, orient):
            return [{"name": "NoId"}]

    api.df = DummyFrame()

    def fake_read_source(file):
        return None

    monkeypatch.setattr(api, "_read_source", fake_read_source)

    with pytest.raises(ValueError, match="No id data has been detected"):
        api.delete_from_file("dummy.xlsx", "Contacts")


def test_call_url_iter_keyboard_interrupt_returns_partial_json(api, monkeypatch):
    api.json_data = {"count": 1, "records": [{"id": 1}]}

    def fake_call_url(url, method="get", data=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    result = api._call_url_iter("https://example/get/Table", "get", None)

    assert result == {"count": 1, "records": [{"id": 1}]}


def test_call_url_iter_wraps_unexpected_errors(api, monkeypatch):
    def fake_call_url(url, method="get", data=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    with pytest.raises(SystemError):
        api._call_url_iter("https://example/get/Table", "get", None)
