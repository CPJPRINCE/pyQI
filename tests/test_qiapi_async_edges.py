import json
import types

import pytest

from pyQi.QiApi_async import QiAPIAsync
from pyQi.common import QiAuthentication, QiRecords, base64_encode


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(
        QiAuthentication,
        "qi_login",
        lambda self: types.SimpleNamespace(username="user", password="pass"),
    )

    def fake_create_session(self, tcp_limit=100):
        self.session = None
        return self.session

    monkeypatch.setattr(QiAPIAsync, "create_session", fake_create_session)
    return QiAPIAsync("user", "example.server", "pass")


@pytest.mark.asyncio
async def test_call_url_iter_without_pagination_calls_once(api, monkeypatch):
    calls = []

    async def fake_call_url(url, method="get", data=None):
        calls.append(url)
        api.json_data = {"count": 10, "records": [{"id": 1}]}

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    result = await api._call_url_iter("https://example/get/Table", "get", None)

    assert len(calls) == 1
    assert result["records"] == [{"id": 1}]


@pytest.mark.asyncio
async def test_call_url_iter_with_pagination_merges_records(api, monkeypatch):
    calls = []
    api.offset = 0

    async def fake_call_url(url, method="get", data=None):
        calls.append(url)
        if "_offset/500" in url:
            api.json_data = {"count": 600, "records": [{"id": 2}]}
        else:
            api.json_data = {"count": 600, "records": [{"id": 1}]}

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    result = await api._call_url_iter("https://example/get/Table", "get", None)

    assert len(calls) == 2
    assert result["records"] == [{"id": 1}, {"id": 2}]


@pytest.mark.asyncio
async def test_search_to_records_returns_qirecord_list(api, monkeypatch):
    async def fake_get_request(*args, **kwargs):
        return {"count": 2, "records": [{"id": 1}, {"id": 2}]}

    monkeypatch.setattr(api, "get_request", fake_get_request)

    records = await api.search_to_records("Contacts", "id", "1")

    assert len(records) == 2
    assert records[0].id == 1
    assert isinstance(api.qi_records, QiRecords)


@pytest.mark.asyncio
async def test_search_to_json_string_returns_json(api, monkeypatch):
    async def fake_search_to_records(*args, **kwargs):
        api.qi_records = QiRecords({"count": 1, "records": [{"id": 9, "name": "X"}]})
        return api.qi_records.records

    monkeypatch.setattr(api, "search_to_records", fake_search_to_records)

    json_string = await api.search_to_json_string("Contacts", "id", "9")

    assert json.loads(json_string)["records"][0]["id"] == 9


@pytest.mark.asyncio
async def test_delete_from_search_only_deletes_non_deleted(api, monkeypatch):
    async def fake_get_request(*args, **kwargs):
        return {
            "records": [
                {"id": 1, "deleted": None},
                {"id": 2, "deleted": True},
                {"id": 3, "deleted": None},
            ]
        }

    deleted_ids = []

    async def fake_delete_request(table, id_to_delete, auto_approve=False, print_response=False):
        deleted_ids.append(id_to_delete)

    monkeypatch.setattr(api, "get_request", fake_get_request)
    monkeypatch.setattr(api, "delete_request", fake_delete_request)

    await api.delete_from_search("Contacts", "name", "Alice")

    assert deleted_ids == [1, 3]


@pytest.mark.asyncio
async def test_lookup_list_builds_case_insensitive_map(api, monkeypatch):
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

    async def fake_get_list(list_name):
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

    await api.lookup_list("Contacts", "status")

    assert api.list_dict == {"active": 100, "inactive": 200}


@pytest.mark.asyncio
async def test_lookup_lists_raises_for_missing_list_values(api, monkeypatch):
    pd = pytest.importorskip("pandas")

    api.types_data = json.dumps({"Contacts": {"fields": []}})
    api.df = pd.DataFrame({"list:status": ["active", "missing"]})
    api.column_headers = list(api.df.columns.values)

    async def fake_lookup_list(table, field_name):
        api.list_dict = {"active": 100}

    monkeypatch.setattr(api, "lookup_list", fake_lookup_list)

    with pytest.raises(ValueError, match="do not match any entries"):
        await api.lookup_lists("Contacts")


@pytest.mark.asyncio
async def test_get_request_with_multi_field_pairs_encodes_each_term(api, monkeypatch):
    captured = {}

    async def fake_call_url_iter(url, method="get", data=None):
        captured["url"] = url
        api.json_data = {"count": 0, "records": []}
        return api.json_data

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    await api.get_request(
        table="Contacts",
        fields_to_search=["first_name", "last_name"],
        search_term=["John", "Doe"],
    )

    assert f"first_name/{base64_encode('John')}" in captured["url"]
    assert f"last_name/{base64_encode('Doe')}" in captured["url"]
