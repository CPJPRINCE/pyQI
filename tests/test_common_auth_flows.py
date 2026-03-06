import types
from unittest.mock import Mock, MagicMock

import pytest

import pyQi.common as common_mod
from pyQi.common import QiAuthentication


class DummyResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


def test_qi_login_uses_credentials_file_short_circuit(monkeypatch):
    def fail_requests_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called in credentials_file mode")

    monkeypatch.setattr(common_mod.requests, "get", fail_requests_get)
    
    # Mock configparser to return credentials from file
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda section, key, fallback=None: {
        'username': 'file_user@example.com',
        'password': 'file_pass'
    }.get(key, fallback)
    
    mock_config_parser = MagicMock(return_value=mock_config)
    monkeypatch.setattr('pyQi.common.configparser.ConfigParser', mock_config_parser)

    auth = QiAuthentication(
        "user@example.com",
        "server.example",
        "pass",
        credentials_file="/tmp/creds.properties",
    )

    assert auth.auth.username == "file_user@example.com"
    assert auth.auth.password == "file_pass"


def test_qi_login_uses_given_password_and_tests_login(monkeypatch):
    called = {}

    def fake_requests_get(url, auth=None):
        called["url"] = url
        called["auth"] = auth
        return DummyResponse(status_code=200)

    monkeypatch.setattr(common_mod.requests, "get", fake_requests_get)

    auth = QiAuthentication("user", "server.example", "pass")

    assert called["url"] == "https://server.example/api"
    assert auth.auth.username == "user"
    assert auth.auth.password == "pass"


def test_qi_login_prompts_when_no_password(monkeypatch):
    monkeypatch.setattr(common_mod.requests, "get", lambda *a, **k: DummyResponse(200))
    monkeypatch.setattr(common_mod, "getpass", lambda prompt: "prompted-pass")

    auth = QiAuthentication("user", "server.example", None)

    assert auth.password == "prompted-pass"
    assert auth.auth.password == "prompted-pass"


def test_qi_login_reads_from_keyring_when_enabled(monkeypatch):
    monkeypatch.setattr(common_mod.requests, "get", lambda *a, **k: DummyResponse(200))

    fake_keyring = types.SimpleNamespace(get_password=lambda service, username: "stored-pass")
    monkeypatch.setattr(common_mod, "keyring", fake_keyring)

    auth = QiAuthentication("user", "server.example", None, use_keyring=True)

    assert auth.password == "stored-pass"


def test_qi_login_saves_to_keyring_when_enabled(monkeypatch):
    monkeypatch.setattr(common_mod.requests, "get", lambda *a, **k: DummyResponse(200))
    monkeypatch.setattr(common_mod, "getpass", lambda prompt: "prompted-pass")

    calls = {}

    def fake_set_password(service, username, password):
        calls["service"] = service
        calls["username"] = username
        calls["password"] = password

    fake_keyring = types.SimpleNamespace(
        get_password=lambda service, username: None,
        set_password=fake_set_password,
    )
    monkeypatch.setattr(common_mod, "keyring", fake_keyring)

    auth = QiAuthentication(
        "user",
        "server.example",
        None,
        use_keyring=True,
        save_password_to_keyring=True,
    )

    assert auth.password == "prompted-pass"
    assert calls["service"] == "pyQi:server.example"
    assert calls["username"] == "user"
    assert calls["password"] == "prompted-pass"


def test_get_password_from_keyring_returns_none_when_user_or_server_missing(monkeypatch):
    monkeypatch.setattr(QiAuthentication, "qi_login", lambda self: None)
    auth = QiAuthentication("", "", "pass", use_keyring=True)

    assert auth._get_password_from_keyring("") is None


def test_get_password_from_keyring_raises_if_keyring_unavailable(monkeypatch):
    monkeypatch.setattr(QiAuthentication, "qi_login", lambda self: None)
    monkeypatch.setattr(common_mod, "keyring", None)

    auth = QiAuthentication("user", "server.example", "pass", use_keyring=True)

    with pytest.raises(RuntimeError, match="keyring package is not installed"):
        auth._get_password_from_keyring("user")


def test_set_password_in_keyring_raises_if_keyring_unavailable(monkeypatch):
    monkeypatch.setattr(QiAuthentication, "qi_login", lambda self: None)
    monkeypatch.setattr(common_mod, "keyring", None)

    auth = QiAuthentication(
        "user",
        "server.example",
        "pass",
        save_password_to_keyring=True,
    )

    with pytest.raises(RuntimeError, match="keyring package is not installed"):
        auth._set_password_in_keyring("user", "secret")
