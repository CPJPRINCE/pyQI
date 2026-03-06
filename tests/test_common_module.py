import json
import types

import pytest

from pyQi.common import (
    QiAuthentication,
    QiRecord,
    QiRecords,
    _response_exception_handler,
    base64_encode,
    parse_data,
)


def test_parse_data_from_dict():
    payload = {"a": 1, "b": "x"}
    assert parse_data(payload) == json.dumps(payload)


def test_parse_data_from_string():
    assert parse_data("hello") == '"hello"'


def test_base64_encode_known_value():
    assert base64_encode("abc") == "base64:YWJj"


def test_response_exception_handler_200_no_error():
    _response_exception_handler(200, "https://example/api")


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (400, ValueError),
        (401, PermissionError),
        (403, PermissionError),
        (404, FileNotFoundError),
        (405, ValueError),
        (408, TimeoutError),
        (415, ValueError),
        (429, RuntimeError),
        (500, RuntimeError),
        (501, NotImplementedError),
    ],
)
def test_response_exception_handler_error_mappings(status, error_type):
    with pytest.raises(error_type):
        _response_exception_handler(status, "https://example/api")


def test_qirecord_dynamic_attributes_and_serialization():
    record = QiRecord(id=1, name="Alpha")

    assert record.id == 1
    assert record.name == "Alpha"
    assert record.to_dict() == {"id": 1, "name": "Alpha"}
    assert json.loads(record.to_json()) == {"id": 1, "name": "Alpha"}


def test_qirecords_with_none_payload():
    records = QiRecords(None)

    assert records.total == 0
    assert records.records == []
    assert records.records_list == []
    assert records.to_dict() is None


def test_qirecords_converts_records_to_objects():
    payload = {
        "count": 2,
        "records": [
            {"id": 1, "name": "One"},
            {"id": 2, "name": "Two"},
        ],
    }

    records = QiRecords(payload)

    assert records.total == 2
    assert len(records.records) == 2
    assert isinstance(records.records[0], QiRecord)
    assert records.records[1].name == "Two"


def test_qirecords_json_to_file_and_json_tostring(tmp_path):
    payload = {"count": 1, "records": [{"id": 123}]}
    records = QiRecords(payload)

    output = tmp_path / "records.json"
    records.json_to_file(str(output))

    assert json.loads(output.read_text(encoding="utf-8")) == payload
    assert json.loads(records.json_tostring()) == payload


def test_auth_helpers_without_real_login(monkeypatch):
    monkeypatch.setattr(
        QiAuthentication,
        "qi_login",
        lambda self: types.SimpleNamespace(username=self.username, password=self.password),
    )

    auth = QiAuthentication("user", "server.example", "pass")

    assert auth._keyring_entry_name() == "pyQi:server.example"
    assert auth._get_password_from_keyring("user") is None


def test_set_password_in_keyring_noop_when_flag_disabled(monkeypatch):
    monkeypatch.setattr(
        QiAuthentication,
        "qi_login",
        lambda self: types.SimpleNamespace(username=self.username, password=self.password),
    )

    auth = QiAuthentication("user", "server.example", "pass")

    assert auth._set_password_in_keyring("user", "secret") is None
