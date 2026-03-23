---
phase: 01-add-google-tasks-contacts-sheets-and-docs-skills
plan: 04
subsystem: api
tags: [google-docs, docs-api, drive-api, text-extraction, argparse]

requires:
  - phase: prior
    provides: claws-common (ClawsClient, output helpers), google-auth-server on port 8301
provides:
  - claws-docs package with list/read/create/append operations
  - Plain text extraction from Google Docs structural JSON
  - Dual-scope auth (documents + drive.readonly) for listing and editing
affects: [docs-integration, google-workspace-skills]

tech-stack:
  added: []
  patterns: [batchUpdate-with-InsertTextRequest, endOfSegmentLocation-for-append, dual-scope-token]

key-files:
  created:
    - skills/docs/pyproject.toml
    - skills/docs/src/claws_docs/__init__.py
    - skills/docs/src/claws_docs/docs.py
    - skills/docs/src/claws_docs/cli.py
    - skills/docs/tests/test_docs.py
    - skills/docs/tests/test_docs_cli.py
  modified:
    - pyproject.toml

key-decisions:
  - "Dual scopes (documents + drive.readonly) requested together for listing via Drive API and editing via Docs API"
  - "Create-with-body uses two API calls: POST to create blank doc, then batchUpdate with InsertTextRequest"
  - "extract_text walks body.content -> paragraph -> elements -> textRun -> content for plain text output"

patterns-established:
  - "batchUpdate pattern: InsertTextRequest with endOfSegmentLocation for appending text"
  - "Docs skill follows same CLI/API client split as gmail and drive skills"

requirements-completed: [D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17]

duration: 4min
completed: 2026-03-23
---

# Phase 01 Plan 04: Google Docs Skill Summary

**Google Docs skill (claws-docs) with plain text extraction from structural JSON, list/read/create/append via Docs and Drive APIs**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T04:48:00Z
- **Completed:** 2026-03-23T04:52:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Docs API client with get_access_token (dual scopes), extract_text, list_documents, read_document, create_document, append_text
- CLI with list, read, create, append subcommands and --as flag for identity delegation
- 35 tests covering all API functions and CLI routing (21 API + 14 CLI)
- Package registered in workspace, full suite of 248 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Docs API client module with tests (TDD)** - `2257a0d` (test: RED) + `79034c4` (feat: GREEN)
2. **Task 2: Create Docs CLI with tests and register workspace (TDD)** - `7c18645` (feat: GREEN, included test)

## Files Created/Modified
- `skills/docs/pyproject.toml` - Package config with claws.skills entry point
- `skills/docs/src/claws_docs/__init__.py` - Package init
- `skills/docs/src/claws_docs/docs.py` - Docs API client with text extraction, CRUD operations
- `skills/docs/src/claws_docs/cli.py` - CLI entry point with list/read/create/append subcommands
- `skills/docs/tests/test_docs.py` - 21 API client tests
- `skills/docs/tests/test_docs_cli.py` - 14 CLI routing tests
- `pyproject.toml` - Added claws-docs to dev deps and uv.sources

## Decisions Made
- Used dual scopes (documents + drive.readonly) in a single token request for listing via Drive API and editing via Docs API
- Create-with-body uses two API calls (POST create blank + batchUpdate InsertTextRequest) matching the Google Docs API design
- extract_text walks structural JSON (body.content -> paragraph -> elements -> textRun -> content) for clean plain text output

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Google Docs API scope must be added to domain-wide delegation if not already present.

## Next Phase Readiness
- claws-docs package complete and tested
- Follows same patterns as gmail, drive, and calendar skills
- Ready for integration with other Google Workspace skills

---
*Phase: 01-add-google-tasks-contacts-sheets-and-docs-skills*
*Completed: 2026-03-23*
