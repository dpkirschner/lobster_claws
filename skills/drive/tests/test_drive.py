"""Tests for Google Drive API client module."""

from unittest.mock import MagicMock, patch

import httpx as real_httpx
import pytest
from claws_drive.drive import (
    DRIVE_SCOPE,
    download_file,
    get_access_token,
    handle_drive_error,
    list_files,
    upload_file,
)

# --- fixtures ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in drive module to return a test token."""
    with patch("claws_drive.drive.ClawsClient") as mock_cls:
        instance = MagicMock()
        instance.post_json.return_value = {
            "access_token": "test-token",
            "expires_in": 3300,
            "token_type": "Bearer",
        }
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def mock_httpx():
    """Patch httpx in drive module."""
    with patch("claws_drive.drive.httpx") as mock:
        yield mock


# --- get_access_token ---


def test_get_access_token_default(mock_auth_client):
    """get_access_token returns token and sends drive scope without subject."""
    token = get_access_token()
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token", {"scopes": [DRIVE_SCOPE]}
    )


def test_get_access_token_as_user(mock_auth_client):
    """get_access_token(as_user=...) includes subject in POST body."""
    token = get_access_token(as_user="alice@x.com")
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {"scopes": [DRIVE_SCOPE], "subject": "alice@x.com"},
    )


# --- list_files ---


def test_list_files(mock_auth_client, mock_httpx):
    """list_files returns file list from API response."""
    response = MagicMock()
    response.json.return_value = {
        "files": [
            {
                "id": "f1",
                "name": "report.txt",
                "mimeType": "text/plain",
                "size": "1234",
                "modifiedTime": "2026-03-20T10:00:00Z",
            }
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    files = list_files()

    assert len(files) == 1
    assert files[0]["id"] == "f1"
    assert files[0]["name"] == "report.txt"

    call_kwargs = mock_httpx.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert "pageSize" in params
    assert "fields" in params


def test_list_files_with_query(mock_auth_client, mock_httpx):
    """list_files(query=...) passes q param to API."""
    response = MagicMock()
    response.json.return_value = {"files": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    list_files(query="name contains 'report'")

    call_kwargs = mock_httpx.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert params["q"] == "name contains 'report'"


# --- download_file ---


def test_download_file_binary(mock_auth_client, mock_httpx, tmp_path):
    """download_file writes binary content for regular files."""
    # First call: metadata
    meta_response = MagicMock()
    meta_response.json.return_value = {
        "id": "f1",
        "name": "photo.jpg",
        "mimeType": "image/jpeg",
        "size": "100",
    }
    meta_response.raise_for_status = MagicMock()

    # Second call: binary content
    content_response = MagicMock()
    content_response.content = b"fakebytes"
    content_response.raise_for_status = MagicMock()

    mock_httpx.get.side_effect = [meta_response, content_response]

    out_path = str(tmp_path / "photo.jpg")
    result = download_file("f1", out_path)

    assert result["file_id"] == "f1"
    assert result["path"] == out_path
    assert result["name"] == "photo.jpg"
    assert result["size"] == len(b"fakebytes")

    with open(out_path, "rb") as f:
        assert f.read() == b"fakebytes"


def test_download_file_google_doc(mock_auth_client, mock_httpx, tmp_path):
    """download_file uses export endpoint for Google Workspace documents."""
    # First call: metadata with Google Docs mimeType
    meta_response = MagicMock()
    meta_response.json.return_value = {
        "id": "doc1",
        "name": "My Document",
        "mimeType": "application/vnd.google-apps.document",
        "size": "0",
    }
    meta_response.raise_for_status = MagicMock()

    # Second call: exported content
    export_response = MagicMock()
    export_response.content = b"exported text content"
    export_response.raise_for_status = MagicMock()

    mock_httpx.get.side_effect = [meta_response, export_response]

    out_path = str(tmp_path / "doc.txt")
    result = download_file("doc1", out_path)

    assert result["name"] == "My Document"
    assert result["size"] == len(b"exported text content")

    # Verify the export call used /export URL and text/plain mimeType
    second_call = mock_httpx.get.call_args_list[1]
    url = second_call[0][0] if second_call[0] else second_call.kwargs.get("url", "")
    assert "/export" in str(url)
    params = second_call.kwargs.get("params") or second_call[1].get("params")
    assert params["mimeType"] == "text/plain"


def test_download_file_unsupported_workspace_type(mock_auth_client, mock_httpx, tmp_path):
    """download_file calls fail() for unsupported Google Workspace document types."""
    meta_response = MagicMock()
    meta_response.json.return_value = {
        "id": "form1",
        "name": "My Form",
        "mimeType": "application/vnd.google-apps.form",
        "size": "0",
    }
    meta_response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = meta_response

    with patch("claws_drive.drive.fail") as mock_fail:
        download_file("form1", str(tmp_path / "form.txt"))
        mock_fail.assert_called_once()
        assert "Unsupported" in mock_fail.call_args[0][0]


# --- upload_file ---


def test_upload_file(mock_auth_client, mock_httpx, tmp_path):
    """upload_file sends multipart/related body with metadata and file content."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")

    response = MagicMock()
    response.json.return_value = {
        "id": "new-id",
        "name": "test.txt",
        "mimeType": "text/plain",
    }
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    result = upload_file(str(test_file), "test.txt")

    assert result["id"] == "new-id"
    assert result["name"] == "test.txt"
    assert result["mimeType"] == "text/plain"

    call_kwargs = mock_httpx.post.call_args
    url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("url", "")
    assert "upload/drive/v3/files" in str(url)

    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
    assert "multipart/related" in headers["Content-Type"]

    content = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
    assert b"hello world" in content
    assert b'"name": "test.txt"' in content


def test_upload_file_with_folder(mock_auth_client, mock_httpx, tmp_path):
    """upload_file includes parents in metadata when folder_id is provided."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")

    response = MagicMock()
    response.json.return_value = {
        "id": "new-id",
        "name": "test.txt",
        "mimeType": "text/plain",
    }
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    upload_file(str(test_file), "test.txt", folder_id="folder-123")

    call_kwargs = mock_httpx.post.call_args
    content = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
    assert b'"parents": ["folder-123"]' in content


# --- handle_drive_error ---


def _make_http_error(status_code: int, message: str = "Error") -> real_httpx.HTTPStatusError:
    """Helper to create a mock HTTPStatusError."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = {
        "error": {"code": status_code, "message": message}
    }
    return real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )


def test_handle_drive_error_401():
    """401 errors call crash() with auth failure message."""
    error = _make_http_error(401, "Invalid Credentials")
    with patch("claws_drive.drive.crash") as mock_crash:
        handle_drive_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_drive_error_403():
    """403 errors call fail() with access denied message."""
    error = _make_http_error(403, "Insufficient Permission")
    with patch("claws_drive.drive.fail") as mock_fail:
        handle_drive_error(error)
        mock_fail.assert_called_once()
        assert "access denied" in mock_fail.call_args[0][0].lower()


def test_handle_drive_error_404():
    """404 errors call fail() with not found message."""
    error = _make_http_error(404, "File not found")
    with patch("claws_drive.drive.fail") as mock_fail:
        handle_drive_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_drive_error_429():
    """429 errors call fail() with rate limit message."""
    error = _make_http_error(429, "Rate Limit Exceeded")
    with patch("claws_drive.drive.fail") as mock_fail:
        handle_drive_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()


def test_handle_drive_error_500():
    """500 errors call crash() with generic error message."""
    error = _make_http_error(500, "Internal Server Error")
    with patch("claws_drive.drive.crash") as mock_crash:
        handle_drive_error(error)
        mock_crash.assert_called_once()
        assert "500" in mock_crash.call_args[0][0]
