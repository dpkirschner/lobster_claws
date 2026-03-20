# Phase 6: Calendar Read Operations - Research

**Researched:** 2026-03-19
**Domain:** Google Calendar API v3, Python CLI skill
**Confidence:** HIGH

## Summary

This phase adds a `claws calendar` skill with `list` and `get` subcommands. The implementation closely mirrors the existing Gmail skill (`claws-gmail`), following the same two-tier HTTP pattern: ClawsClient for auth token acquisition from the google-auth server on port 8301, then raw httpx calls to the Google Calendar API v3. The Calendar API endpoints are straightforward REST: `GET .../events` for listing with time-range filtering, `GET .../events/{eventId}` for single event retrieval.

The Gmail skill provides a near-complete structural template. The calendar module (`calendar.py`) will mirror `gmail.py` with token acquisition, API helpers, and error handling. The CLI (`cli.py`) will use argparse with subparsers for `list` and `get` commands. Date range filtering uses RFC 3339 timestamps via the `timeMin`/`timeMax` query parameters. All-day events use `date` instead of `dateTime` in start/end objects, which requires handling both formats.

**Primary recommendation:** Clone the Gmail skill structure verbatim, replacing Gmail-specific logic with Calendar API calls. Use `singleEvents=true` and `orderBy=startTime` for the list endpoint to get expanded recurring events in chronological order.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Date range interface:** `--today`, `--week`, `--from YYYY-MM-DD`, `--to YYYY-MM-DD` convenience flags. `--max` flag with default of 25.
- **Full calendar scope:** Use `https://www.googleapis.com/auth/calendar` (not `calendar.readonly`) so Phase 7 writes need zero scope changes.
- **Event output minimum fields:** id, title (summary), start/end times, location, description. Attendees optional for list, required for get.

### Claude's Discretion
- Default date range (today vs next 7 days)
- Event output fields for list vs get (list can be summary, get can be full)
- Time format in output (ISO 8601 vs human-readable)
- Timezone handling
- All-day event representation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAL-01 | User can list events for a date range (today, this week, custom range) | Calendar API `events.list` with `timeMin`/`timeMax` RFC 3339 params, `singleEvents=true`, `orderBy=startTime`. CLI flags `--today`, `--week`, `--from`, `--to`. |
| CAL-02 | User can get details for a specific event by ID | Calendar API `events.get` endpoint: `GET /calendars/primary/events/{eventId}`. Returns full Event resource. |
| CAL-06 | Calendar skill outputs structured JSON via stdout using claws_common.output | Use `result()` from `claws_common.output`. List wraps as `{"events": [...], "result_count": N}`. Get returns flat event dict. |
| CAL-07 | Calendar CLI registered as `claws calendar` via entry-point discovery | Entry point in pyproject.toml: `calendar = "claws_calendar.cli:main"` under `[project.entry-points."claws.skills"]`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | (already in workspace) | Direct HTTP calls to Calendar API | Project convention -- Gmail uses same pattern |
| claws-common | workspace | ClawsClient, output helpers | Project shared library |
| argparse | stdlib | CLI argument parsing | Project convention -- Gmail uses same |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime | stdlib | RFC 3339 timestamp generation for timeMin/timeMax | Converting --from/--to date strings to API params |
| zoneinfo | stdlib (3.9+) | Timezone handling for local time | Building timezone-aware RFC 3339 timestamps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw httpx | google-api-python-client | Adds heavy dependency; project uses thin httpx pattern for all Google APIs |
| zoneinfo | pytz | zoneinfo is stdlib since 3.9, no extra dependency needed |

**Installation:**
```bash
# No new packages needed -- httpx and claws-common already in workspace
# Only need to add claws-calendar as workspace member
uv sync
```

## Architecture Patterns

### Recommended Project Structure
```
skills/
└── calendar/
    ├── pyproject.toml           # claws-calendar package definition
    ├── src/
    │   └── claws_calendar/
    │       ├── __init__.py
    │       ├── calendar.py      # API module: token, list_events, get_event, error handler
    │       └── cli.py           # argparse CLI: list, get subcommands
    └── tests/
        ├── __init__.py
        ├── test_calendar_api.py # Tests for calendar.py (mock httpx)
        └── test_calendar_cli.py # Tests for cli.py (mock API functions)
```

### Pattern 1: Two-Tier HTTP (Auth + API)
**What:** ClawsClient talks to local auth server for tokens, then raw httpx calls Google Calendar API with Bearer token.
**When to use:** All Google API skills.
**Example:**
```python
# Source: Gmail skill pattern (skills/gmail/src/claws_gmail/gmail.py)
from claws_common.client import ClawsClient

AUTH_PORT = 8301
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary"

def get_access_token() -> str:
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    resp = client.post_json("/token", {"scopes": [CALENDAR_SCOPE]})
    return resp["access_token"]

def _calendar_get(path: str, token: str, params: dict | None = None) -> dict:
    resp = httpx.get(
        f"{CALENDAR_BASE}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()
```

### Pattern 2: Date Range to RFC 3339
**What:** Convert user-friendly date flags to RFC 3339 timestamps required by Calendar API.
**When to use:** `list` subcommand date filtering.
**Example:**
```python
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

def date_to_rfc3339(d: date, end_of_day: bool = False) -> str:
    """Convert a date to RFC 3339 timestamp string.

    Calendar API requires timezone offset. Uses local timezone.
    end_of_day=True sets time to 23:59:59 for timeMax bounds.
    """
    local_tz = ZoneInfo("America/Los_Angeles")  # or detect from system
    if end_of_day:
        dt = datetime.combine(d, time(23, 59, 59), tzinfo=local_tz)
    else:
        dt = datetime.combine(d, time(0, 0, 0), tzinfo=local_tz)
    return dt.isoformat()
```

### Pattern 3: Event Formatting (List vs Get)
**What:** List returns compact event summaries, get returns full detail.
**When to use:** Shaping API responses for output.
**Example:**
```python
def format_event_summary(event: dict) -> dict:
    """Compact event for list output."""
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event["id"],
        "summary": event.get("summary", "(No title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "location": event.get("location"),
        "all_day": "date" in start,
    }

def format_event_detail(event: dict) -> dict:
    """Full event for get output."""
    detail = format_event_summary(event)
    detail.update({
        "description": event.get("description"),
        "status": event.get("status"),
        "html_link": event.get("htmlLink"),
        "organizer": event.get("organizer", {}).get("email"),
        "attendees": [
            {
                "email": a["email"],
                "response_status": a.get("responseStatus"),
                "display_name": a.get("displayName"),
            }
            for a in event.get("attendees", [])
        ],
        "created": event.get("created"),
        "updated": event.get("updated"),
    })
    return detail
```

### Anti-Patterns to Avoid
- **Using google-api-python-client:** Adds 10+ transitive dependencies. Project convention is thin httpx calls. The Gmail skill already proves this pattern works.
- **Hardcoding timezone:** Use `datetime.now().astimezone().tzinfo` or accept a `--timezone` flag. The Calendar API `timeZone` param can also be passed to get responses in a specific timezone.
- **Conftest.py in skill test directories:** Gmail had an importlib collision with conftest.py. Keep fixtures inline in test files (as Gmail now does).
- **Naming test files generically:** Use `test_calendar_api.py` and `test_calendar_cli.py` to avoid name collisions across workspace test discovery.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 3339 timestamps | String formatting | `datetime.isoformat()` | Handles timezone offsets correctly |
| Timezone detection | Manual UTC offset calc | `zoneinfo.ZoneInfo` + `datetime.now().astimezone()` | Stdlib, handles DST |
| HTTP auth headers | Custom auth middleware | Same Bearer token pattern as Gmail | Proven in production |
| JSON output formatting | Custom print/json.dumps | `claws_common.output.result()` | Handles flush, consistent format |

## Common Pitfalls

### Pitfall 1: All-Day Events Have `date` Not `dateTime`
**What goes wrong:** Code assumes `event["start"]["dateTime"]` always exists, crashes on all-day events.
**Why it happens:** All-day events use `{"date": "2026-03-20"}` instead of `{"dateTime": "2026-03-20T10:00:00-07:00"}`.
**How to avoid:** Always check `start.get("dateTime") or start.get("date")`. Include an `all_day` boolean field in output.
**Warning signs:** KeyError on event["start"]["dateTime"] in tests or production.

### Pitfall 2: Recurring Events Returned as Single Entry
**What goes wrong:** A weekly meeting shows once instead of multiple instances within the date range.
**Why it happens:** Without `singleEvents=true`, the API returns the recurring event definition, not individual instances.
**How to avoid:** Always pass `singleEvents=true` when listing events. This expands recurring events into individual instances and enables `orderBy=startTime`.
**Warning signs:** Fewer events than expected, events with `recurrence` field instead of individual start/end times.

### Pitfall 3: timeMin/timeMax Are Exclusive Bounds
**What goes wrong:** Events exactly at the boundary time are missing.
**Why it happens:** `timeMin` filters by event end time (exclusive), `timeMax` filters by event start time (exclusive). An event ending exactly at timeMin is excluded.
**How to avoid:** For "today" queries, set timeMin to start of day and timeMax to start of next day. This correctly captures all events overlapping with the day.
**Warning signs:** Events at midnight boundaries missing from results.

### Pitfall 4: Test File Name Collision
**What goes wrong:** pytest discovers `tests/test_cli.py` from multiple skill packages, causing importlib conflicts.
**Why it happens:** `--import-mode=importlib` with generic test file names across workspace members.
**How to avoid:** Use unique prefixed names: `test_calendar_api.py`, `test_calendar_cli.py`. Gmail learned this the hard way.
**Warning signs:** `ModuleNotFoundError` or wrong module loaded during test runs.

### Pitfall 5: Missing `singleEvents` Breaks `orderBy`
**What goes wrong:** API returns 400 error when `orderBy=startTime` is used.
**Why it happens:** `orderBy=startTime` requires `singleEvents=true`. Without it, the API rejects the combination.
**How to avoid:** Always pair them: `singleEvents=true&orderBy=startTime`.
**Warning signs:** HTTP 400 from Calendar API with message about orderBy.

## Code Examples

### Calendar API: List Events
```python
# Source: Google Calendar API v3 reference
# GET https://www.googleapis.com/calendar/v3/calendars/primary/events
def list_events(
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 25,
) -> list[dict]:
    token = get_access_token()
    params = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max

    data = _calendar_get("/events", token, params=params)
    return [format_event_summary(e) for e in data.get("items", [])]
```

### Calendar API: Get Single Event
```python
# Source: Google Calendar API v3 reference
# GET https://www.googleapis.com/calendar/v3/calendars/primary/events/{eventId}
def get_event(event_id: str) -> dict:
    token = get_access_token()
    data = _calendar_get(f"/events/{event_id}", token)
    return format_event_detail(data)
```

### CLI: Subcommand Routing
```python
# Source: Gmail CLI pattern (skills/gmail/src/claws_gmail/cli.py)
def main():
    parser = argparse.ArgumentParser(
        prog="claws-calendar",
        description="Calendar skill for listing and viewing events",
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subs.add_parser("list", help="List calendar events")
    list_p.add_argument("--today", action="store_true", help="Show today's events")
    list_p.add_argument("--week", action="store_true", help="Show this week's events")
    list_p.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    list_p.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    list_p.add_argument("--max", type=int, default=25, help="Max events (default: 25)")

    # get
    get_p = subs.add_parser("get", help="Get event details by ID")
    get_p.add_argument("id", help="Event ID")

    args = parser.parse_args()
    # ... dispatch to API functions
```

### pyproject.toml
```toml
[project]
name = "claws-calendar"
version = "0.1.0"
description = "Calendar skill for Lobster Claws"
requires-python = ">=3.12"
dependencies = ["claws-common"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.entry-points."claws.skills"]
calendar = "claws_calendar.cli:main"

[tool.uv.sources]
claws-common = { workspace = true }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-api-python-client | Direct httpx REST calls | Project convention | No heavy client library dependency |
| pytz for timezones | zoneinfo (stdlib) | Python 3.9+ | No extra dependency |

## Open Questions

1. **Default date range when no flags provided**
   - What we know: User left this as Claude's discretion. Options are "today" or "next 7 days".
   - Recommendation: Default to **next 7 days**. An agent asking "what's happening" benefits more from a week view. `--today` is available for narrowing. This matches how most calendar UIs default to a week view.

2. **Timezone handling**
   - What we know: Calendar API accepts `timeZone` param and returns times in calendar's timezone by default. RFC 3339 timestamps from `--from`/`--to` need a timezone.
   - Recommendation: Use the system's local timezone (`datetime.now().astimezone().tzinfo`) for building `timeMin`/`timeMax`. Output times in whatever format the API returns (ISO 8601 with offset). This keeps things simple and correct.

3. **Time format in output**
   - What we know: User left as discretion. Options are ISO 8601 or human-readable.
   - Recommendation: Use **ISO 8601** (the raw API format). The agent consuming this output can format for humans if needed. Machine-readable output is more versatile and consistent with the project's JSON-stdout convention.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ |
| Config file | Root `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest skills/calendar/tests/ -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAL-01 | list_events with date range params | unit | `uv run pytest skills/calendar/tests/test_calendar_api.py -x -k list` | No -- Wave 0 |
| CAL-01 | CLI list subcommand with --today/--week/--from/--to | unit | `uv run pytest skills/calendar/tests/test_calendar_cli.py -x -k list` | No -- Wave 0 |
| CAL-02 | get_event by ID returns full detail | unit | `uv run pytest skills/calendar/tests/test_calendar_api.py -x -k get` | No -- Wave 0 |
| CAL-02 | CLI get subcommand with event ID | unit | `uv run pytest skills/calendar/tests/test_calendar_cli.py -x -k get` | No -- Wave 0 |
| CAL-06 | Output uses result() with structured JSON | unit | `uv run pytest skills/calendar/tests/test_calendar_cli.py -x -k result` | No -- Wave 0 |
| CAL-07 | Entry point registered in pyproject.toml | unit | `uv run pytest skills/calendar/tests/test_calendar_cli.py -x -k subcommand` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest skills/calendar/tests/ -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `skills/calendar/tests/__init__.py` -- required for test discovery
- [ ] `skills/calendar/tests/test_calendar_api.py` -- covers CAL-01, CAL-02
- [ ] `skills/calendar/tests/test_calendar_cli.py` -- covers CAL-01, CAL-02, CAL-06, CAL-07
- [ ] Package skeleton (`pyproject.toml`, `__init__.py`, `calendar.py`, `cli.py`) -- needed before tests can import
- [ ] Root `pyproject.toml` updated with `claws-calendar` workspace member and dev dependency

## Sources

### Primary (HIGH confidence)
- [Events: list | Google Calendar API v3](https://developers.google.com/workspace/calendar/api/v3/reference/events/list) -- query parameters, pagination, scopes
- [Events resource | Google Calendar API v3](https://developers.google.com/workspace/calendar/api/v3/reference/events) -- full Event resource fields and types
- [Events: get | Google Calendar API v3](https://developers.google.com/workspace/calendar/api/v3/reference/events/get) -- single event retrieval endpoint
- Gmail skill source code (`skills/gmail/`) -- proven structural template in this project

### Secondary (MEDIUM confidence)
- None needed -- API docs and existing codebase fully cover this domain

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, mirrors Gmail exactly
- Architecture: HIGH -- direct clone of Gmail skill pattern with Calendar API endpoints
- Pitfalls: HIGH -- all-day events and singleEvents gotchas are well-documented in Calendar API docs; test naming collision learned from Gmail

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- Google Calendar API v3 is mature)
