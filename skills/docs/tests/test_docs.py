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
def mock_httpx():
    """Patch httpx in docs module."""
    with patch("claws_docs.docs.httpx") as mock:
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


def test_list_documents(mock_auth_client, mock_httpx):
    """list_documents calls Drive API with correct mimeType filter."""
    response = MagicMock()
    response.json.return_value = {
        "files": [
            {"id": "doc1", "name": "My Doc", "modifiedTime": "2026-03-20T10:00:00Z"},
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    docs = list_documents(max_results=50)

    assert len(docs) == 1
    assert docs[0]["id"] == "doc1"

    # Verify Drive API call
    call_args = mock_httpx.get.call_args
    url = call_args[0][0]
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert "drive/v3/files" in url
    assert "mimeType='application/vnd.google-apps.document'" in params["q"]
    assert params["pageSize"] == 50


def test_list_documents_as_user(mock_auth_client, mock_httpx):
    """list_documents(as_user=...) threads as_user through to get_access_token."""
    response = MagicMock()
    response.json.return_value = {"files": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    list_documents(as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- read_document ---


def test_read_document(mock_auth_client, mock_httpx):
    """read_document calls GET then extract_text, returns structured dict."""
    doc_response = {
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
    response = MagicMock()
    response.json.return_value = doc_response
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    result = read_document("doc-123")

    assert result["documentId"] == "doc-123"
    assert result["title"] == "Test Doc"
    assert result["text"] == "Document content\n"

    # Verify Docs API call
    call_args = mock_httpx.get.call_args
    url = call_args[0][0]
    assert "docs.googleapis.com/v1/documents/doc-123" in url


def test_read_document_as_user(mock_auth_client, mock_httpx):
    """read_document(doc_id, as_user=...) threads as_user through."""
    response = MagicMock()
    response.json.return_value = {
        "documentId": "doc-123",
        "title": "Test",
        "body": {"content": []},
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    read_document("doc-123", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- create_document ---


def test_create_document_without_body(mock_auth_client, mock_httpx):
    """create_document without body makes single POST to create blank doc."""
    create_response = MagicMock()
    create_response.json.return_value = {
        "documentId": "new-doc-1",
        "title": "My New Doc",
    }
    create_response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = create_response

    result = create_document(title="My New Doc")

    assert result["documentId"] == "new-doc-1"
    assert result["title"] == "My New Doc"

    # Should only call POST once (no batchUpdate)
    assert mock_httpx.post.call_count == 1
    call_args = mock_httpx.post.call_args
    url = call_args[0][0]
    assert "docs.googleapis.com/v1/documents" in url
    json_data = call_args.kwargs.get("json") or call_args[1].get("json")
    assert json_data == {"title": "My New Doc"}


def test_create_document_with_body(mock_auth_client, mock_httpx):
    """create_document with body makes POST to create then batchUpdate with InsertTextRequest."""
    create_response = MagicMock()
    create_response.json.return_value = {
        "documentId": "new-doc-2",
        "title": "Doc With Body",
    }
    create_response.raise_for_status = MagicMock()

    batch_response = MagicMock()
    batch_response.json.return_value = {"replies": []}
    batch_response.raise_for_status = MagicMock()

    mock_httpx.post.side_effect = [create_response, batch_response]

    result = create_document(title="Doc With Body", body="Hello world")

    assert result["documentId"] == "new-doc-2"
    assert result["title"] == "Doc With Body"

    # Should call POST twice (create + batchUpdate)
    assert mock_httpx.post.call_count == 2

    # Second call should be batchUpdate
    batch_call = mock_httpx.post.call_args_list[1]
    url = batch_call[0][0]
    assert "batchUpdate" in url
    json_data = batch_call.kwargs.get("json") or batch_call[1].get("json")
    assert json_data["requests"][0]["insertText"]["text"] == "Hello world"
    assert "endOfSegmentLocation" in json_data["requests"][0]["insertText"]


def test_create_document_as_user(mock_auth_client, mock_httpx):
    """create_document(title, as_user=...) threads as_user through."""
    response = MagicMock()
    response.json.return_value = {"documentId": "new-1", "title": "T"}
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    create_document(title="T", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- append_text ---


def test_append_text(mock_auth_client, mock_httpx):
    """append_text sends batchUpdate with InsertTextRequest and endOfSegmentLocation."""
    response = MagicMock()
    response.json.return_value = {"replies": []}
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    append_text("doc-123", "More text here")

    call_args = mock_httpx.post.call_args
    url = call_args[0][0]
    assert "doc-123:batchUpdate" in url
    json_data = call_args.kwargs.get("json") or call_args[1].get("json")
    requests = json_data["requests"]
    assert len(requests) == 1
    insert = requests[0]["insertText"]
    assert insert["text"] == "More text here"
    assert insert["endOfSegmentLocation"] == {}


def test_append_text_as_user(mock_auth_client, mock_httpx):
    """append_text(doc_id, text, as_user=...) threads as_user through."""
    response = MagicMock()
    response.json.return_value = {"replies": []}
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    append_text("doc-123", "text", as_user="test@example.com")

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
