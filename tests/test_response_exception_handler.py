import pytest

from pyQi.common import _response_exception_handler


class TestResponseExceptionHandlerSuccess:
    def test_status_200_logs_success(self):
        _response_exception_handler(200, "https://example.com/api")


class TestResponseExceptionHandlerClientErrors:
    def test_status_400_bad_request(self):
        with pytest.raises(ValueError, match="400 Bad Request"):
            _response_exception_handler(400, "https://example.com/api")

    def test_status_401_unauthorized(self):
        with pytest.raises(PermissionError, match="401 Unauthorized"):
            _response_exception_handler(401, "https://example.com/api")

    def test_status_403_forbidden(self):
        with pytest.raises(PermissionError, match="403 Forbidden"):
            _response_exception_handler(403, "https://example.com/api")

    def test_status_404_not_found(self):
        with pytest.raises(FileNotFoundError, match="404 Not Found"):
            _response_exception_handler(404, "https://example.com/api")

    def test_status_405_method_not_allowed(self):
        with pytest.raises(ValueError, match="405 Method Not Allowed"):
            _response_exception_handler(405, "https://example.com/api")

    def test_status_408_request_timeout(self):
        with pytest.raises(TimeoutError, match="408 Request Timeout"):
            _response_exception_handler(408, "https://example.com/api")

    def test_status_415_unsupported_media_type(self):
        with pytest.raises(ValueError, match="415 Unsupported Media Type"):
            _response_exception_handler(415, "https://example.com/api")

    def test_status_429_too_many_requests(self):
        with pytest.raises(RuntimeError, match="429 Too Many Requests"):
            _response_exception_handler(429, "https://example.com/api")


class TestResponseExceptionHandlerServerErrors:
    def test_status_500_internal_server_error(self):
        with pytest.raises(RuntimeError, match="500 Internal Server Error"):
            _response_exception_handler(500, "https://example.com/api")

    def test_status_501_not_implemented(self):
        with pytest.raises(NotImplementedError, match="501 Not Implemented"):
            _response_exception_handler(501, "https://example.com/api")


class TestResponseExceptionHandlerIncludesUrl:
    def test_error_message_includes_url(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            _response_exception_handler(404, "https://custom.server/api/get/Contacts")

        assert "https://custom.server/api/get/Contacts" in str(exc_info.value)

    def test_different_urls_in_errors(self):
        with pytest.raises(PermissionError) as exc_info1:
            _response_exception_handler(401, "https://server1/api")

        with pytest.raises(PermissionError) as exc_info2:
            _response_exception_handler(401, "https://server2/api")

        assert "server1" in str(exc_info1.value)
        assert "server2" in str(exc_info2.value)
