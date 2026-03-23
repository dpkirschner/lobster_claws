---
phase: 01-add-google-tasks-contacts-sheets-and-docs-skills
plan: 03
subsystem: sheets-skill
tags: [google-sheets, api-client, cli, skill]
dependency_graph:
  requires: [claws-common, google-auth-server]
  provides: [claws-sheets]
  affects: [pyproject.toml]
tech_stack:
  added: [claws-sheets]
  patterns: [dual-scope-auth, a1-notation, data-only-operations]
key_files:
  created:
    - skills/sheets/pyproject.toml
    - skills/sheets/src/claws_sheets/__init__.py
    - skills/sheets/src/claws_sheets/sheets.py
    - skills/sheets/src/claws_sheets/cli.py
    - skills/sheets/tests/test_sheets.py
    - skills/sheets/tests/test_sheets_cli.py
  modified:
    - pyproject.toml
decisions:
  - Dual scopes (spreadsheets + drive.readonly) requested together since list needs Drive API
  - Data-only operations per D-07 -- no formatting, charts, or formulas
  - valueInputOption=USER_ENTERED for write operations (lets Sheets interpret types)
  - Full URL for _sheets_get instead of path-based (flexibility for Sheets vs Drive base URLs)
metrics:
  duration: 221s
  completed: "2026-03-23T04:51:38Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 37
  tests_total: 250
---

# Phase 01 Plan 03: Google Sheets Skill Summary

Sheets API client and CLI with data-only list/read/write/create using dual-scope auth (spreadsheets + drive.readonly) and A1 notation ranges.

## What Was Built

### Sheets API Client (`sheets.py`)
- `get_access_token()` -- requests both `spreadsheets` and `drive.readonly` scopes (dual scope needed because listing spreadsheets uses Drive API)
- `list_spreadsheets()` -- queries Drive API with `mimeType='application/vnd.google-apps.spreadsheet'` filter
- `read_values()` -- GET Sheets API with A1 notation range, returns 2D values array
- `write_values()` -- PUT with `valueInputOption=USER_ENTERED` so Sheets auto-detects types
- `create_spreadsheet()` -- POST with `properties.title`
- `handle_sheets_error()` -- 401 crash, 403/404/429 fail, other crash
- All operations support `as_user` for identity delegation

### Sheets CLI (`cli.py`)
- `claws sheets list [--max N]` -- list spreadsheets
- `claws sheets read SPREADSHEET_ID RANGE` -- read cell values
- `claws sheets write SPREADSHEET_ID RANGE --values '[[...]]'` -- write cells (JSON 2D array)
- `claws sheets create --title NAME` -- create spreadsheet
- `--as user@domain.com` flag on all operations
- JSON parse error handling for `--values`
- Connection/timeout/HTTP error routing

### Package Registration
- `claws-sheets` added to root `pyproject.toml` dev deps and `[tool.uv.sources]`
- Entry point registered: `sheets = "claws_sheets.cli:main"`

## Commits

| Hash | Type | Description |
|------|------|-------------|
| cfec9f1 | test | Add failing tests for Sheets API client (RED) |
| fb3583f | feat | Implement Sheets API client with dual scope auth (GREEN) |
| d9b949f | test | Add failing tests for Sheets CLI (RED) |
| 694e9ce | feat | Add Sheets CLI with list/read/write/create and register workspace (GREEN) |

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all operations are fully wired to API functions.

## Verification

- 37 sheets tests pass (23 API + 14 CLI)
- 250 total tests pass (no regressions)
- `uv run claws sheets --help` shows all subcommands
- `uv sync` resolves cleanly with claws-sheets registered
