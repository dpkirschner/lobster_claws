---
phase: 01-add-google-tasks-contacts-sheets-and-docs-skills
plan: 01
subsystem: api
tags: [google-tasks, httpx, argparse, crud, tdd]

requires:
  - phase: prior-google-auth
    provides: "google-auth server on port 8301 with delegation support"
  - phase: prior-gmail
    provides: "gmail skill pattern (API client + CLI + tests)"
provides:
  - "claws-tasks package with full CRUD for Google Tasks API"
  - "Tasks CLI with lists/list/create/complete/update/delete subcommands"
  - "--as flag for identity delegation on all operations"
affects: [contacts, sheets, docs]

tech-stack:
  added: [google-tasks-api-v1]
  patterns: [tasks-api-client-pattern]

key-files:
  created:
    - skills/tasks/pyproject.toml
    - skills/tasks/src/claws_tasks/__init__.py
    - skills/tasks/src/claws_tasks/tasks.py
    - skills/tasks/src/claws_tasks/cli.py
    - skills/tasks/tests/test_tasks.py
    - skills/tasks/tests/test_tasks_cli.py
  modified:
    - pyproject.toml

key-decisions:
  - "Followed gmail skill pattern exactly for consistency across Google API skills"
  - "Used @default as default tasklist ID matching Google Tasks API convention"

patterns-established:
  - "Google API skill pattern: API client module + CLI module + separate test files"

requirements-completed: [D-01, D-02, D-03, D-13, D-14, D-15, D-16, D-17]

duration: 3min
completed: 2026-03-23
---

# Phase 01 Plan 01: Google Tasks Skill Summary

**Full CRUD Google Tasks skill (claws-tasks) with API client, CLI, 44 tests, and workspace registration following gmail pattern**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T04:47:48Z
- **Completed:** 2026-03-23T04:51:03Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Tasks API client with token acquisition, list task lists, list/create/complete/update/delete tasks, and error handling
- Tasks CLI with 6 subcommands (lists, list, create, complete, update, delete) and --as identity delegation
- 44 tests (24 API + 20 CLI) all passing with TDD methodology
- Full test suite (257 tests) passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Tasks API client module with tests** - `045f1e9` (test+feat, TDD)
2. **Task 2: Create Tasks CLI with tests and register workspace** - `ca2bdfe` (feat, TDD)

_Note: TDD tasks have RED (failing tests) then GREEN (implementation) in single commits_

## Files Created/Modified
- `skills/tasks/pyproject.toml` - Package config with hatchling build and claws.skills entry point
- `skills/tasks/src/claws_tasks/__init__.py` - Package init
- `skills/tasks/src/claws_tasks/tasks.py` - Tasks API client with token acquisition, CRUD operations, error handling
- `skills/tasks/src/claws_tasks/cli.py` - CLI entry point with argparse subcommands
- `skills/tasks/tests/test_tasks.py` - 24 tests for API client
- `skills/tasks/tests/test_tasks_cli.py` - 20 tests for CLI routing
- `pyproject.toml` - Added claws-tasks to dev deps and uv.sources

## Decisions Made
- Followed gmail skill pattern exactly for consistency across Google API skills
- Used @default as default tasklist ID matching Google Tasks API convention

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added root pyproject.toml registration during Task 1**
- **Found during:** Task 1 (API client tests)
- **Issue:** Tests could not import claws_tasks module because package was not registered in workspace
- **Fix:** Added claws-tasks to dev deps and uv.sources in root pyproject.toml, ran uv sync
- **Files modified:** pyproject.toml
- **Verification:** uv sync installed package, tests import and pass
- **Committed in:** ca2bdfe (Task 2 commit, where root pyproject.toml change logically belongs)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Root pyproject.toml registration was planned for Task 2 but needed during Task 1 for test execution. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Google Tasks API scope must be added to domain-wide delegation in Google Workspace Admin (prerequisite documented in prior phases).

## Known Stubs
None - all functions are fully implemented with real API client calls.

## Next Phase Readiness
- Tasks skill complete, ready for Contacts skill (plan 02)
- Same pattern (API client + CLI + tests) applies to remaining Google API skills

---
*Phase: 01-add-google-tasks-contacts-sheets-and-docs-skills*
*Completed: 2026-03-23*
