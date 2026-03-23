---
phase: 01-add-google-tasks-contacts-sheets-and-docs-skills
verified: 2026-03-22T00:00:00Z
status: passed
score: 21/21 must-haves verified
re_verification: false
---

# Phase 1: Add Google Tasks, Contacts, Sheets, and Docs Skills — Verification Report

**Phase Goal:** Add four new Google API skills (Tasks, Contacts, Sheets, Docs) following the established claw pattern — thin CLI with argparse, ClawsClient for auth, raw httpx for Google REST APIs, result/fail/crash output helpers.
**Verified:** 2026-03-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | claws tasks lists shows all task lists | VERIFIED | `list_task_lists()` in tasks.py; `lists` subcommand in cli.py; routes to result() |
| 2 | claws tasks list shows tasks in a task list | VERIFIED | `list_tasks()` in tasks.py; `list` subcommand with `--list` and `--max` flags |
| 3 | claws tasks create adds a new task | VERIFIED | `create_task()` in tasks.py; `create` subcommand with `--title` (required), `--list`, `--notes` |
| 4 | claws tasks complete marks a task as done | VERIFIED | `complete_task()` patches `{"status": "completed"}`; `complete` subcommand |
| 5 | claws tasks update modifies a task | VERIFIED | `update_task()` sends PATCH with provided fields; `update` subcommand |
| 6 | claws tasks delete removes a task | VERIFIED | `delete_task()` sends DELETE; CLI returns `{"deleted": True}` |
| 7 | --as flag delegates identity (tasks) | VERIFIED | `as_user` routed through all task functions; `dest="as_user"` in parser |
| 8 | claws contacts list shows all contacts | VERIFIED | `list_contacts()` GETs `/people/me/connections`; `list` subcommand with `--max` |
| 9 | claws contacts search finds contacts by query | VERIFIED | `search_contacts()` GETs `/people:searchContacts` with query param |
| 10 | claws contacts get retrieves a contact by resource name | VERIFIED | `get_contact()` GETs `/{resource_name}` with personFields |
| 11 | claws contacts create adds a new contact | VERIFIED | `create_contact()` POSTs to `/people:createContact`; optional email/phone |
| 12 | claws contacts update modifies a contact (with etag) | VERIFIED | `update_contact()` GETs etag first then PATCHes `/{resource_name}:updateContact` |
| 13 | claws contacts delete removes a contact | VERIFIED | `delete_contact()` DELETEs `/{resource_name}:deleteContact` |
| 14 | --as flag delegates identity (contacts) | VERIFIED | `as_user` routed through all contact functions |
| 15 | claws sheets list shows spreadsheets via Drive API | VERIFIED | `list_spreadsheets()` uses Drive API with mimeType filter |
| 16 | claws sheets read SPREADSHEET_ID RANGE returns cell values | VERIFIED | `read_values()` GETs Sheets API values endpoint; returns 2D array |
| 17 | claws sheets write SPREADSHEET_ID RANGE --values writes cell values | VERIFIED | `write_values()` PUTs with `valueInputOption=USER_ENTERED`; JSON parsed in CLI |
| 18 | claws sheets create --title NAME creates a new spreadsheet | VERIFIED | `create_spreadsheet()` POSTs with `{"properties": {"title": title}}` |
| 19 | claws docs list shows documents via Drive API | VERIFIED | `list_documents()` uses Drive API with mimeType='application/vnd.google-apps.document' |
| 20 | claws docs read DOC_ID extracts plain text from structural JSON | VERIFIED | `extract_text()` walks body.content->paragraph->elements->textRun->content |
| 21 | claws docs create --title NAME --body TEXT creates a doc and inserts text | VERIFIED | `create_document()` does two API calls when body provided: POST + batchUpdate |
| 22 | claws docs append DOC_ID --body TEXT appends text to existing doc | VERIFIED | `append_text()` uses batchUpdate with `insertText` + `endOfSegmentLocation: {}` |
| 23 | --as flag delegates identity (sheets, docs) | VERIFIED | `as_user` routed through all sheet and doc functions |

**Score:** 21/21 truths verified (truths 7, 14, 23 consolidated as cross-cutting --as flag)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skills/tasks/src/claws_tasks/tasks.py` | Tasks API client | VERIFIED | All 8 required functions present and substantive |
| `skills/tasks/src/claws_tasks/cli.py` | Tasks CLI entry point | VERIFIED | `main()` with 6 subcommands, `--as` flag, error routing |
| `skills/tasks/pyproject.toml` | Package config with entry point | VERIFIED | `tasks = "claws_tasks.cli:main"` under `[project.entry-points."claws.skills"]` |
| `skills/contacts/src/claws_contacts/contacts.py` | Contacts API client | VERIFIED | All 7 required functions present; etag fetch-before-patch implemented |
| `skills/contacts/src/claws_contacts/cli.py` | Contacts CLI entry point | VERIFIED | `main()` with 6 subcommands, `--as` flag, error routing |
| `skills/contacts/pyproject.toml` | Package config with entry point | VERIFIED | `contacts = "claws_contacts.cli:main"` |
| `skills/sheets/src/claws_sheets/sheets.py` | Sheets API client | VERIFIED | All 5 required functions; dual scope (sheets + drive.readonly); valueInputOption present |
| `skills/sheets/src/claws_sheets/cli.py` | Sheets CLI entry point | VERIFIED | `main()` with 4 subcommands; `json.loads()` for --values; error routing |
| `skills/sheets/pyproject.toml` | Package config with entry point | VERIFIED | `sheets = "claws_sheets.cli:main"` |
| `skills/docs/src/claws_docs/docs.py` | Docs API client | VERIFIED | `extract_text()`, `list_documents()`, `read_document()`, `create_document()`, `append_text()`, `handle_docs_error()` all present |
| `skills/docs/src/claws_docs/cli.py` | Docs CLI entry point | VERIFIED | `main()` with 4 subcommands including append; `--as` flag |
| `skills/docs/pyproject.toml` | Package config with entry point | VERIFIED | `docs = "claws_docs.cli:main"` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `skills/tasks/src/claws_tasks/cli.py` | `skills/tasks/src/claws_tasks/tasks.py` | import | WIRED | `from claws_tasks.tasks import complete_task, create_task, delete_task, handle_tasks_error, list_task_lists, list_tasks, update_task` |
| `skills/tasks/src/claws_tasks/tasks.py` | `claws_common.client` | ClawsClient for auth | WIRED | `ClawsClient(service="google-auth", port=8301)` present; used in `get_access_token()` |
| `skills/contacts/src/claws_contacts/cli.py` | `skills/contacts/src/claws_contacts/contacts.py` | import | WIRED | `from claws_contacts.contacts import create_contact, delete_contact, get_contact, handle_contacts_error, list_contacts, search_contacts, update_contact` |
| `skills/contacts/src/claws_contacts/contacts.py` | `claws_common.client` | ClawsClient for auth | WIRED | `ClawsClient(service="google-auth", port=AUTH_PORT)` where AUTH_PORT=8301 |
| `skills/sheets/src/claws_sheets/cli.py` | `skills/sheets/src/claws_sheets/sheets.py` | import | WIRED | `from claws_sheets.sheets import create_spreadsheet, handle_sheets_error, list_spreadsheets, read_values, write_values` |
| `skills/sheets/src/claws_sheets/sheets.py` | `claws_common.client` | ClawsClient for auth | WIRED | `ClawsClient(service="google-auth", port=AUTH_PORT)` |
| `skills/docs/src/claws_docs/cli.py` | `skills/docs/src/claws_docs/docs.py` | import | WIRED | `from claws_docs.docs import append_text, create_document, handle_docs_error, list_documents, read_document` |
| `skills/docs/src/claws_docs/docs.py` | `claws_common.client` | ClawsClient for auth | WIRED | `ClawsClient(service="google-auth", port=AUTH_PORT)` |
| Root `pyproject.toml` | All four skills | workspace members | WIRED | `claws-tasks`, `claws-contacts`, `claws-sheets`, `claws-docs` in both `[dependency-groups] dev` and `[tool.uv.sources]` |

---

### Data-Flow Trace (Level 4)

These skills are CLI tools, not rendering components. Data flows through: ClawsClient.post_json("/token") -> Google REST API -> result()/fail()/crash(). No static data stubs or hardcoded empty returns found in any of the four API client modules. All public functions call `get_access_token()` and then make live httpx calls.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `tasks.py` | `resp["access_token"]` | ClawsClient POST /token | Yes — live HTTP call | FLOWING |
| `tasks.py` | `data.get("items", [])` | httpx.get Tasks API | Yes — real API response | FLOWING |
| `contacts.py` | `data.get("connections", [])` | httpx.get People API | Yes — real API response | FLOWING |
| `contacts.py` | `current.get("etag", "")` | httpx.get before PATCH | Yes — fetched from live contact | FLOWING |
| `sheets.py` | `data.get("files", [])` | httpx.get Drive API | Yes — real API response | FLOWING |
| `sheets.py` | `data.get("values", [])` | httpx.get Sheets API | Yes — real API response | FLOWING |
| `docs.py` | `extract_text(doc)` | httpx.get Docs API | Yes — structural JSON from live doc | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Tasks skill discoverable | `uv run claws tasks --help` | Shows `{lists,list,create,complete,update,delete}` | PASS |
| Contacts skill discoverable | `uv run claws contacts --help` | Shows `{list,search,get,create,update,delete}` | PASS |
| Sheets skill discoverable | `uv run claws sheets --help` | Shows `{list,read,write,create}` | PASS |
| Docs skill discoverable | `uv run claws docs --help` | Shows `{list,read,create,append}` | PASS |
| Tasks test suite | `uv run pytest skills/tasks` | 44 passed | PASS |
| Contacts test suite | `uv run pytest skills/contacts` | 38 passed | PASS |
| Sheets test suite | `uv run pytest skills/sheets` | 37 passed | PASS |
| Docs test suite | `uv run pytest skills/docs` | 37 passed | PASS |
| Full regression suite | `uv run pytest` | 369 passed, 0 failures | PASS |

---

### Requirements Coverage

All requirement IDs D-01 through D-17 from CONTEXT.md are accounted for across the four plans.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01 | 01-01-PLAN | Tasks: full CRUD — list task lists, list/create/complete/update/delete tasks | SATISFIED | All 7 functions in tasks.py; all subcommands in cli.py |
| D-02 | 01-01-PLAN | Tasks: nested subcommands (`lists` for task lists, `list/create/complete/update/delete` for tasks) | SATISFIED | `lists` subcommand distinct from `list`; `--list` flag for tasklist ID |
| D-03 | 01-01-PLAN | Tasks scope: `https://www.googleapis.com/auth/tasks` | SATISFIED | `TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"` in tasks.py |
| D-04 | 01-02-PLAN | Contacts: full CRUD — list, search, get, create, update, delete | SATISFIED | All 6 CRUD functions in contacts.py |
| D-05 | 01-02-PLAN | Contacts subcommands: list, search, get, create, update, delete | SATISFIED | All 6 subcommands in contacts CLI |
| D-06 | 01-02-PLAN | People API scope: `https://www.googleapis.com/auth/contacts` | SATISFIED | `CONTACTS_SCOPE = "https://www.googleapis.com/auth/contacts"` in contacts.py |
| D-07 | 01-03-PLAN | Sheets: data only — read/write cell values by range. No formatting, charts, formulas | SATISFIED | Only `list_spreadsheets`, `read_values`, `write_values`, `create_spreadsheet` — no formatting functions |
| D-08 | 01-03-PLAN | Sheets subcommands: list, read SPREADSHEET_ID RANGE, write SPREADSHEET_ID RANGE --values, create --title | SATISFIED | All 4 subcommands implemented as specified |
| D-09 | 01-03-PLAN | Sheets scopes: spreadsheets + drive.readonly | SATISFIED | `get_access_token()` requests `[SHEETS_SCOPE, DRIVE_READONLY_SCOPE]` |
| D-10 | 01-04-PLAN | Docs: read text extraction, create with plain text, append. No formatting manipulation | SATISFIED | `extract_text()` extracts plain text; create/append use batchUpdate with plain text |
| D-11 | 01-04-PLAN | Docs subcommands: list, read DOC_ID, create --title --body, append DOC_ID --body | SATISFIED | All 4 subcommands implemented as specified |
| D-12 | 01-04-PLAN | Docs scopes: documents + drive.readonly | SATISFIED | `get_access_token()` requests `[DOCS_SCOPE, DRIVE_READONLY_SCOPE]` |
| D-13 | All plans | All four skills support `--as user@domain.com` flag | SATISFIED | `--as` / `dest="as_user"` in all four CLIs; propagated to all API functions |
| D-14 | All plans | All skills use existing google-auth server (port 8301) — no new servers | SATISFIED | `AUTH_PORT = 8301` and `ClawsClient(service="google-auth", port=8301)` in all four API modules |
| D-15 | All plans | Follow established patterns: ClawsClient for auth, raw httpx for Google APIs, argparse CLI, result/fail/crash | SATISFIED | Pattern followed exactly in all four skills |
| D-16 | All plans | Each skill is its own package: claws-tasks, claws-contacts, claws-sheets, claws-docs | SATISFIED | Four separate pyproject.toml files with correct package names |
| D-17 | All plans | Entry points registered as claws.skills group: tasks, contacts, sheets, docs | SATISFIED | `[project.entry-points."claws.skills"]` with correct keys in all four pyproject.toml files |

All 17 requirements satisfied. No orphaned requirements.

---

### Anti-Patterns Found

Scanned all 8 implementation files (4 API modules + 4 CLI modules). No blockers or warnings found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TODOs, stubs, placeholder returns, or hardcoded empty data found | — | — |

Note: `data.get("items", [])` and similar calls are safe defaults for absent API response keys, not stub data — the fetch is live.

---

### Human Verification Required

All four skills require a live Google Workspace environment to exercise end-to-end. The following cannot be verified programmatically:

**1. Token acquisition from google-auth server**
- Test: Run `claws tasks lists` with google-auth server running on port 8301
- Expected: Returns JSON list of task lists
- Why human: Requires live google-auth server and valid service account credentials

**2. Google API calls with live tokens**
- Test: Run `claws contacts list`, `claws sheets read`, `claws docs read DOC_ID` against real Google Workspace
- Expected: Each command returns non-empty JSON result
- Why human: Requires domain-wide delegation grants for the new scopes (Tasks, Contacts, Sheets, Documents)

**3. Contacts etag update flow**
- Test: `claws contacts create --name "Test"` then `claws contacts update people/CXXX --name "Updated"`
- Expected: Second call succeeds without 400 etag mismatch error
- Why human: etag correctness depends on live API response; can't simulate actual etag values in integration

**4. Docs plain-text extraction accuracy**
- Test: `claws docs read DOC_ID` on a real document with formatting
- Expected: Returns readable plain text without structural JSON noise
- Why human: Can't verify text extraction quality without a real document's structural JSON

---

### Gaps Summary

No gaps found. All 21 observable truths are verified, all artifacts exist and are fully wired, all 17 requirements are satisfied, and the full test suite passes (369 tests, 0 failures). The phase goal is achieved.

---

_Verified: 2026-03-22T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
