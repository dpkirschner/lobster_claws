"""Tests for Google Docs API client module."""

from unittest.mock import MagicMock, patch

import pytest
from claws_docs.docs import (
    append_text,
    create_document,
    extract_text,
    get_access_token,
    handle_docs_error,
    list_documents,
    read_document,
)

# --- fixtures ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in docs module to return a test token."""
    with patch("claws_docs.docs.ClawsClient") as mock_cls:
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
    """Patch google_request in docs module."""
    with patch("claws_docs.docs.google_request") as mock:
        yield mock


# --- get_access_token ---


def test_get_access_token_requests_both_scopes(mock_auth_client):
    """get_access_token requests BOTH docs and drive.readonly scopes."""
    token = get_access_token()
    assert token == "test-token"
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "https://www.googleapis.com/auth/documents" in body["scopes"]
    assert "https://www.googleapis.com/auth/drive.readonly" in body["scopes"]


def test_get_access_token_with_subject(mock_auth_client):
    """get_access_token(as_user=...) includes subject in auth server POST body."""
    token = get_access_token(as_user="alice@example.com")
    assert token == "test-token"
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "alice@example.com"


def test_get_access_token_without_subject(mock_auth_client):
    """get_access_token() without as_user does NOT include subject in body."""
    get_access_token()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "subject" not in body


# --- extract_text ---


def test_extract_text_with_paragraphs():
    """extract_text concatenates textRun content from paragraphs."""
    document = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello "}},
                            {"textRun": {"content": "world\n"}},
                        ]
                    }
                },
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Second paragraph\n"}},
                        ]
                    }
                },
            ]
        }
    }
    assert extract_text(document) == "Hello world\nSecond paragraph\n"


def test_extract_text_empty_document():
    """extract_text returns empty string for doc with no body/content."""
    assert extract_text({}) == ""
    assert extract_text({"body": {}}) == ""
    assert extract_text({"body": {"content": []}}) == ""


def test_extract_text_mixed_elements():
    """extract_text handles elements with and without textRun."""
    document = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Has text\n"}},
                            {"inlineObjectElement": {"inlineObjectId": "obj1"}},
                            {"textRun": {"content": "More text\n"}},
                        ]
                    }
                },
                {"sectionBreak": {}},  # Non-paragraph element
            ]
        }
    }
    assert extract_text(document) == "Has text\nMore text\n"


def test_extract_text_paragraph_no_text_runs():
    """extract_text handles paragraphs with no textRun elements."""
    document = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"inlineObjectElement": {"inlineObjectId": "obj1"}},
                        ]
                    }
                },
            ]
        }
    }
    assert extract_text(document) == ""


# --- list_documents ---


def test_list_documents(mock_auth_client, mock_google_request):
    """list_documents calls Drive API with correct mimeType filter."""
    mock_google_request.return_value = {
        "files": [
            {"id": "doc1", "name": "My Doc", "modifiedTime": "2026-03-20T10:00:00Z"},
        ]
    }

    docs = list_documents(max_results=50)

    assert len(docs) == 1
    assert docs[0]["id"] == "doc1"

    # Verify google_request call
    call_args = mock_google_request.call_args
    assert call_args[0][0] == "GET"
    assert "drive/v3/files" in call_args[0][1]
    params = call_args[1]["params"]
    assert "mimeType='application/vnd.google-apps.document'" in params["q"]
    assert params["pageSize"] == 50


def test_list_documents_as_user(mock_auth_client, mock_google_request):
    """list_documents(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"files": []}

    list_documents(as_user="test@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- read_document ---


def test_read_document(mock_auth_client, mock_google_request):
    """read_document calls GET then extract_text, returns structured dict."""
    mock_google_request.return_value = {
        "documentId": "doc-123",
        "title": "Test Doc",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Document content\n"}},
                        ]
                    }
                }
            ]
        },
    }

    result = read_document("doc-123")

    assert result["documentId"] == "doc-123"
    assert result["title"] == "Test Doc"
    assert result["text"] == "Document content\n"

    # Verify google_request call
    call_args = mock_google_request.call_args
    assert call_args[0][0] == "GET"
    assert "docs.googleapis.com/v1/documents/doc-123" in call_args[0][1]


def test_read_document_as_user(mock_auth_client, mock_google_request):
    """read_document(doc_id, as_user=...) threads as_user through."""
    mock_google_request.return_value = {
        "documentId": "doc-123",
        "title": "Test",
        "body": {"content": []},
    }

    read_document("doc-123", as_user="test@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- create_document ---


def test_create_document_without_body(mock_auth_client, mock_google_request):
    """create_document without body makes single POST to create blank doc."""
    mock_google_request.return_value = {
        "documentId": "new-doc-1",
        "title": "My New Doc",
    }

    result = create_document(title="My New Doc")

    assert result["documentId"] == "new-doc-1"
    assert result["title"] == "My New Doc"

    # Should only call google_request once (no batchUpdate)
    assert mock_google_request.call_count == 1
    call_args = mock_google_request.call_args
    assert call_args[0][0] == "POST"
    assert "docs.googleapis.com/v1/documents" in call_args[0][1]
    assert call_args[1]["json"] == {"title": "My New Doc"}


def test_create_document_with_body(mock_auth_client, mock_google_request):
    """create_document with body makes POST to create then batchUpdate with InsertTextRequest."""
    mock_google_request.side_effect = [
        {"documentId": "new-doc-2", "title": "Doc With Body"},
        {"replies": []},
    ]

    result = create_document(title="Doc With Body", body="Hello world")

    assert result["documentId"] == "new-doc-2"
    assert result["title"] == "Doc With Body"

    # Should call google_request twice (create + batchUpdate)
    assert mock_google_request.call_count == 2

    # Second call should be batchUpdate
    batch_call = mock_google_request.call_args_list[1]
    assert "batchUpdate" in batch_call[0][1]
    json_data = batch_call[1]["json"]
    assert json_data["requests"][0]["insertText"]["text"] == "Hello world"
    assert "endOfSegmentLocation" in json_data["requests"][0]["insertText"]


def test_create_document_as_user(mock_auth_client, mock_google_request):
    """create_document(title, as_user=...) threads as_user through."""
    mock_google_request.return_value = {"documentId": "new-1", "title": "T"}

    create_document(title="T", as_user="test@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- append_text ---


def test_append_text(mock_auth_client, mock_google_request):
    """append_text sends batchUpdate with InsertTextRequest and endOfSegmentLocation."""
    mock_google_request.return_value = {"replies": []}

    append_text("doc-123", "More text here")

    call_args = mock_google_request.call_args
    assert call_args[0][0] == "POST"
    assert "doc-123:batchUpdate" in call_args[0][1]
    json_data = call_args[1]["json"]
    requests = json_data["requests"]
    assert len(requests) == 1
    insert = requests[0]["insertText"]
    assert insert["text"] == "More text here"
    assert insert["endOfSegmentLocation"] == {}


def test_append_text_as_user(mock_auth_client, mock_google_request):
    """append_text(doc_id, text, as_user=...) threads as_user through."""
    mock_google_request.return_value = {"replies": []}

    append_text("doc-123", "text", as_user="test@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- handle_docs_error ---


def test_handle_docs_error_401():
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

    with patch("claws_docs.docs.crash") as mock_crash:
        handle_docs_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_docs_error_403():
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

    with patch("claws_docs.docs.fail") as mock_fail:
        handle_docs_error(error)
        mock_fail.assert_called_once()
        assert "denied" in mock_fail.call_args[0][0].lower()


def test_handle_docs_error_404():
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

    with patch("claws_docs.docs.fail") as mock_fail:
        handle_docs_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_docs_error_429():
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

    with patch("claws_docs.docs.fail") as mock_fail:
        handle_docs_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()


def test_handle_docs_error_500():
    """500 errors call crash() with generic message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        "error": {"code": 500, "message": "Internal Server Error"}
    }
    error = real_httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("claws_docs.docs.crash") as mock_crash:
        handle_docs_error(error)
        mock_crash.assert_called_once()
