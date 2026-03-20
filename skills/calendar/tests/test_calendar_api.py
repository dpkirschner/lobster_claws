"""Tests for Calendar API client module."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from claws_calendar.calendar import (
    date_to_rfc3339,
    format_event_detail,
    format_event_summary,
    get_access_token,
    get_event,
    handle_calendar_error,
    list_events,
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
def mock_httpx():
    """Patch httpx in calendar module."""
    with patch("claws_calendar.calendar.httpx") as mock:
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


# --- list_events ---


def test_list_events_default_params(mock_auth_client, mock_httpx, sample_timed_event):
    """list_events with no args uses default params and returns formatted events."""
    response = MagicMock()
    response.json.return_value = {"items": [sample_timed_event]}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

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
    call_kwargs = mock_httpx.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert params["singleEvents"] == "true"
    assert params["orderBy"] == "startTime"
    assert params["maxResults"] == 25
    assert "timeMin" not in params
    assert "timeMax" not in params


def test_list_events_custom_time_range(mock_auth_client, mock_httpx):
    """list_events passes timeMin/timeMax when provided."""
    response = MagicMock()
    response.json.return_value = {"items": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    list_events(time_min="2026-03-20T00:00:00Z", time_max="2026-03-21T00:00:00Z")

    call_kwargs = mock_httpx.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert params["timeMin"] == "2026-03-20T00:00:00Z"
    assert params["timeMax"] == "2026-03-21T00:00:00Z"


def test_list_events_custom_max_results(mock_auth_client, mock_httpx):
    """list_events passes custom maxResults."""
    response = MagicMock()
    response.json.return_value = {"items": []}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    list_events(max_results=10)

    call_kwargs = mock_httpx.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
    assert params["maxResults"] == 10


def test_list_events_empty(mock_auth_client, mock_httpx):
    """list_events returns empty list when no items."""
    response = MagicMock()
    response.json.return_value = {}
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

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


def test_get_event(mock_auth_client, mock_httpx, sample_timed_event):
    """get_event calls API with event ID and returns full detail."""
    response = MagicMock()
    response.json.return_value = sample_timed_event
    response.raise_for_status = MagicMock()
    mock_httpx.get.return_value = response

    result = get_event("evt-001")

    assert result["id"] == "evt-001"
    assert result["description"] == "Daily sync"
    assert result["html_link"] == "https://calendar.google.com/event?eid=abc"

    # Verify correct URL path
    call_args = mock_httpx.get.call_args
    url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
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
