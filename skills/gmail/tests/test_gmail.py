"""Tests for Gmail API client module."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from claws_gmail.gmail import (
    build_raw_message,
    extract_body,
    get_access_token,
    get_header,
    handle_gmail_error,
    list_inbox,
    read_message,
    search_messages,
    send_message,
)


# --- fixtures (moved from conftest.py to avoid importlib module name collision) ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in gmail module to return a test token."""
    with patch("claws_gmail.gmail.ClawsClient") as mock_cls:
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
    """Patch google_request in gmail module."""
    with patch("claws_gmail.gmail.google_request") as mock:
        yield mock


@pytest.fixture
def sample_message_metadata():
    """Gmail API message response in format=metadata."""
    return {
        "id": "msg-001",
        "threadId": "thread-001",
        "snippet": "Hey, how are you?",
        "payload": {
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "Subject", "value": "Hello there"},
                {"name": "Date", "value": "Mon, 17 Mar 2026 10:00:00 -0700"},
            ]
        },
    }


@pytest.fixture
def sample_message_full():
    """Gmail API message response in format=full with nested MIME."""
    body_text = base64.urlsafe_b64encode(b"This is the plain text body.").decode("ascii")
    return {
        "id": "msg-002",
        "threadId": "thread-002",
        "snippet": "This is the plain text...",
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": body_text, "size": 28},
                        },
                        {
                            "mimeType": "text/html",
                            "body": {
                                "data": base64.urlsafe_b64encode(
                                    b"<p>This is the plain text body.</p>"
                                ).decode("ascii"),
                                "size": 40,
                            },
                        },
                    ],
                }
            ],
        },
    }


# --- get_access_token ---


def test_get_access_token(mock_auth_client):
    """get_access_token returns the token string from auth server."""
    token = get_access_token()
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token", {"scopes": ["https://www.googleapis.com/auth/gmail.modify"]}
    )


# --- get_header ---


def test_get_header_found():
    """get_header returns value for matching header (case-insensitive)."""
    headers = [
        {"name": "From", "value": "alice@example.com"},
        {"name": "Subject", "value": "Hi"},
    ]
    assert get_header(headers, "from") == "alice@example.com"
    assert get_header(headers, "FROM") == "alice@example.com"
    assert get_header(headers, "Subject") == "Hi"


def test_get_header_missing():
    """get_header returns empty string for missing header."""
    headers = [{"name": "From", "value": "alice@example.com"}]
    assert get_header(headers, "To") == ""


# --- extract_body ---


def test_extract_body_simple():
    """extract_body decodes text/plain body from simple payload."""
    encoded = base64.urlsafe_b64encode(b"Hello world").decode("ascii")
    payload = {
        "mimeType": "text/plain",
        "body": {"data": encoded, "size": 11},
    }
    assert extract_body(payload) == "Hello world"


def test_extract_body_nested():
    """extract_body finds text/plain in nested multipart structure."""
    encoded = base64.urlsafe_b64encode(b"Nested body text").decode("ascii")
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": encoded, "size": 16},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": "irrelevant", "size": 10},
                    },
                ],
            }
        ],
    }
    assert extract_body(payload) == "Nested body text"


def test_extract_body_missing():
    """extract_body returns empty string when no text/plain exists."""
    html_encoded = base64.urlsafe_b64encode(b"<p>HTML only</p>").decode("ascii")
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/html",
                "body": {"data": html_encoded, "size": 20},
            }
        ],
    }
    assert extract_body(payload) == ""


# --- build_raw_message ---


def test_build_raw_message():
    """build_raw_message produces base64url string with no +, /, or = chars."""
    raw = build_raw_message(to="bob@example.com", subject="Test", body="Hello")
    # Must not contain +, /, or = (base64url without padding)
    assert "+" not in raw
    assert "/" not in raw
    assert "=" not in raw
    # Decode and verify content (add padding back for decode)
    padded = raw + "=" * (4 - len(raw) % 4) if len(raw) % 4 else raw
    decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
    assert "To: bob@example.com" in decoded
    assert "Subject: Test" in decoded
    assert "Hello" in decoded


def test_build_raw_message_cc_bcc():
    """build_raw_message includes Cc and Bcc headers when provided."""
    raw = build_raw_message(
        to="bob@example.com",
        subject="Test",
        body="Hello",
        cc="cc@example.com",
        bcc="bcc@example.com",
    )
    padded = raw + "=" * (4 - len(raw) % 4) if len(raw) % 4 else raw
    decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
    assert "Cc: cc@example.com" in decoded
    assert "Bcc: bcc@example.com" in decoded


# --- list_inbox ---


def test_list_inbox(mock_auth_client, mock_google_request, sample_message_metadata):
    """list_inbox fetches IDs then metadata, returns structured dicts."""
    mock_google_request.side_effect = [
        {"messages": [{"id": "msg-001", "threadId": "thread-001"}]},
        sample_message_metadata,
    ]

    messages = list_inbox(max_results=5)

    assert len(messages) == 1
    msg = messages[0]
    assert msg["id"] == "msg-001"
    assert msg["thread_id"] == "thread-001"
    assert msg["from"] == "alice@example.com"
    assert msg["subject"] == "Hello there"
    assert msg["date"] == "Mon, 17 Mar 2026 10:00:00 -0700"
    assert msg["snippet"] == "Hey, how are you?"


def test_list_inbox_empty(mock_auth_client, mock_google_request):
    """list_inbox returns empty list when no messages exist."""
    mock_google_request.return_value = {}  # No "messages" key

    messages = list_inbox()
    assert messages == []


# --- read_message ---


def test_read_message(mock_auth_client, mock_google_request, sample_message_full):
    """read_message fetches full message and extracts text body."""
    mock_google_request.return_value = sample_message_full

    msg = read_message("msg-002")

    assert msg["id"] == "msg-002"
    assert msg["thread_id"] == "thread-002"
    assert msg["body"] == "This is the plain text body."
    assert msg["snippet"] == "This is the plain text..."


# --- send_message ---


def test_send_message(mock_auth_client, mock_google_request):
    """send_message posts base64url-encoded raw message."""
    mock_google_request.return_value = {"id": "sent-001", "threadId": "thread-sent-001"}

    result = send_message(to="bob@example.com", subject="Test", body="Hello")

    assert result["message_id"] == "sent-001"
    assert result["thread_id"] == "thread-sent-001"

    # Verify the raw field was sent
    call_kwargs = mock_google_request.call_args
    json_data = call_kwargs.kwargs.get("json")
    assert "raw" in json_data


# --- search_messages ---


def test_search_messages(mock_auth_client, mock_google_request, sample_message_metadata):
    """search_messages passes query and returns same shape as list_inbox."""
    mock_google_request.side_effect = [
        {"messages": [{"id": "msg-001", "threadId": "thread-001"}]},
        sample_message_metadata,
    ]

    messages = search_messages("from:alice", max_results=5)

    assert len(messages) == 1
    assert messages[0]["from"] == "alice@example.com"

    # Verify query was passed as params
    first_call = mock_google_request.call_args_list[0]
    params = first_call.kwargs.get("params")
    assert params["q"] == "from:alice"


# --- handle_gmail_error ---


def test_get_access_token_with_subject(mock_auth_client):
    """get_access_token(as_user=...) includes subject in auth server POST body."""
    token = get_access_token(as_user="alice@example.com")
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {"scopes": ["https://www.googleapis.com/auth/gmail.modify"], "subject": "alice@example.com"},
    )


def test_get_access_token_without_subject(mock_auth_client):
    """get_access_token() without as_user does NOT include subject in body."""
    token = get_access_token()
    assert token == "test-token"
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "subject" not in body


def test_list_inbox_passes_subject(mock_auth_client, mock_google_request):
    """list_inbox(as_user=...) threads as_user through to token_fn."""
    mock_google_request.return_value = {"messages": []}

    list_inbox(as_user="test@example.com")

    # Extract token_fn passed to google_request and invoke it to verify delegation
    token_fn = mock_google_request.call_args_list[0][0][2]
    token_fn()
    body = mock_auth_client.post_json.call_args[0][1]
    assert body["subject"] == "test@example.com"


def test_read_message_passes_subject(mock_auth_client, mock_google_request, sample_message_full):
    """read_message(msg_id, as_user=...) threads as_user through to token_fn."""
    mock_google_request.return_value = sample_message_full

    read_message("msg-002", as_user="test@example.com")

    token_fn = mock_google_request.call_args_list[0][0][2]
    token_fn()
    body = mock_auth_client.post_json.call_args[0][1]
    assert body["subject"] == "test@example.com"


def test_send_message_passes_subject(mock_auth_client, mock_google_request):
    """send_message(..., as_user=...) threads as_user through to token_fn."""
    mock_google_request.return_value = {"id": "sent-001", "threadId": "thread-sent-001"}

    send_message(to="bob@example.com", subject="Test", body="Hello", as_user="test@example.com")

    token_fn = mock_google_request.call_args_list[0][0][2]
    token_fn()
    body = mock_auth_client.post_json.call_args[0][1]
    assert body["subject"] == "test@example.com"


def test_search_messages_passes_subject(mock_auth_client, mock_google_request):
    """search_messages(query, as_user=...) threads as_user through to token_fn."""
    mock_google_request.return_value = {"messages": []}

    search_messages("from:alice", as_user="test@example.com")

    token_fn = mock_google_request.call_args_list[0][0][2]
    token_fn()
    body = mock_auth_client.post_json.call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- handle_gmail_error ---


def test_handle_gmail_error_401():
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

    with patch("claws_gmail.gmail.crash") as mock_crash:
        handle_gmail_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_gmail_error_404():
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

    with patch("claws_gmail.gmail.fail") as mock_fail:
        handle_gmail_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_gmail_error_429():
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

    with patch("claws_gmail.gmail.fail") as mock_fail:
        handle_gmail_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()
