---
phase: 01-add-google-tasks-contacts-sheets-and-docs-skills
plan: 02
subsystem: api
tags: [google-contacts, people-api, httpx, argparse, crud]

requires:
  - phase: prior
    provides: "claws-common client library, google-auth server, gmail skill pattern"
provides:
  - "claws-contacts package with full CRUD + search via People API"
  - "contacts CLI with list, search, get, create, update, delete subcommands"
  - "--as flag for identity delegation on contacts operations"
affects: [docs-skill, sheets-skill]

tech-stack:
  added: []
  patterns: [etag-based-optimistic-concurrency-on-update]

key-files:
  created:
    - skills/contacts/src/claws_contacts/contacts.py
    - skills/contacts/src/claws_contacts/cli.py
    - skills/contacts/pyproject.toml
    - skills/contacts/tests/test_contacts.py
    - skills/contacts/tests/test_contacts_cli.py
  modified:
    - pyproject.toml

key-decisions:
  - "Followed gmail skill pattern exactly for consistency"
  - "Used full URLs in HTTP helpers since People API endpoints vary (people/me/connections vs people:searchContacts)"
  - "Etag fetched from top-level contact response etag field for update operations"

patterns-established:
  - "Contacts CRUD: thin CLI dispatches to API client, API client uses httpx directly for Google APIs"
  - "Etag pattern: GET before PATCH to obtain etag for optimistic concurrency"

requirements-completed: [D-04, D-05, D-06, D-13, D-14, D-15, D-16, D-17]

duration: 4min
completed: 2026-03-23
---

# Phase 01 Plan 02: Google Contacts Skill Summary

**Full CRUD contacts skill (claws-contacts) with People API client, etag-based updates, search, and --as identity delegation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T04:48:00Z
- **Completed:** 2026-03-23T04:52:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- People API client with list, search, get, create, update (etag), and delete operations
- CLI with 6 subcommands all supporting --as flag for identity delegation
- 40 tests covering API client and CLI (22 API + 18 CLI)
- Full test suite at 253 tests passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Contacts API client module with tests** - `27ddae0` (feat)
2. **Task 2: Create Contacts CLI with tests and register workspace** - `a5be583` (feat)

## Files Created/Modified
- `skills/contacts/pyproject.toml` - Package config with hatchling build and claws.skills entry point
- `skills/contacts/src/claws_contacts/__init__.py` - Package init
- `skills/contacts/src/claws_contacts/contacts.py` - People API client with CRUD, search, etag handling, error translation
- `skills/contacts/src/claws_contacts/cli.py` - CLI entry point with list/search/get/create/update/delete subcommands
- `skills/contacts/tests/test_contacts.py` - 22 tests for API client
- `skills/contacts/tests/test_contacts_cli.py` - 18 tests for CLI routing
- `pyproject.toml` - Added claws-contacts to dev dependencies and uv.sources

## Decisions Made
- Followed gmail skill pattern exactly for consistency across skills
- Used full URLs in HTTP helper functions since People API endpoints vary in structure
- Etag fetched from top-level contact response for update operations (simpler than navigating metadata.sources)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Contacts scope must be added to domain-wide delegation in Google Workspace Admin (prerequisite from prior phases).

## Next Phase Readiness
- Contacts skill complete and registered in workspace
- Pattern established for remaining skills (tasks, sheets, docs)
- Full test suite green at 253 tests

## Self-Check: PASSED

All 6 created files verified present. Both commit hashes (27ddae0, a5be583) verified in git log. 253 tests passing.

---
*Phase: 01-add-google-tasks-contacts-sheets-and-docs-skills*
*Completed: 2026-03-23*
