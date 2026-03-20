---
phase: 06-calendar-read-operations
plan: 01
subsystem: api
tags: [google-calendar, httpx, calendar-api, tdd]

# Dependency graph
requires:
  - phase: 04-google-auth-server
    provides: "Auth server on port 8301 for OAuth token acquisition"
provides:
  - "Calendar API module with list_events, get_event, format helpers, error handling"
  - "claws-calendar package skeleton registered as workspace member"
affects: [06-02-cli, 07-calendar-write-operations]

# Tech tracking
tech-stack:
  added: [claws-calendar]
  patterns: [two-tier-http-calendar, event-summary-detail-formatting]

key-files:
  created:
    - skills/calendar/src/claws_calendar/calendar.py
    - skills/calendar/tests/test_calendar_api.py
    - skills/calendar/pyproject.toml
    - skills/calendar/src/claws_calendar/__init__.py
  modified:
    - pyproject.toml

key-decisions:
  - "Cloned Gmail skill pattern exactly: ClawsClient for auth, raw httpx for Calendar API"
  - "Used CALENDAR_BASE pointing to primary calendar (calendars/primary)"

patterns-established:
  - "Calendar event formatting: format_event_summary for lists, format_event_detail for single event views"
  - "All-day detection via 'date' key presence in start dict"

requirements-completed: [CAL-01, CAL-02, CAL-06]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 06 Plan 01: Calendar API Module Summary

**Calendar API module with list_events/get_event using two-tier HTTP pattern (ClawsClient auth + raw httpx), all-day event handling, and error translation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T07:00:29Z
- **Completed:** 2026-03-20T07:03:11Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments
- Calendar API module with get_access_token, list_events, get_event, format_event_summary, format_event_detail, date_to_rfc3339, handle_calendar_error
- Package skeleton with workspace registration and entry-point
- 19 unit tests covering all behaviors, full suite green (119 tests)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Package skeleton + failing tests** - `32aced9` (test)
2. **Task 1 GREEN: Implement calendar.py** - `1aff55e` (feat)

## Files Created/Modified
- `skills/calendar/pyproject.toml` - Package definition with claws-calendar entry-point
- `skills/calendar/src/claws_calendar/__init__.py` - Package init
- `skills/calendar/src/claws_calendar/calendar.py` - Calendar API module: token acquisition, list/get events, formatting, error handling
- `skills/calendar/tests/__init__.py` - Test package init
- `skills/calendar/tests/test_calendar_api.py` - 19 unit tests covering all calendar API behaviors
- `pyproject.toml` - Added claws-calendar to workspace members and dev dependencies

## Decisions Made
- Cloned Gmail skill pattern exactly for consistency across skills
- Used `calendars/primary` as base URL (most common calendar)
- All-day event detection based on presence of `date` key vs `dateTime` in start object

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed import sorting for ruff compliance**
- **Found during:** Task 1 (verification step)
- **Issue:** Import blocks not sorted per ruff I001 rule
- **Fix:** Ran `ruff check --fix` to auto-sort imports
- **Files modified:** calendar.py, test_calendar_api.py
- **Verification:** `ruff check skills/calendar/` passes clean
- **Committed in:** 1aff55e (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Cosmetic import ordering fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Calendar API module ready for Plan 02 to wire into CLI (argparse commands)
- Entry-point already registered: `calendar = "claws_calendar.cli:main"`
- All formatting and error handling in place for CLI to consume

---
*Phase: 06-calendar-read-operations*
*Completed: 2026-03-20*
