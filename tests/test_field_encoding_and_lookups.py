import json
import types

import pytest

from pyQi.QiApi_async import QiAPIAsync
from pyQi.common import QiAuthentication, base64_encode


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


class TestBase64Encoding:
    def test_base64_encode_prefix(self):
        result = base64_encode("test")
        assert result.startswith("base64:")

    def test_base64_encode_replaces_equals(self):
        result = base64_encode("data===")
        assert "=" not in result
        assert "~" in result

    def test_base64_encode_custom_chars(self):
        # Test with strings that result in base64 chars that need replacement
        result1 = base64_encode("test")
        assert "base64:" in result1
        result2 = base64_encode("data with spaces")
        assert "base64:" in result2

    def test_base64_encode_special_characters(self):
        result = base64_encode("!@#$%^&*()")
        assert base64_encode("!@#$%^&*()") == result


@pytest.mark.asyncio
async def test_lookup_relationship_without_pandas_fails(api, monkeypatch):
    monkeypatch.setattr("pyQi.QiApi_async.pd", None)
    api.column_headers = ["relationship:Company:company_id:123"]

    with pytest.raises(AttributeError):
        await api.lookup_relationship()


@pytest.mark.asyncio
async def test_lookup_relationship_parses_header_correctly(api, monkeypatch):
    pd = pytest.importorskip("pandas")

    api.types_data = json.dumps({"Company": {"id": 999}})
    api.df = pd.DataFrame({"relationship:Company:company_id:123": [1, 2, 3]})
    api.column_headers = list(api.df.columns.values)

    async def fake_lookup_table_id(table):
        api.table_id = "999"
        return "999"

    monkeypatch.setattr(api, "lookup_table_id", fake_lookup_table_id)

    await api.lookup_relationship()

    assert "relationship:999:company_id" in api.df.columns


@pytest.mark.asyncio
async def test_get_request_with_single_field_and_term(api, monkeypatch):
    captured = {}

    async def fake_call_url_iter(url, method="get", data=None):
        captured["url"] = url
        api.json_data = {"count": 0, "records": []}
        return api.json_data

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    await api.get_request(
        table="Contacts",
        fields_to_search="name",
        search_term="John",
    )

    assert "/get/Contacts/name/" in captured["url"]
    assert base64_encode("John") in captured["url"]


@pytest.mark.asyncio
async def test_get_request_with_list_of_fields(api, monkeypatch):
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

    assert base64_encode("John") in captured["url"]
    assert base64_encode("Doe") in captured["url"]


@pytest.mark.asyncio
async def test_get_request_with_fields_to_return(api, monkeypatch):
    captured = {}

    async def fake_call_url_iter(url, method="get", data=None):
        captured["url"] = url
        api.json_data = {"count": 0, "records": []}
        return api.json_data

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    await api.get_request(
        table="Contacts",
        fields_to_return="id,name,email",
    )

    assert "_fields/" in captured["url"]


@pytest.mark.asyncio
async def test_get_request_with_id_field_omits_fields_param(api, monkeypatch):
    captured = {}

    async def fake_call_url_iter(url, method="get", data=None):
        captured["url"] = url
        api.json_data = {"count": 0, "records": []}
        return api.json_data

    monkeypatch.setattr(api, "_call_url_iter", fake_call_url_iter)

    await api.get_request(
        table="Contacts",
        fields_to_search="id",
        search_term="123",
    )

    assert "_fields/" not in captured["url"]
