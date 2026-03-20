from unittest.mock import patch

import httpx
import pytest
from claws_common.client import ClawsClient


@pytest.fixture
def client():
    """Client pointed at localhost for testing."""
    with patch("claws_common.client.resolve_host", return_value="127.0.0.1"):
        return ClawsClient(service="test-service", port=9999)


def test_get_success(httpx_mock, client):
    httpx_mock.add_response(json={"status": "ok"})
    result = client.get("/health")
    assert result == {"status": "ok"}


def test_get_connection_error(httpx_mock, client):
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    with pytest.raises(ConnectionError, match="Cannot connect to test-service"):
        client.get("/health")


def test_get_timeout(httpx_mock, client):
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"))
    with pytest.raises(TimeoutError, match="test-service"):
        client.get("/health")


def test_post_file_success(httpx_mock, client, tmp_path):
    test_file = tmp_path / "audio.wav"
    test_file.write_bytes(b"fake audio data")
    httpx_mock.add_response(json={"text": "hello world"})
    result = client.post_file("/transcribe", str(test_file))
    assert result == {"text": "hello world"}


def test_post_file_connection_error(httpx_mock, client, tmp_path):
    test_file = tmp_path / "audio.wav"
    test_file.write_bytes(b"fake audio data")
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    with pytest.raises(ConnectionError, match="Cannot connect to test-service"):
        client.post_file("/transcribe", str(test_file))


def test_post_json_success(httpx_mock, client):
    httpx_mock.add_response(json={"access_token": "tok", "expires_in": 3600})
    result = client.post_json("/token", {"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]})
    assert result == {"access_token": "tok", "expires_in": 3600}


def test_post_json_connection_error(httpx_mock, client):
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    with pytest.raises(ConnectionError, match="Cannot connect to test-service"):
        client.post_json("/token", {"scopes": ["a"]})


def test_post_json_timeout(httpx_mock, client):
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"))
    with pytest.raises(TimeoutError, match="test-service"):
        client.post_json("/token", {"scopes": ["a"]})


def test_get_with_params(httpx_mock, client):
    httpx_mock.add_response(json={"results": []})
    result = client.get("/search", params={"q": "test", "limit": "10"})
    assert result == {"results": []}


def test_get_without_params_unchanged(httpx_mock, client):
    httpx_mock.add_response(json={"status": "ok"})
    result = client.get("/health")
    assert result == {"status": "ok"}


def test_client_uses_resolve_host():
    with patch("claws_common.client.resolve_host", return_value="custom-host"):
        c = ClawsClient(service="svc", port=8300)
        assert c.base_url == "http://custom-host:8300"
