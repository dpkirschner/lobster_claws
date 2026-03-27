"""Tests for Google Drive API client module."""

from unittest.mock import MagicMock, call, patch

import httpx as real_httpx
import pytest
from claws_drive.drive import (
    DRIVE_BASE,
    DRIVE_SCOPE,
    DRIVE_UPLOAD_BASE,
    download_file,
    get_access_token,
    handle_drive_error,
    list_drives,
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
def mock_google_request():
    """Patch google_request in drive module."""
    with patch("claws_drive.drive.google_request") as mock:
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


def test_list_files(mock_auth_client, mock_google_request):
    """list_files returns file list from API response."""
    mock_google_request.return_value = {
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

    files = list_files()

    assert len(files) == 1
    assert files[0]["id"] == "f1"
    assert files[0]["name"] == "report.txt"

    args, kwargs = mock_google_request.call_args
    assert args[0] == "GET"
    assert args[1] == f"{DRIVE_BASE}/files"
    params = kwargs.get("params")
    assert "pageSize" in params
    assert "fields" in params


# --- list_drives ---


def test_list_drives(mock_auth_client, mock_google_request):
    """list_drives returns drives from API response."""
    mock_google_request.return_value = {
        "drives": [
            {"id": "drive-1", "name": "Engineering", "kind": "drive#drive"},
            {"id": "drive-2", "name": "Marketing", "kind": "drive#drive"},
        ]
    }

    drives = list_drives()

    assert len(drives) == 2
    assert drives[0]["id"] == "drive-1"
    assert drives[0]["name"] == "Engineering"
    assert drives[1]["id"] == "drive-2"


def test_list_drives_empty(mock_auth_client, mock_google_request):
    """list_drives returns empty list when no drives accessible."""
    mock_google_request.return_value = {}

    drives = list_drives()
    assert drives == []


def test_list_drives_as_user(mock_auth_client, mock_google_request):
    """list_drives(as_user=...) passes a token_fn that delegates to get_access_token."""
    mock_google_request.return_value = {"drives": []}

    list_drives(as_user="alice@x.com")

    # The token_fn (second positional arg) should produce a token via get_access_token
    args, kwargs = mock_google_request.call_args
    token_fn = args[2]
    # Invoke the captured token_fn to verify it calls auth with subject
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "alice@x.com"


def test_list_files_shared_drive(mock_auth_client, mock_google_request):
    """list_files(drive_id=...) adds Shared Drive params."""
    mock_google_request.return_value = {"files": []}

    list_files(drive_id="drive-abc")

    args, kwargs = mock_google_request.call_args
    params = kwargs.get("params")
    assert params["supportsAllDrives"] == "true"
    assert params["includeItemsFromAllDrives"] == "true"
    assert params["driveId"] == "drive-abc"
    assert params["corpora"] == "drive"


def test_list_files_with_query(mock_auth_client, mock_google_request):
    """list_files(query=...) passes q param to API."""
    mock_google_request.return_value = {"files": []}

    list_files(query="name contains 'report'")

    args, kwargs = mock_google_request.call_args
    params = kwargs.get("params")
    assert params["q"] == "name contains 'report'"


# --- download_file ---


def test_download_file_binary(mock_auth_client, mock_google_request, tmp_path):
    """download_file writes binary content for regular files."""
    # First call: metadata (JSON dict), second call: binary response (raw)
    content_response = MagicMock()
    content_response.content = b"fakebytes"

    mock_google_request.side_effect = [
        {
            "id": "f1",
            "name": "photo.jpg",
            "mimeType": "image/jpeg",
            "size": "100",
        },
        content_response,
    ]

    out_path = str(tmp_path / "photo.jpg")
    result = download_file("f1", out_path)

    assert result["file_id"] == "f1"
    assert result["path"] == out_path
    assert result["name"] == "photo.jpg"
    assert result["size"] == len(b"fakebytes")

    with open(out_path, "rb") as f:
        assert f.read() == b"fakebytes"


def test_download_file_shared_drive(mock_auth_client, mock_google_request, tmp_path):
    """download_file(drive_id=...) adds supportsAllDrives to metadata fetch."""
    content_response = MagicMock()
    content_response.content = b"fakebytes"

    mock_google_request.side_effect = [
        {
            "id": "f1",
            "name": "photo.jpg",
            "mimeType": "image/jpeg",
            "size": "100",
        },
        content_response,
    ]

    out_path = str(tmp_path / "photo.jpg")
    download_file("f1", out_path, drive_id="drive-abc")

    # Metadata call should include supportsAllDrives
    meta_call = mock_google_request.call_args_list[0]
    meta_params = meta_call.kwargs.get("params")
    assert meta_params["supportsAllDrives"] == "true"

    # Download call should also include supportsAllDrives
    dl_call = mock_google_request.call_args_list[1]
    dl_params = dl_call.kwargs.get("params")
    assert dl_params["supportsAllDrives"] == "true"


def test_download_file_google_doc(mock_auth_client, mock_google_request, tmp_path):
    """download_file uses export endpoint for Google Workspace documents."""
    export_response = MagicMock()
    export_response.content = b"exported text content"

    mock_google_request.side_effect = [
        {
            "id": "doc1",
            "name": "My Document",
            "mimeType": "application/vnd.google-apps.document",
            "size": "0",
        },
        export_response,
    ]

    out_path = str(tmp_path / "doc.txt")
    result = download_file("doc1", out_path)

    assert result["name"] == "My Document"
    assert result["size"] == len(b"exported text content")

    # Verify the export call used /export URL and text/plain mimeType
    second_call = mock_google_request.call_args_list[1]
    url = second_call[0][1]
    assert "/export" in url
    params = second_call.kwargs.get("params")
    assert params["mimeType"] == "text/plain"


def test_download_file_unsupported_workspace_type(mock_auth_client, mock_google_request, tmp_path):
    """download_file calls fail() for unsupported Google Workspace document types."""
    mock_google_request.return_value = {
        "id": "form1",
        "name": "My Form",
        "mimeType": "application/vnd.google-apps.form",
        "size": "0",
    }

    with patch("claws_drive.drive.fail") as mock_fail:
        download_file("form1", str(tmp_path / "form.txt"))
        mock_fail.assert_called_once()
        assert "Unsupported" in mock_fail.call_args[0][0]


# --- upload_file ---


def test_upload_file(mock_auth_client, mock_google_request, tmp_path):
    """upload_file sends multipart/related body with metadata and file content."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")

    response = MagicMock()
    response.json.return_value = {
        "id": "new-id",
        "name": "test.txt",
        "mimeType": "text/plain",
    }
    mock_google_request.return_value = response

    result = upload_file(str(test_file), "test.txt")

    assert result["id"] == "new-id"
    assert result["name"] == "test.txt"
    assert result["mimeType"] == "text/plain"

    args, kwargs = mock_google_request.call_args
    assert args[0] == "POST"
    assert "upload/drive/v3/files" in args[1]

    extra_headers = kwargs.get("extra_headers")
    assert "multipart/related" in extra_headers["Content-Type"]

    content = kwargs.get("content")
    assert b"hello world" in content
    assert b'"name": "test.txt"' in content


def test_upload_file_shared_drive(mock_auth_client, mock_google_request, tmp_path):
    """upload_file(drive_id=...) adds supportsAllDrives to URL and parents to metadata."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")

    response = MagicMock()
    response.json.return_value = {
        "id": "new-id",
        "name": "test.txt",
        "mimeType": "text/plain",
    }
    mock_google_request.return_value = response

    upload_file(str(test_file), "test.txt", drive_id="drive-abc")

    args, kwargs = mock_google_request.call_args
    url = args[1]
    assert "supportsAllDrives=true" in url

    content = kwargs.get("content")
    assert b'"parents": ["drive-abc"]' in content


def test_upload_file_with_folder(mock_auth_client, mock_google_request, tmp_path):
    """upload_file includes parents in metadata when folder_id is provided."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")

    response = MagicMock()
    response.json.return_value = {
        "id": "new-id",
        "name": "test.txt",
        "mimeType": "text/plain",
    }
    mock_google_request.return_value = response

    upload_file(str(test_file), "test.txt", folder_id="folder-123")

    args, kwargs = mock_google_request.call_args
    content = kwargs.get("content")
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
