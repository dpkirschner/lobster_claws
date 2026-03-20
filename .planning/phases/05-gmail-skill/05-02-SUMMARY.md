---
phase: 05-gmail-skill
plan: 02
subsystem: cli
tags: [argparse, gmail, cli, entry-point]

# Dependency graph
requires:
  - phase: 05-gmail-skill/01
    provides: "gmail.py module with list_inbox, read_message, send_message, search_messages, handle_gmail_error"
provides:
  - "claws-gmail CLI entry point with inbox, read, send, search subcommands"
  - "Gmail skill discoverable via `claws gmail` meta-CLI"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subcommand CLI pattern with argparse and required subparser"
    - "stdin fallback for message body when not a TTY"

key-files:
  created:
    - skills/gmail/src/claws_gmail/cli.py
    - skills/gmail/tests/test_gmail_cli.py
  modified:
    - skills/gmail/tests/test_gmail.py

key-decisions:
  - "Renamed test_cli.py to test_gmail_cli.py to avoid importlib module name collision with transcribe test_cli.py"
  - "Moved conftest.py fixtures inline into test_gmail.py to avoid conftest module collision with google-auth"

patterns-established:
  - "Unique test file names across workspace to avoid --import-mode=importlib collisions"

requirements-completed: [GMAIL-01, GMAIL-02, GMAIL-03, GMAIL-04, GMAIL-05, GMAIL-06]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 05 Plan 02: Gmail CLI Summary

**Argparse CLI with inbox/read/send/search subcommands delegating to gmail.py, plus workspace wiring for `claws gmail` discovery**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T06:17:04Z
- **Completed:** 2026-03-20T06:21:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- CLI entry point with 4 subcommands (inbox, read, send, search) routing to gmail.py functions
- All list outputs wrapped in dicts with messages array and result_count
- Send supports --body flag, stdin fallback, --cc, --bcc
- Gmail skill discoverable as `claws gmail` via meta-CLI entry-point discovery
- Full 100-test suite passing with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): CLI routing tests** - `2701998` (test)
2. **Task 1 (GREEN): CLI implementation** - `c8f9188` (feat)
3. **Task 2: Workspace wiring + conftest fix** - `7d0e71e` (chore)

## Files Created/Modified
- `skills/gmail/src/claws_gmail/cli.py` - Argparse CLI with 4 subcommands, error handling, stdin fallback
- `skills/gmail/tests/test_gmail_cli.py` - 12 tests covering all subcommands, error cases, stdin
- `skills/gmail/tests/test_gmail.py` - Added fixtures (moved from conftest.py)
- `skills/gmail/tests/conftest.py` - Deleted (fixtures moved to test_gmail.py)

## Decisions Made
- Renamed test_cli.py to test_gmail_cli.py to avoid importlib module name collision with transcribe tests
- Moved conftest.py fixtures into test_gmail.py to fix plugin registration collision between gmail and google-auth conftest files under --import-mode=importlib

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed conftest.py module name collision**
- **Found during:** Task 2 (full test suite verification)
- **Issue:** Both `skills/gmail/tests/conftest.py` and `servers/google-auth/tests/conftest.py` resolved to the same module name `tests.conftest` under `--import-mode=importlib`, causing pytest plugin registration error
- **Fix:** Moved gmail conftest fixtures inline into test_gmail.py and deleted conftest.py
- **Files modified:** skills/gmail/tests/test_gmail.py, skills/gmail/tests/conftest.py (deleted)
- **Verification:** Full test suite passes (100 tests)
- **Committed in:** 7d0e71e

**2. [Rule 3 - Blocking] Fixed test_cli.py module name collision**
- **Found during:** Task 2 (full test suite verification)
- **Issue:** Both `skills/gmail/tests/test_cli.py` and `skills/transcribe/tests/test_cli.py` resolved to same module name, causing gmail tests to run under transcribe path (phantom tests)
- **Fix:** Renamed to test_gmail_cli.py (following Phase 04 precedent of unique test file names)
- **Files modified:** skills/gmail/tests/test_cli.py -> test_gmail_cli.py
- **Verification:** Full test suite passes with correct 100 tests (not 105 with phantom duplicates)
- **Committed in:** 7d0e71e

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for correct test collection. Pre-existing issue from Plan 05-01 conftest creation. No scope creep.

## Issues Encountered
- Root pyproject.toml already had claws-gmail in dev deps and uv sources from Plan 05-01, so no changes needed there

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Gmail skill complete: CLI + API module + workspace integration
- Phase 05 fully complete (both plans executed)
- Ready for integration testing with live Google Workspace (requires service account + delegation setup per Phase 04 USER-SETUP)

---
*Phase: 05-gmail-skill*
*Completed: 2026-03-20*
