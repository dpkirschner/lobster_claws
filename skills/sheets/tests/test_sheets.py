"""Tests for Google Sheets API client module."""

from unittest.mock import MagicMock, patch

import pytest

from claws_sheets.sheets import (
    AUTH_PORT,
    DRIVE_BASE,
    DRIVE_READONLY_SCOPE,
    SHEETS_BASE,
    SHEETS_SCOPE,
    create_spreadsheet,
    get_access_token,
    handle_sheets_error,
    list_spreadsheets,
    read_values,
    write_values,
)


# --- fixtures ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in sheets module to return a test token."""
    with patch("claws_sheets.sheets.ClawsClient") as mock_cls:
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
    """Patch httpx in sheets module."""
    with patch("claws_sheets.sheets.httpx") as mock:
        yield mock


# --- constants ---


def test_auth_port():
    """AUTH_PORT is 8301."""
    assert AUTH_PORT == 8301


def test_sheets_scope():
    """SHEETS_SCOPE is the full spreadsheets scope URL."""
    assert SHEETS_SCOPE == "https://www.googleapis.com/auth/spreadsheets"


def test_drive_readonly_scope():
    """DRIVE_READONLY_SCOPE is the drive.readonly scope URL."""
    assert DRIVE_READONLY_SCOPE == "https://www.googleapis.com/auth/drive.readonly"


def test_sheets_base():
    """SHEETS_BASE is the Sheets API v4 URL."""
    assert SHEETS_BASE == "https://sheets.googleapis.com/v4/spreadsheets"


def test_drive_base():
    """DRIVE_BASE is the Drive API v3 URL."""
    assert DRIVE_BASE == "https://www.googleapis.com/drive/v3"


# --- get_access_token ---


def test_get_access_token_requests_both_scopes(mock_auth_client):
    """get_access_token requests BOTH spreadsheets and drive.readonly scopes."""
    token = get_access_token()
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {
            "scopes": [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
        },
    )


def test_get_access_token_with_subject(mock_auth_client):
    """get_access_token(as_user=...) includes subject in POST body."""
    token = get_access_token(as_user="alice@example.com")
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {
            "scopes": [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
            "subject": "alice@example.com",
        },
    )


def test_get_access_token_without_subject(mock_auth_client):
    """get_access_token() without as_user does NOT include subject in body."""
    get_access_token()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "subject" not in body


# --- list_spreadsheets ---


def test_list_spreadsheets(mock_auth_client, mock_httpx):
    """list_spreadsheets uses Drive API with mimeType query filter."""
    response = MagicMock()
    response.json.return_value = {
        "files": [
            {"id": "sheet-1", "name": "Budget", "modifiedTime": "2026-01-01T00:00:00Z"}
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    files = list_spreadsheets(max_results=50)

    assert len(files) == 1
    assert files[0]["id"] == "sheet-1"
    assert files[0]["name"] == "Budget"

    # Verify Drive API call with correct mimeType query
    call_args = mock_httpx.get.call_args
    url = call_args[0][0]
    assert "drive/v3/files" in url
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert "application/vnd.google-apps.spreadsheet" in params["q"]
    assert params["pageSize"] == 50


def test_list_spreadsheets_empty(mock_auth_client, mock_httpx):
    """list_spreadsheets returns empty list when no files."""
    response = MagicMock()
    response.json.return_value = {}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    files = list_spreadsheets()
    assert files == []


def test_list_spreadsheets_passes_subject(mock_auth_client, mock_httpx):
    """list_spreadsheets(as_user=...) threads as_user through to get_access_token."""
    response = MagicMock()
    response.json.return_value = {"files": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    list_spreadsheets(as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- read_values ---


def test_read_values(mock_auth_client, mock_httpx):
    """read_values calls correct Sheets API URL and returns values array."""
    response = MagicMock()
    response.json.return_value = {
        "range": "Sheet1!A1:B2",
        "values": [["a", "b"], ["c", "d"]],
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    values = read_values("sheet-123", "Sheet1!A1:B2")

    assert values == [["a", "b"], ["c", "d"]]

    # Verify URL
    call_args = mock_httpx.get.call_args
    url = call_args[0][0]
    assert "sheet-123" in url
    assert "Sheet1!A1:B2" in url
    assert "sheets.googleapis.com" in url


def test_read_values_empty(mock_auth_client, mock_httpx):
    """read_values returns empty list when no values in range."""
    response = MagicMock()
    response.json.return_value = {"range": "Sheet1!A1:B2"}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    values = read_values("sheet-123", "Sheet1!A1:B2")
    assert values == []


def test_read_values_passes_subject(mock_auth_client, mock_httpx):
    """read_values(as_user=...) threads as_user through to get_access_token."""
    response = MagicMock()
    response.json.return_value = {"values": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    read_values("sheet-123", "Sheet1!A1:B2", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- write_values ---


def test_write_values(mock_auth_client, mock_httpx):
    """write_values calls PUT with valueInputOption=USER_ENTERED."""
    response = MagicMock()
    response.json.return_value = {
        "spreadsheetId": "sheet-123",
        "updatedRange": "Sheet1!A1:B2",
        "updatedRows": 2,
        "updatedColumns": 2,
        "updatedCells": 4,
    }
    response.raise_for_status = MagicMock()
    mock_httpx.put.return_value = response

    result = write_values("sheet-123", "Sheet1!A1:B2", [["a", "b"], ["c", "d"]])

    assert result["updatedCells"] == 4

    # Verify PUT URL and params
    call_args = mock_httpx.put.call_args
    url = call_args[0][0]
    assert "sheet-123" in url
    assert "Sheet1!A1:B2" in url
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["valueInputOption"] == "USER_ENTERED"

    # Verify body
    json_data = call_args.kwargs.get("json") or call_args[1].get("json")
    assert json_data["range"] == "Sheet1!A1:B2"
    assert json_data["values"] == [["a", "b"], ["c", "d"]]


def test_write_values_passes_subject(mock_auth_client, mock_httpx):
    """write_values(as_user=...) threads as_user through to get_access_token."""
    response = MagicMock()
    response.json.return_value = {}
    response.raise_for_status = MagicMock()
    mock_httpx.put.return_value = response

    write_values("sheet-123", "Sheet1!A1:B2", [["a"]], as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- create_spreadsheet ---


def test_create_spreadsheet(mock_auth_client, mock_httpx):
    """create_spreadsheet posts with properties.title and returns id+title."""
    response = MagicMock()
    response.json.return_value = {
        "spreadsheetId": "new-sheet-1",
        "properties": {"title": "My Sheet"},
    }
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    result = create_spreadsheet("My Sheet")

    assert result["spreadsheetId"] == "new-sheet-1"
    assert result["title"] == "My Sheet"

    # Verify POST body
    call_args = mock_httpx.post.call_args
    url = call_args[0][0]
    assert "sheets.googleapis.com" in url
    json_data = call_args.kwargs.get("json") or call_args[1].get("json")
    assert json_data["properties"]["title"] == "My Sheet"


def test_create_spreadsheet_passes_subject(mock_auth_client, mock_httpx):
    """create_spreadsheet(as_user=...) threads as_user through to get_access_token."""
    response = MagicMock()
    response.json.return_value = {
        "spreadsheetId": "new-sheet-1",
        "properties": {"title": "Test"},
    }
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    create_spreadsheet("Test", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- handle_sheets_error ---


def test_handle_sheets_error_401():
    """401 errors call crash() with auth failure message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {"code": 401, "message": "Invalid Credentials"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_sheets.sheets.crash") as mock_crash:
        handle_sheets_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_sheets_error_403():
    """403 errors call fail() with access denied message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {"code": 403, "message": "Forbidden"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_sheets.sheets.fail") as mock_fail:
        handle_sheets_error(error)
        mock_fail.assert_called_once()
        assert "denied" in mock_fail.call_args[0][0].lower()


def test_handle_sheets_error_404():
    """404 errors call fail() with not found message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {
        "error": {"code": 404, "message": "Not Found"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_sheets.sheets.fail") as mock_fail:
        handle_sheets_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_sheets_error_429():
    """429 errors call fail() with rate limit message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {
        "error": {"code": 429, "message": "Rate Limit Exceeded"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_sheets.sheets.fail") as mock_fail:
        handle_sheets_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()


def test_handle_sheets_error_500():
    """500 errors call crash() with generic error message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        "error": {"code": 500, "message": "Internal Server Error"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_sheets.sheets.crash") as mock_crash:
        handle_sheets_error(error)
        mock_crash.assert_called_once()
        assert "500" in mock_crash.call_args[0][0]
