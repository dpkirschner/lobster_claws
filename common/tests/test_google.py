"""Tests for google_request retry-on-401 logic."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from claws_common.google import google_request, invalidate_token_cache


@pytest.fixture
def mock_httpx_request():
    with patch("claws_common.google.httpx.request") as mock:
        yield mock


@pytest.fixture
def mock_invalidate():
    with patch("claws_common.google.invalidate_token_cache") as mock:
        yield mock


def _make_response(status_code, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=MagicMock(), response=resp
        )
    return resp


def test_success_no_retry(mock_httpx_request, mock_invalidate):
    """Successful request returns JSON without retry."""
    mock_httpx_request.return_value = _make_response(200, {"ok": True})
    token_fn = MagicMock(return_value="token-1")

    result = google_request("GET", "https://api.example.com/data", token_fn)

    assert result == {"ok": True}
    assert token_fn.call_count == 1
    mock_invalidate.assert_not_called()


def test_401_retry_success(mock_httpx_request, mock_invalidate):
    """401 triggers cache clear, fresh token, and successful retry."""
    mock_httpx_request.side_effect = [
        _make_response(401),
        _make_response(200, {"retried": True}),
    ]
    token_fn = MagicMock(side_effect=["stale-token", "fresh-token"])

    result = google_request("GET", "https://api.example.com/data", token_fn)

    assert result == {"retried": True}
    assert token_fn.call_count == 2
    mock_invalidate.assert_called_once()


def test_401_retry_401_raises(mock_httpx_request, mock_invalidate):
    """Two consecutive 401s raises HTTPStatusError."""
    mock_httpx_request.side_effect = [
        _make_response(401),
        _make_response(401),
    ]
    token_fn = MagicMock(side_effect=["stale-token", "also-stale"])

    with pytest.raises(httpx.HTTPStatusError):
        google_request("GET", "https://api.example.com/data", token_fn)

    mock_invalidate.assert_called_once()


def test_non_401_error_raises_immediately(mock_httpx_request, mock_invalidate):
    """Non-401 errors raise without retry."""
    mock_httpx_request.return_value = _make_response(403)
    token_fn = MagicMock(return_value="token-1")

    with pytest.raises(httpx.HTTPStatusError):
        google_request("GET", "https://api.example.com/data", token_fn)

    assert token_fn.call_count == 1
    mock_invalidate.assert_not_called()


def test_raw_returns_response(mock_httpx_request, mock_invalidate):
    """raw=True returns the Response object instead of JSON."""
    resp = _make_response(200, {"data": "value"})
    mock_httpx_request.return_value = resp
    token_fn = MagicMock(return_value="token-1")

    result = google_request("GET", "https://api.example.com/data", token_fn, raw=True)

    assert result is resp


def test_extra_headers_merged(mock_httpx_request, mock_invalidate):
    """extra_headers are merged with the auth header."""
    mock_httpx_request.return_value = _make_response(200, {})
    token_fn = MagicMock(return_value="token-1")

    google_request(
        "POST", "https://api.example.com/upload", token_fn,
        extra_headers={"Content-Type": "multipart/related"},
    )

    call_headers = mock_httpx_request.call_args.kwargs["headers"]
    assert call_headers["Authorization"] == "Bearer token-1"
    assert call_headers["Content-Type"] == "multipart/related"


def test_invalidate_token_cache_calls_delete():
    """invalidate_token_cache calls DELETE /cache on auth server."""
    with patch("claws_common.google.ClawsClient") as MockClient:
        instance = MagicMock()
        instance.delete.return_value = {"cleared": 3}
        MockClient.return_value = instance

        result = invalidate_token_cache()

        assert result == {"cleared": 3}
        instance.delete.assert_called_once_with("/cache", params=None)


def test_invalidate_token_cache_with_subject():
    """invalidate_token_cache passes subject as query param."""
    with patch("claws_common.google.ClawsClient") as MockClient:
        instance = MagicMock()
        instance.delete.return_value = {"cleared": 1}
        MockClient.return_value = instance

        invalidate_token_cache(subject="alice@example.com")

        instance.delete.assert_called_once_with(
            "/cache", params={"subject": "alice@example.com"}
        )
