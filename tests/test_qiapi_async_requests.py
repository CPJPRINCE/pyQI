import types

import pytest

from pyQi.QiApi_async import QiAPIAsync
from pyQi.common import QiAuthentication, base64_encode


class DummyResponse:
    def __init__(self, payload: str, status: int = 200):
        self._payload = payload
        self.status = status

    async def text(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self, payload: str):
        self.payload = payload
        self.calls = []

    def get(self, url, auth=None):
        self.calls.append((url, auth))
        return DummyResponse(self.payload)


class SpySemaphore:
    def __init__(self):
        self.enter_count = 0

    async def __aenter__(self):
        self.enter_count += 1

    async def __aexit__(self, exc_type, exc, tb):
        return False


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
async def test_get_request_builds_expected_url_and_delegates(api, monkeypatch):
    captured = {}

    async def fake_call_url_iter(url, method="get", data=None):
        captured["url"] = url
        captured["method"] = method
        captured["data"] = data
        api.json_data = {"count": 1, "records": [{"id": 1}]}
        return api.json_data

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    result = await api.get_request(
        table="Contacts",
        fields_to_search="name",
        search_term="Alice",
        per_page=50,
        sort_by="name",
    )

    assert captured["method"] == "get"
    assert captured["data"] is None
    assert "/get/Contacts/name/" in captured["url"]
    assert base64_encode("Alice") in captured["url"]
    assert "_per_page/50" in captured["url"]
    assert "_sort_by/name" in captured["url"]
    assert result == {"count": 1, "records": [{"id": 1}]}


@pytest.mark.asyncio
async def test_delete_request_builds_expected_approve_url(api, monkeypatch):
    captured = {}

    async def fake_call_url(url, method, data=None):
        captured["url"] = url
        captured["method"] = method
        captured["data"] = data

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    await api.delete_request(
        table="Contacts",
        id_to_delete=42,
        auto_approve=True,
        print_response=True,
    )

    assert captured["method"] == "delete"
    assert captured["data"] is None
    assert captured["url"].endswith("/delete/Contacts/id/42/_approve/yes")


@pytest.mark.asyncio
async def test_get_types_uses_semaphore_and_session_get(api):
    api.sem = SpySemaphore()
    api.session = DummySession('{"types": []}')

    payload = await api.get_types()

    assert api.sem.enter_count == 1
    assert payload == '{"types": []}'
    assert len(api.session.calls) == 1
    assert api.session.calls[0][0].endswith("/get/types")


@pytest.mark.asyncio
async def test_get_list_uses_semaphore_and_session_get(api):
    api.sem = SpySemaphore()
    api.session = DummySession('{"records": []}')

    payload = await api.get_list("CategoryList")

    assert api.sem.enter_count == 1
    assert payload == '{"records": []}'
    assert len(api.session.calls) == 1
    assert api.session.calls[0][0].endswith("/get/CategoryList")
