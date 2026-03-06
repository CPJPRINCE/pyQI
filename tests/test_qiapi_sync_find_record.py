import json
import types

import pytest

from pyQi.QiApi import QiAPI
from pyQi.common import QiAuthentication, QiRecord


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(
        QiAuthentication,
        "qi_login",
        lambda self: types.SimpleNamespace(username="user", password="pass"),
    )
    return QiAPI("user", "example.server", "pass")


def test_find_record_returns_qirecord(api, monkeypatch):
    def fake_get_request(*args, **kwargs):
        api.json_data = {
            "records": [
                {"id": 123, "name": "Alice", "status": "active"},
            ]
        }
        return api.json_data

    monkeypatch.setattr(api, "get_request", fake_get_request)

    record = api.find_record(
        table="Contacts",
        fields_to_search="name",
        search_term="Alice",
    )

    assert isinstance(record, QiRecord)
    assert record.id == 123
    assert record.name == "Alice"
    assert record.status == "active"


def test_find_record_by_id_forwards_expected_search_params(api, monkeypatch):
    captured = {}

    def fake_get_request(*args, **kwargs):
        captured.update(kwargs)
        api.json_data = {"records": [{"id": "42", "name": "Bob"}]}
        return api.json_data

    monkeypatch.setattr(api, "get_request", fake_get_request)

    record = api.find_record_by_id(
        table="Contacts",
        id=42,
        fields_to_return="id,name",
        print_response=True,
    )

    assert isinstance(record, QiRecord)
    assert captured["table"] == "Contacts"
    assert captured["fields_to_search"] == "id"
    assert captured["search_term"] == "42"
    assert captured["fields"] == "id,name"
    assert captured["print_response"] is True


def test_get_request_builds_expected_url_and_delegates(api, monkeypatch):
    captured = {}

    def fake_call_url_iter(url, method="get", data=None):
        captured["url"] = url
        captured["method"] = method
        captured["data"] = data
        api.json_data = {"count": 1, "records": [{"id": 1}]}
        return api.json_data

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    result = api.get_request(
        table="Contacts",
        fields_to_search="name",
        search_term="Alice",
        per_page=50,
        sort_by="name",
    )

    assert captured["method"] == "get"
    assert captured["data"] is None
    assert "/get/Contacts/name/" in captured["url"]
    assert result == {"count": 1, "records": [{"id": 1}]}


def test_delete_request_builds_expected_approve_url(api, monkeypatch):
    captured = {}

    def fake_call_url(url, method, data=None):
        captured["url"] = url
        captured["method"] = method
        captured["data"] = data

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    api.delete_request(
        table="Contacts",
        id_to_delete=42,
        auto_approve=True,
        print_response=True,
    )

    assert captured["method"] == "delete"
    assert captured["data"] is None
    assert captured["url"].endswith("/delete/Contacts/id/42/_approve/yes")


def test_put_request_with_auto_approve(api, monkeypatch):
    captured = {}

    def fake_call_url_iter(url, method, data=None):
        captured["url"] = url
        captured["method"] = method

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    api.put_request(
        data={"id": 1, "name": "Updated"},
        table="Contacts",
        auto_approve=True,
    )

    assert captured["method"] == "put"
    assert captured["url"].endswith("/put/Contacts/_approve/yes")


def test_post_request_standard_url(api, monkeypatch):
    captured = {}

    def fake_call_url(url, method, data=None):
        captured["url"] = url
        captured["method"] = method

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    api.post_request(
        data={"name": "New"},
        table="Contacts",
        auto_approve=False,
    )

    assert captured["method"] == "post"
    assert captured["url"].endswith("/post/Contacts")


def test_get_types_simple(api, monkeypatch):
    class DummyResponse:
        def __init__(self):
            self.text = '{"Contacts": {}}'
            self.status_code = 200

    def fake_requests_get(url, auth=None):
        return DummyResponse()

    monkeypatch.setattr("pyQi.QiApi.requests.get", fake_requests_get)

    result = api.get_types()

    assert result == '{"Contacts": {}}'


def test_get_list_simple(api, monkeypatch):
    class DummyResponse:
        def __init__(self):
            self.text = '{"records": []}'
            self.status_code = 200

    def fake_requests_get(url, auth=None):
        return DummyResponse()

    monkeypatch.setattr("pyQi.QiApi.requests.get", fake_requests_get)

    result = api.get_list("StatusList")

    assert result == '{"records": []}'


def test_call_url_iter_without_pagination_calls_once(api, monkeypatch):
    calls = []

    def fake_call_url(url, method="get", data=None):
        calls.append(url)
        api.json_data = {"count": 10, "records": [{"id": 1}]}

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    result = api._call_url_iter("https://example/get/Table", "get", None)

    assert len(calls) == 1
    assert result["records"] == [{"id": 1}]


def test_search_to_records_returns_qirecord_list(api, monkeypatch):
    def fake_get_request(*args, **kwargs):
        return {"count": 2, "records": [{"id": 1}, {"id": 2}]}

    monkeypatch.setattr(api, "get_request", fake_get_request)

    records = api.search_to_records("Contacts", "id", "1")

    assert len(records) == 2
    assert records[0].id == 1


def test_delete_from_search_only_deletes_non_deleted(api, monkeypatch):
    def fake_get_request(*args, **kwargs):
        return {
            "records": [
                {"id": 1, "deleted": None},
                {"id": 2, "deleted": True},
                {"id": 3, "deleted": None},
            ]
        }

    deleted_ids = []

    def fake_delete_request(table, id_to_delete, auto_approve=False, print_response=False):
        deleted_ids.append(id_to_delete)

    monkeypatch.setattr(api, "get_request", fake_get_request)
    monkeypatch.setattr(api, "delete_request", fake_delete_request)

    api.delete_from_search("Contacts", "name", "Alice")

    assert deleted_ids == [1, 3]
