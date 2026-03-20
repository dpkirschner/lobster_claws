"""Google Calendar API client module.

Handles token acquisition, event listing, event details,
date conversion, event formatting, and error handling.
"""

from datetime import date, datetime, time

import httpx
from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary"


def get_access_token() -> str:
    """Get Calendar access token from auth server."""
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    resp = client.post_json("/token", {"scopes": [CALENDAR_SCOPE]})
    return resp["access_token"]


def _calendar_get(path: str, token: str, params: dict | None = None) -> dict:
    """GET request to Google Calendar API."""
    resp = httpx.get(
        f"{CALENDAR_BASE}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def date_to_rfc3339(d: date, end_of_day: bool = False) -> str:
    """Convert a date to RFC 3339 timestamp with local timezone.

    Args:
        d: The date to convert.
        end_of_day: If True, set time to 23:59:59. Otherwise 00:00:00.

    Returns:
        ISO 8601 timestamp string with timezone offset.
    """
    local_tz = datetime.now().astimezone().tzinfo
    t = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    dt = datetime.combine(d, t, tzinfo=local_tz)
    return dt.isoformat()


def format_event_summary(event: dict) -> dict:
    """Format a Calendar API event into a summary dict.

    Handles both timed events (dateTime) and all-day events (date).
    """
    start = event.get("start", {})
    end = event.get("end", {})
    all_day = "date" in start

    return {
        "id": event["id"],
        "summary": event.get("summary", "(No title)"),
        "start": start.get("date") if all_day else start.get("dateTime"),
        "end": end.get("date") if all_day else end.get("dateTime"),
        "location": event.get("location", None),
        "all_day": all_day,
    }


def format_event_detail(event: dict) -> dict:
    """Format a Calendar API event into a full detail dict.

    Includes all summary fields plus description, status, html_link,
    organizer, attendees, created, and updated.
    """
    detail = format_event_summary(event)

    attendees_raw = event.get("attendees", [])
    attendees = [
        {
            "email": a["email"],
            "response_status": a.get("responseStatus", "needsAction"),
            "display_name": a.get("displayName"),
        }
        for a in attendees_raw
    ]

    organizer = event.get("organizer")
    organizer_email = organizer.get("email") if organizer else None

    detail.update(
        {
            "description": event.get("description", None),
            "status": event.get("status", None),
            "html_link": event.get("htmlLink", None),
            "organizer": organizer_email,
            "attendees": attendees,
            "created": event.get("created", None),
            "updated": event.get("updated", None),
        }
    )
    return detail


def list_events(
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 25,
) -> list[dict]:
    """List calendar events.

    Args:
        time_min: RFC 3339 lower bound for event start time.
        time_max: RFC 3339 upper bound for event start time.
        max_results: Maximum number of events to return (default 25).

    Returns:
        List of formatted event summary dicts.
    """
    token = get_access_token()
    params: dict = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min is not None:
        params["timeMin"] = time_min
    if time_max is not None:
        params["timeMax"] = time_max

    data = _calendar_get("/events", token, params=params)
    return [format_event_summary(e) for e in data.get("items", [])]


def get_event(event_id: str) -> dict:
    """Get full detail for a single calendar event.

    Args:
        event_id: The Calendar event ID.

    Returns:
        Full event detail dict.
    """
    token = get_access_token()
    data = _calendar_get(f"/events/{event_id}", token)
    return format_event_detail(data)


def handle_calendar_error(e: httpx.HTTPStatusError) -> None:
    """Translate Calendar API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Calendar authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Calendar access denied: {message}")
    elif status == 404:
        fail(f"Event not found: {message}")
    elif status == 429:
        fail("Calendar rate limit exceeded. Try again later.")
    else:
        crash(f"Calendar API error ({status}): {message}")
