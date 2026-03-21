---
phase: 08-multi-agent-identity
plan: 02
subsystem: auth
tags: [google-workspace, delegation, argparse, cli]

# Dependency graph
requires:
  - phase: 08-01
    provides: "Auth server subject delegation via POST /token body"
provides:
  - "--as flag on Gmail CLI for per-agent identity"
  - "--as flag on Calendar CLI for per-agent identity"
  - "as_user parameter on all public API functions in both skills"
  - "Subject threading from CLI through API to auth server"
affects: [09-google-drive]

# Tech tracking
tech-stack:
  added: []
  patterns: ["as_user parameter threading from CLI --as flag through API functions to auth server POST body"]

key-files:
  created: []
  modified:
    - skills/gmail/src/claws_gmail/gmail.py
    - skills/gmail/src/claws_gmail/cli.py
    - skills/gmail/tests/test_gmail.py
    - skills/gmail/tests/test_gmail_cli.py
    - skills/calendar/src/claws_calendar/calendar.py
    - skills/calendar/src/claws_calendar/cli.py
    - skills/calendar/tests/test_calendar_api.py
    - skills/calendar/tests/test_calendar_cli.py

key-decisions:
  - "Used as_user parameter name (not subject) to avoid conflict with email subject in send_message"
  - "Added --as flag on parent parser so it applies to all subcommands uniformly"

patterns-established:
  - "as_user threading: CLI --as dest=as_user -> API function as_user param -> get_access_token(as_user=) -> body['subject'] in POST /token"

requirements-completed: [ID-04, ID-05]

# Metrics
duration: 6min
completed: 2026-03-21
---

# Phase 08 Plan 02: Skill Subject Threading Summary

**Gmail and Calendar CLIs accept --as user@domain.com, threading subject through all API functions to auth server token requests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-21T23:11:44Z
- **Completed:** 2026-03-21T23:17:36Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Gmail skill: --as flag on all subcommands (inbox, read, send, search), as_user threaded through every public function
- Calendar skill: --as flag on all subcommands (list, get, create, update, delete), as_user threaded through every public function
- Full backward compatibility: all existing tests pass with as_user=None default
- 181 tests pass across entire repo with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --as flag to Gmail skill** - `cf7bf83` (test: RED) -> `345b121` (feat: GREEN)
2. **Task 2: Add --as flag to Calendar skill** - `d256b42` (test: RED) -> `5765658` (feat: GREEN)

_TDD tasks have multiple commits (test -> feat)_

## Files Created/Modified
- `skills/gmail/src/claws_gmail/gmail.py` - Added as_user param to get_access_token, list_inbox, read_message, send_message, search_messages
- `skills/gmail/src/claws_gmail/cli.py` - Added --as flag, threaded as_user through all dispatches
- `skills/gmail/tests/test_gmail.py` - Added 6 new tests for subject threading
- `skills/gmail/tests/test_gmail_cli.py` - Added 5 new tests for --as flag, updated 7 existing tests
- `skills/calendar/src/claws_calendar/calendar.py` - Added as_user param to get_access_token, list_events, get_event, create_event, update_event, delete_event
- `skills/calendar/src/claws_calendar/cli.py` - Added --as flag, threaded as_user through all dispatches
- `skills/calendar/tests/test_calendar_api.py` - Added 7 new tests for subject threading
- `skills/calendar/tests/test_calendar_cli.py` - Added 6 new tests for --as flag, updated 10 existing tests

## Decisions Made
- Used `as_user` as the identity parameter name across all functions (not `subject`) to avoid naming conflict with the email subject parameter in `send_message`
- Added `--as` flag on the parent argparse parser so it applies uniformly to all subcommands without repetition

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both Gmail and Calendar skills support multi-agent identity via --as flag
- Pattern validated end-to-end: CLI --as -> as_user param -> get_access_token -> POST /token with subject
- Ready for Drive skill (Phase 9) to follow identical pattern

## Self-Check: PASSED

All files found, all commits verified, all acceptance criteria met. 181 tests pass.

---
*Phase: 08-multi-agent-identity*
*Completed: 2026-03-21*
