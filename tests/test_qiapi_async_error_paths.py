import types

import pytest

from pyQi.QiApi_async import QiAPIAsync
from pyQi.common import QiAuthentication


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
async def test_call_url_iter_keyboard_interrupt_returns_partial_json(api, monkeypatch):
    api.json_data = {"count": 1, "records": [{"id": 1}]}

    async def fake_call_url(url, method="get", data=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    result = await api._call_url_iter("https://example/get/Table", "get", None)

    assert result == {"count": 1, "records": [{"id": 1}]}


@pytest.mark.asyncio
async def test_call_url_iter_wraps_unexpected_errors(api, monkeypatch):
    async def fake_call_url(url, method="get", data=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "_call_url", fake_call_url)

    with pytest.raises(SystemError):
        await api._call_url_iter("https://example/get/Table", "get", None)


@pytest.mark.asyncio
async def test_update_from_file_raises_without_id_and_lookup_field(api, monkeypatch):
    class DummyFrame:
        def __init__(self):
            self.columns = types.SimpleNamespace(values=["name"])

        def to_dict(self, orient):
            return [{"name": "NoId"}]

    api.df = DummyFrame()

    def fake_read_source(file):
        return None

    async def fake_lookup_table_id(table):
        return 123

    monkeypatch.setattr(api, "_read_source", fake_read_source)
    monkeypatch.setattr(api, "lookup_table_id", fake_lookup_table_id)

    with pytest.raises(ValueError, match="No id data has been detected"):
        await api.update_from_file("dummy.xlsx", "Contacts")


@pytest.mark.asyncio
async def test_delete_from_file_raises_without_id_and_lookup_field(api, monkeypatch):
    class DummyFrame:
        def to_dict(self, orient):
            return [{"name": "NoId"}]

    api.df = DummyFrame()

    def fake_read_source(file):
        return None

    monkeypatch.setattr(api, "_read_source", fake_read_source)

    with pytest.raises(ValueError, match="No id data has been detected"):
        await api.delete_from_file("dummy.xlsx", "Contacts")
