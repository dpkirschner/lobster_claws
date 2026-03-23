"""Tests for Contacts API client module."""

from unittest.mock import MagicMock, patch

import pytest
from claws_contacts.contacts import (
    create_contact,
    delete_contact,
    get_access_token,
    get_contact,
    handle_contacts_error,
    list_contacts,
    search_contacts,
    update_contact,
)

# --- fixtures ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in contacts module to return a test token."""
    with patch("claws_contacts.contacts.ClawsClient") as mock_cls:
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
    """Patch httpx in contacts module."""
    with patch("claws_contacts.contacts.httpx") as mock:
        yield mock


# --- get_access_token ---


def test_get_access_token(mock_auth_client):
    """get_access_token returns the token string from auth server."""
    token = get_access_token()
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token", {"scopes": ["https://www.googleapis.com/auth/contacts"]}
    )


def test_get_access_token_with_subject(mock_auth_client):
    """get_access_token(as_user=...) includes subject in auth server POST body."""
    token = get_access_token(as_user="alice@example.com")
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {"scopes": ["https://www.googleapis.com/auth/contacts"], "subject": "alice@example.com"},
    )


def test_get_access_token_without_subject(mock_auth_client):
    """get_access_token() without as_user does NOT include subject in body."""
    token = get_access_token()
    assert token == "test-token"
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "subject" not in body


# --- list_contacts ---


def test_list_contacts(mock_auth_client, mock_httpx):
    """list_contacts returns connections from response."""
    response = MagicMock()
    response.json.return_value = {
        "connections": [
            {"resourceName": "people/c1", "names": [{"displayName": "Alice"}]},
            {"resourceName": "people/c2", "names": [{"displayName": "Bob"}]},
        ],
        "totalPeople": 2,
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    contacts = list_contacts(max_results=100)
    assert len(contacts) == 2
    assert contacts[0]["resourceName"] == "people/c1"

    # Verify correct URL and params
    call_args = mock_httpx.get.call_args
    url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url")
    assert "people/me/connections" in url
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["personFields"] == "names,emailAddresses,phoneNumbers"
    assert params["pageSize"] == 100


def test_list_contacts_empty(mock_auth_client, mock_httpx):
    """list_contacts returns empty list when no connections."""
    response = MagicMock()
    response.json.return_value = {}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    contacts = list_contacts()
    assert contacts == []


def test_list_contacts_passes_subject(mock_auth_client, mock_httpx):
    """list_contacts(as_user=...) threads as_user through to get_access_token."""
    response = MagicMock()
    response.json.return_value = {"connections": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    list_contacts(as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- search_contacts ---


def test_search_contacts(mock_auth_client, mock_httpx):
    """search_contacts passes query parameter and returns results."""
    response = MagicMock()
    response.json.return_value = {
        "results": [
            {"person": {"resourceName": "people/c1", "names": [{"displayName": "Alice"}]}}
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    results = search_contacts(query="alice")
    assert len(results) == 1

    # Verify query param
    call_args = mock_httpx.get.call_args
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["query"] == "alice"
    assert params["readMask"] == "names,emailAddresses,phoneNumbers"


def test_search_contacts_passes_subject(mock_auth_client, mock_httpx):
    """search_contacts(as_user=...) threads as_user through."""
    response = MagicMock()
    response.json.return_value = {"results": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    search_contacts(query="alice", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- get_contact ---


def test_get_contact(mock_auth_client, mock_httpx):
    """get_contact calls correct URL with resource_name."""
    response = MagicMock()
    response.json.return_value = {
        "resourceName": "people/c123",
        "names": [{"displayName": "Alice"}],
    }
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    contact = get_contact(resource_name="people/c123")
    assert contact["resourceName"] == "people/c123"

    # Verify URL contains the resource name
    call_args = mock_httpx.get.call_args
    url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url")
    assert "people/c123" in url
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["personFields"] == "names,emailAddresses,phoneNumbers"


def test_get_contact_passes_subject(mock_auth_client, mock_httpx):
    """get_contact(as_user=...) threads as_user through."""
    response = MagicMock()
    response.json.return_value = {"resourceName": "people/c123"}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    get_contact(resource_name="people/c123", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- create_contact ---


def test_create_contact_all_fields(mock_auth_client, mock_httpx):
    """create_contact with all fields sends names, email, phone."""
    response = MagicMock()
    response.json.return_value = {
        "resourceName": "people/c999",
        "names": [{"givenName": "Alice"}],
        "emailAddresses": [{"value": "a@x.com"}],
        "phoneNumbers": [{"value": "555-1234"}],
    }
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    contact = create_contact(name="Alice", email="a@x.com", phone="555-1234")
    assert contact["resourceName"] == "people/c999"

    # Verify body
    call_args = mock_httpx.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    assert body["names"] == [{"givenName": "Alice"}]
    assert body["emailAddresses"] == [{"value": "a@x.com"}]
    assert body["phoneNumbers"] == [{"value": "555-1234"}]


def test_create_contact_name_only(mock_auth_client, mock_httpx):
    """create_contact with name only works without email/phone."""
    response = MagicMock()
    response.json.return_value = {
        "resourceName": "people/c999",
        "names": [{"givenName": "Alice"}],
    }
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    contact = create_contact(name="Alice")
    assert contact["resourceName"] == "people/c999"

    # Verify body has no email or phone
    call_args = mock_httpx.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    assert body["names"] == [{"givenName": "Alice"}]
    assert "emailAddresses" not in body
    assert "phoneNumbers" not in body


def test_create_contact_passes_subject(mock_auth_client, mock_httpx):
    """create_contact(as_user=...) threads as_user through."""
    response = MagicMock()
    response.json.return_value = {"resourceName": "people/c999"}
    response.raise_for_status = MagicMock()
    mock_httpx.post.return_value = response

    create_contact(name="Alice", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- update_contact ---


def test_update_contact(mock_auth_client, mock_httpx):
    """update_contact fetches etag first, then patches with etag included."""
    # First call: GET to fetch etag
    get_response = MagicMock()
    get_response.json.return_value = {
        "resourceName": "people/c123",
        "etag": "abc123etag",
        "metadata": {"sources": [{"etag": "abc123etag"}]},
        "names": [{"givenName": "OldName"}],
    }
    get_response.raise_for_status = MagicMock()

    # Second call: PATCH with etag
    patch_response = MagicMock()
    patch_response.json.return_value = {
        "resourceName": "people/c123",
        "names": [{"givenName": "NewName"}],
    }
    patch_response.raise_for_status = MagicMock()

    mock_httpx.get.return_value = get_response
    mock_httpx.patch.return_value = patch_response

    result = update_contact(resource_name="people/c123", name="NewName")
    assert result["names"][0]["givenName"] == "NewName"

    # Verify GET was called first
    mock_httpx.get.assert_called_once()

    # Verify PATCH includes etag
    patch_call = mock_httpx.patch.call_args
    body = patch_call.kwargs.get("json") or patch_call[1].get("json")
    assert body["etag"] == "abc123etag"
    assert body["names"] == [{"givenName": "NewName"}]


def test_update_contact_passes_subject(mock_auth_client, mock_httpx):
    """update_contact(as_user=...) threads as_user through."""
    get_response = MagicMock()
    get_response.json.return_value = {
        "resourceName": "people/c123",
        "etag": "abc123etag",
        "metadata": {"sources": [{"etag": "abc123etag"}]},
    }
    get_response.raise_for_status = MagicMock()

    patch_response = MagicMock()
    patch_response.json.return_value = {"resourceName": "people/c123"}
    patch_response.raise_for_status = MagicMock()

    mock_httpx.get.return_value = get_response
    mock_httpx.patch.return_value = patch_response

    update_contact(resource_name="people/c123", name="NewName", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- delete_contact ---


def test_delete_contact(mock_auth_client, mock_httpx):
    """delete_contact calls correct URL."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    mock_httpx.delete.return_value = response

    delete_contact(resource_name="people/c123")

    # Verify URL contains the resource name and deleteContact
    call_args = mock_httpx.delete.call_args
    url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url")
    assert "people/c123:deleteContact" in url


def test_delete_contact_passes_subject(mock_auth_client, mock_httpx):
    """delete_contact(as_user=...) threads as_user through."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    mock_httpx.delete.return_value = response

    delete_contact(resource_name="people/c123", as_user="test@example.com")

    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "test@example.com"


# --- handle_contacts_error ---


def test_handle_contacts_error_401():
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

    with patch("claws_contacts.contacts.crash") as mock_crash:
        handle_contacts_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_contacts_error_403():
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

    with patch("claws_contacts.contacts.fail") as mock_fail:
        handle_contacts_error(error)
        mock_fail.assert_called_once()


def test_handle_contacts_error_404():
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

    with patch("claws_contacts.contacts.fail") as mock_fail:
        handle_contacts_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_contacts_error_429():
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

    with patch("claws_contacts.contacts.fail") as mock_fail:
        handle_contacts_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()


def test_handle_contacts_error_500():
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

    with patch("claws_contacts.contacts.crash") as mock_crash:
        handle_contacts_error(error)
        mock_crash.assert_called_once()
