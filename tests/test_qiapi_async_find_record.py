import types

import pytest

from pyQi.QiApi_async import QiAPIAsync
from pyQi.common import QiAuthentication, QiRecord


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
async def test_find_record_returns_qirecord(api, monkeypatch):
    async def fake_get_request(*args, **kwargs):
        api.json_data = {
            "records": [
                {"id": 123, "name": "Alice", "status": "active"},
            ]
        }
        return api.json_data

    monkeypatch.setattr(api, "get_request", fake_get_request)

    record = await api.find_record(
        table="Contacts",
        fields_to_search="name",
        search_term="Alice",
    )

    assert isinstance(record, QiRecord)
    assert record.id == 123
    assert record.name == "Alice"
    assert record.status == "active"


@pytest.mark.asyncio
async def test_find_record_by_id_forwards_expected_search_params(api, monkeypatch):
    captured = {}

    async def fake_get_request(*args, **kwargs):
        captured.update(kwargs)
        api.json_data = {"records": [{"id": "42", "name": "Bob"}]}
        return api.json_data

    monkeypatch.setattr(api, "get_request", fake_get_request)

    record = await api.find_record_by_id(
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
