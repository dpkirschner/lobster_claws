"""Tests for Calendar API client module."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from claws_calendar.calendar import (
    _calendar_delete,
    _calendar_post,
    _calendar_put,
    create_event,
    date_to_rfc3339,
    delete_event,
    format_event_detail,
    format_event_summary,
    get_access_token,
    get_event,
    handle_calendar_error,
    list_events,
    update_event,
)

# --- fixtures ---


@pytest.fixture
def mock_auth_client():
    """Patch ClawsClient in calendar module to return a test token."""
    with patch("claws_calendar.calendar.ClawsClient") as mock_cls:
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
    """Patch google_request in calendar module."""
    with patch("claws_calendar.calendar.google_request") as mock:
        yield mock


@pytest.fixture
def sample_timed_event():
    """Calendar API event with dateTime (timed event)."""
    return {
        "id": "evt-001",
        "summary": "Team standup",
        "start": {"dateTime": "2026-03-20T10:00:00-07:00"},
        "end": {"dateTime": "2026-03-20T11:00:00-07:00"},
        "location": "Room A",
        "description": "Daily sync",
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=abc",
        "organizer": {"email": "boss@example.com"},
        "attendees": [
            {
                "email": "alice@example.com",
                "responseStatus": "accepted",
                "displayName": "Alice",
            }
        ],
        "created": "2026-03-01T00:00:00Z",
        "updated": "2026-03-19T12:00:00Z",
    }


@pytest.fixture
def sample_allday_event():
    """Calendar API event with date (all-day event)."""
    return {
        "id": "evt-002",
        "summary": "Company holiday",
        "start": {"date": "2026-03-20"},
        "end": {"date": "2026-03-21"},
    }


# --- get_access_token ---


def test_get_access_token(mock_auth_client):
    """get_access_token returns the token string from auth server."""
    token = get_access_token()
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token", {"scopes": ["https://www.googleapis.com/auth/calendar"]}
    )


def test_get_access_token_with_subject(mock_auth_client):
    """get_access_token(as_user=...) includes subject in auth server POST body."""
    token = get_access_token(as_user="bob@example.com")
    assert token == "test-token"
    mock_auth_client.post_json.assert_called_once_with(
        "/token",
        {"scopes": ["https://www.googleapis.com/auth/calendar"], "subject": "bob@example.com"},
    )


def test_get_access_token_without_subject(mock_auth_client):
    """get_access_token() without as_user does NOT include subject in body."""
    token = get_access_token()
    assert token == "test-token"
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert "subject" not in body


def test_list_events_passes_subject(mock_auth_client, mock_google_request):
    """list_events(as_user=...) threads as_user through to get_access_token."""
    mock_google_request.return_value = {"items": []}

    list_events(as_user="bob@example.com")

    # The token_fn should call get_access_token with the subject when invoked
    token_fn = mock_google_request.call_args[0][2]
    token_fn()  # trigger the lambda
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "bob@example.com"


def test_get_event_passes_subject(mock_auth_client, mock_google_request, sample_timed_event):
    """get_event(event_id, as_user=...) threads as_user through."""
    mock_google_request.return_value = sample_timed_event

    get_event("evt-001", as_user="bob@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "bob@example.com"


def test_create_event_passes_subject(mock_auth_client, mock_google_request, sample_timed_event):
    """create_event(..., as_user=...) threads as_user through."""
    mock_google_request.return_value = sample_timed_event

    create_event("Test", "2026-03-20T10:00:00Z", "2026-03-20T11:00:00Z", as_user="bob@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "bob@example.com"


def test_update_event_passes_subject(mock_auth_client, mock_google_request, sample_timed_event):
    """update_event(event_id, as_user=...) threads as_user through."""
    mock_google_request.return_value = sample_timed_event

    update_event("evt-001", title="New", as_user="bob@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "bob@example.com"


def test_delete_event_passes_subject(mock_auth_client, mock_google_request):
    """delete_event(event_id, as_user=...) threads as_user through."""
    mock_google_request.return_value = MagicMock()

    delete_event("evt-001", as_user="bob@example.com")

    token_fn = mock_google_request.call_args[0][2]
    token_fn()
    call_args = mock_auth_client.post_json.call_args
    body = call_args[0][1]
    assert body["subject"] == "bob@example.com"


# --- list_events ---


def test_list_events_default_params(mock_auth_client, mock_google_request, sample_timed_event):
    """list_events with no args uses default params and returns formatted events."""
    mock_google_request.return_value = {"items": [sample_timed_event]}

    events = list_events()

    assert len(events) == 1
    evt = events[0]
    assert evt["id"] == "evt-001"
    assert evt["summary"] == "Team standup"
    assert evt["start"] == "2026-03-20T10:00:00-07:00"
    assert evt["end"] == "2026-03-20T11:00:00-07:00"
    assert evt["location"] == "Room A"
    assert evt["all_day"] is False

    # Verify API params
    call_kwargs = mock_google_request.call_args
    params = call_kwargs.kwargs.get("params")
    assert params["singleEvents"] == "true"
    assert params["orderBy"] == "startTime"
    assert params["maxResults"] == 25
    assert "timeMin" not in params
    assert "timeMax" not in params


def test_list_events_custom_time_range(mock_auth_client, mock_google_request):
    """list_events passes timeMin/timeMax when provided."""
    mock_google_request.return_value = {"items": []}

    list_events(time_min="2026-03-20T00:00:00Z", time_max="2026-03-21T00:00:00Z")

    call_kwargs = mock_google_request.call_args
    params = call_kwargs.kwargs.get("params")
    assert params["timeMin"] == "2026-03-20T00:00:00Z"
    assert params["timeMax"] == "2026-03-21T00:00:00Z"


def test_list_events_custom_max_results(mock_auth_client, mock_google_request):
    """list_events passes custom maxResults."""
    mock_google_request.return_value = {"items": []}

    list_events(max_results=10)

    call_kwargs = mock_google_request.call_args
    params = call_kwargs.kwargs.get("params")
    assert params["maxResults"] == 10


def test_list_events_empty(mock_auth_client, mock_google_request):
    """list_events returns empty list when no items."""
    mock_google_request.return_value = {}

    events = list_events()
    assert events == []


# --- format_event_summary ---


def test_format_event_summary_timed(sample_timed_event):
    """format_event_summary returns correct fields for timed event."""
    result = format_event_summary(sample_timed_event)
    assert result["id"] == "evt-001"
    assert result["summary"] == "Team standup"
    assert result["start"] == "2026-03-20T10:00:00-07:00"
    assert result["end"] == "2026-03-20T11:00:00-07:00"
    assert result["location"] == "Room A"
    assert result["all_day"] is False


def test_format_event_summary_allday(sample_allday_event):
    """format_event_summary handles all-day events with date fields."""
    result = format_event_summary(sample_allday_event)
    assert result["id"] == "evt-002"
    assert result["summary"] == "Company holiday"
    assert result["start"] == "2026-03-20"
    assert result["end"] == "2026-03-21"
    assert result["all_day"] is True
    assert result["location"] is None


def test_format_event_summary_no_title():
    """format_event_summary defaults to '(No title)' when summary missing."""
    event = {
        "id": "evt-003",
        "start": {"dateTime": "2026-03-20T10:00:00-07:00"},
        "end": {"dateTime": "2026-03-20T11:00:00-07:00"},
    }
    result = format_event_summary(event)
    assert result["summary"] == "(No title)"


def test_format_event_summary_no_location():
    """format_event_summary returns None for missing location."""
    event = {
        "id": "evt-004",
        "summary": "Meeting",
        "start": {"dateTime": "2026-03-20T10:00:00-07:00"},
        "end": {"dateTime": "2026-03-20T11:00:00-07:00"},
    }
    result = format_event_summary(event)
    assert result["location"] is None


# --- format_event_detail ---


def test_format_event_detail_full(sample_timed_event):
    """format_event_detail returns all fields including attendees."""
    result = format_event_detail(sample_timed_event)
    # Summary fields
    assert result["id"] == "evt-001"
    assert result["summary"] == "Team standup"
    assert result["all_day"] is False
    # Detail fields
    assert result["description"] == "Daily sync"
    assert result["status"] == "confirmed"
    assert result["html_link"] == "https://calendar.google.com/event?eid=abc"
    assert result["organizer"] == "boss@example.com"
    assert result["created"] == "2026-03-01T00:00:00Z"
    assert result["updated"] == "2026-03-19T12:00:00Z"
    # Attendees
    assert len(result["attendees"]) == 1
    att = result["attendees"][0]
    assert att["email"] == "alice@example.com"
    assert att["response_status"] == "accepted"
    assert att["display_name"] == "Alice"


def test_format_event_detail_empty_attendees(sample_allday_event):
    """format_event_detail returns empty attendees list when none present."""
    result = format_event_detail(sample_allday_event)
    assert result["attendees"] == []
    assert result["description"] is None
    assert result["organizer"] is None


# --- get_event ---


def test_get_event(mock_auth_client, mock_google_request, sample_timed_event):
    """get_event calls API with event ID and returns full detail."""
    mock_google_request.return_value = sample_timed_event

    result = get_event("evt-001")

    assert result["id"] == "evt-001"
    assert result["description"] == "Daily sync"
    assert result["html_link"] == "https://calendar.google.com/event?eid=abc"

    # Verify correct URL path
    call_args = mock_google_request.call_args
    url = call_args[0][1]
    assert "events/evt-001" in url


# --- handle_calendar_error ---


def test_handle_calendar_error_401():
    """401 errors call crash() with auth message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {"code": 401, "message": "Invalid Credentials"}
    }
    error = real_httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)

    with patch("claws_calendar.calendar.crash") as mock_crash:
        handle_calendar_error(error)
        mock_crash.assert_called_once()
        assert "auth" in mock_crash.call_args[0][0].lower()


def test_handle_calendar_error_403():
    """403 errors call fail() with access denied."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {"code": 403, "message": "Forbidden"}
    }
    error = real_httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)

    with patch("claws_calendar.calendar.fail") as mock_fail:
        handle_calendar_error(error)
        mock_fail.assert_called_once()
        assert "access denied" in mock_fail.call_args[0][0].lower()


def test_handle_calendar_error_404():
    """404 errors call fail() with not found."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {
        "error": {"code": 404, "message": "Not Found"}
    }
    error = real_httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)

    with patch("claws_calendar.calendar.fail") as mock_fail:
        handle_calendar_error(error)
        mock_fail.assert_called_once()
        assert "not found" in mock_fail.call_args[0][0].lower()


def test_handle_calendar_error_429():
    """429 errors call fail() with rate limit message."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {
        "error": {"code": 429, "message": "Rate Limit Exceeded"}
    }
    error = real_httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)

    with patch("claws_calendar.calendar.fail") as mock_fail:
        handle_calendar_error(error)
        mock_fail.assert_called_once()
        assert "rate limit" in mock_fail.call_args[0][0].lower()


def test_handle_calendar_error_500():
    """500 errors call crash() with generic error."""
    import httpx as real_httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        "error": {"code": 500, "message": "Internal Server Error"}
    }
    error = real_httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)

    with patch("claws_calendar.calendar.crash") as mock_crash:
        handle_calendar_error(error)
        mock_crash.assert_called_once()


# --- date_to_rfc3339 ---


def test_date_to_rfc3339_start_of_day():
    """date_to_rfc3339 converts date to start-of-day ISO 8601 timestamp."""
    result = date_to_rfc3339(date(2026, 3, 20))
    assert result.startswith("2026-03-20T00:00:00")
    # Should have timezone offset (not naive)
    assert "+" in result or result.endswith("Z") or "-" in result[19:]


def test_date_to_rfc3339_end_of_day():
    """date_to_rfc3339 with end_of_day=True sets time to 23:59:59."""
    result = date_to_rfc3339(date(2026, 3, 20), end_of_day=True)
    assert result.startswith("2026-03-20T23:59:59")
    # Should have timezone offset
    assert "+" in result or result.endswith("Z") or "-" in result[19:]


# --- _calendar_post ---


def test_calendar_post(mock_google_request):
    """_calendar_post calls google_request with correct args and returns result."""
    mock_google_request.return_value = {"id": "new-evt"}
    token_fn = lambda: "test-token"

    result = _calendar_post("/events", token_fn, {"summary": "Test"})

    assert result == {"id": "new-evt"}
    mock_google_request.assert_called_once_with(
        "POST",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        token_fn,
        json={"summary": "Test"},
    )


# --- _calendar_put ---


def test_calendar_put(mock_google_request):
    """_calendar_put calls google_request with correct args and returns result."""
    mock_google_request.return_value = {"id": "evt-001", "summary": "Updated"}
    token_fn = lambda: "test-token"

    result = _calendar_put("/events/evt-001", token_fn, {"summary": "Updated"})

    assert result == {"id": "evt-001", "summary": "Updated"}
    mock_google_request.assert_called_once_with(
        "PUT",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events/evt-001",
        token_fn,
        json={"summary": "Updated"},
    )


# --- _calendar_delete ---


def test_calendar_delete(mock_google_request):
    """_calendar_delete calls google_request with raw=True and returns None."""
    mock_google_request.return_value = MagicMock()
    token_fn = lambda: "test-token"

    result = _calendar_delete("/events/evt-001", token_fn)

    assert result is None
    mock_google_request.assert_called_once_with(
        "DELETE",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events/evt-001",
        token_fn,
        raw=True,
    )


# --- create_event ---


def test_create_event_minimal(mock_auth_client, mock_google_request, sample_timed_event):
    """create_event with only title+start+end builds correct minimal body."""
    mock_google_request.return_value = sample_timed_event

    result = create_event(
        "Team standup",
        "2026-03-20T10:00:00-07:00",
        "2026-03-20T11:00:00-07:00",
    )

    assert result["id"] == "evt-001"
    assert result["summary"] == "Team standup"

    call_kwargs = mock_google_request.call_args
    body = call_kwargs.kwargs.get("json")
    assert body["summary"] == "Team standup"
    assert body["start"] == {"dateTime": "2026-03-20T10:00:00-07:00"}
    assert body["end"] == {"dateTime": "2026-03-20T11:00:00-07:00"}
    assert "location" not in body
    assert "description" not in body
    assert "attendees" not in body


def test_create_event_full(mock_auth_client, mock_google_request, sample_timed_event):
    """create_event with all optional fields includes them in body."""
    mock_google_request.return_value = sample_timed_event

    result = create_event(
        "Team standup",
        "2026-03-20T10:00:00-07:00",
        "2026-03-20T11:00:00-07:00",
        location="Room A",
        description="Daily sync",
        attendees=["alice@example.com", "bob@example.com"],
    )

    assert result["id"] == "evt-001"

    call_kwargs = mock_google_request.call_args
    body = call_kwargs.kwargs.get("json")
    assert body["location"] == "Room A"
    assert body["description"] == "Daily sync"
    assert body["attendees"] == [
        {"email": "alice@example.com"},
        {"email": "bob@example.com"},
    ]


def test_create_event_all_day(mock_auth_client, mock_google_request, sample_timed_event):
    """create_event with all_day=True uses date instead of dateTime."""
    mock_google_request.return_value = sample_timed_event

    create_event(
        "Company holiday",
        "2026-03-20",
        "2026-03-21",
        all_day=True,
    )

    call_kwargs = mock_google_request.call_args
    body = call_kwargs.kwargs.get("json")
    assert body["start"] == {"date": "2026-03-20"}
    assert body["end"] == {"date": "2026-03-21"}


def test_create_event_calls_auth(mock_auth_client, mock_google_request, sample_timed_event):
    """create_event passes a token_fn that calls get_access_token."""
    mock_google_request.return_value = sample_timed_event

    create_event("Test", "2026-03-20T10:00:00Z", "2026-03-20T11:00:00Z")

    # Verify google_request was called with a callable token_fn
    call_args = mock_google_request.call_args
    token_fn = call_args[0][2]
    assert callable(token_fn)
    # Invoke the token_fn to verify it calls auth
    token_fn()
    mock_auth_client.post_json.assert_called_once()


# --- update_event ---


def test_update_event(mock_auth_client, mock_google_request, sample_timed_event):
    """update_event calls PUT with all provided fields."""
    mock_google_request.return_value = sample_timed_event

    result = update_event(
        "evt-001",
        title="New title",
        start="2026-03-20T14:00:00-07:00",
        end="2026-03-20T15:00:00-07:00",
        location="Room B",
        description="Updated sync",
        attendees=["charlie@example.com"],
    )

    assert result["id"] == "evt-001"

    call_args = mock_google_request.call_args
    url = call_args[0][1]
    assert "events/evt-001" in url

    body = call_args.kwargs.get("json")
    assert body["summary"] == "New title"
    assert body["start"] == {"dateTime": "2026-03-20T14:00:00-07:00"}
    assert body["end"] == {"dateTime": "2026-03-20T15:00:00-07:00"}
    assert body["location"] == "Room B"
    assert body["description"] == "Updated sync"
    assert body["attendees"] == [{"email": "charlie@example.com"}]


def test_update_event_partial(mock_auth_client, mock_google_request, sample_timed_event):
    """update_event with only title sends body with only summary."""
    mock_google_request.return_value = sample_timed_event

    update_event("evt-001", title="New title")

    call_args = mock_google_request.call_args
    body = call_args.kwargs.get("json")
    assert body == {"summary": "New title"}


def test_update_event_calls_auth(mock_auth_client, mock_google_request, sample_timed_event):
    """update_event passes a token_fn that calls get_access_token."""
    mock_google_request.return_value = sample_timed_event

    update_event("evt-001", title="Test")

    call_args = mock_google_request.call_args
    token_fn = call_args[0][2]
    assert callable(token_fn)
    token_fn()
    mock_auth_client.post_json.assert_called_once()


# --- delete_event ---


def test_delete_event(mock_auth_client, mock_google_request):
    """delete_event calls DELETE and returns confirmation dict."""
    mock_google_request.return_value = MagicMock()

    result = delete_event("evt-001")

    assert result == {"deleted": True, "event_id": "evt-001"}

    call_args = mock_google_request.call_args
    url = call_args[0][1]
    assert "events/evt-001" in url


def test_delete_event_calls_auth(mock_auth_client, mock_google_request):
    """delete_event passes a token_fn that calls get_access_token."""
    mock_google_request.return_value = MagicMock()

    delete_event("evt-001")

    call_args = mock_google_request.call_args
    token_fn = call_args[0][2]
    assert callable(token_fn)
    token_fn()
    mock_auth_client.post_json.assert_called_once()
