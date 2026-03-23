# Phase 01: Add Google Tasks, Contacts, Sheets, and Docs Skills - Research

**Researched:** 2026-03-22
**Domain:** Google Workspace REST APIs + established claw pattern replication
**Confidence:** HIGH

## Summary

This phase adds four new Google API skills following the exact pattern established by gmail, calendar, and drive skills. The architecture is fully proven: each skill is a Python package with an API client module (token acquisition, HTTP helpers, error handling) and a CLI module (argparse with subcommands, `--as` flag, error routing). All four skills use the existing google-auth server on port 8301 -- no new servers needed.

The research confirms all four Google APIs (Tasks v1, People v1, Sheets v4, Docs v1) are stable REST APIs with straightforward CRUD operations. The only notable complexity is the Google Docs API's structural document model (batchUpdate with request objects for text insertion/appending), and the People API's etag requirement for contact updates.

**Primary recommendation:** Clone the gmail/calendar/drive pattern exactly for each skill. The established pattern handles auth, HTTP, error handling, output, and testing with zero ambiguity.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Tasks: Full CRUD -- list task lists, list tasks, create, complete (mark done), update, delete
- **D-02:** Tasks: Nested subcommands for task list management: `claws tasks lists` and `claws tasks list/create/complete/update/delete`
- **D-03:** Tasks API scope: `https://www.googleapis.com/auth/tasks`
- **D-04:** Contacts: Full CRUD -- list, search, get, create, update, delete contacts
- **D-05:** Contacts subcommands: `list`, `search`, `get`, `create`, `update`, `delete`
- **D-06:** People API, scope: `https://www.googleapis.com/auth/contacts`
- **D-07:** Sheets: Data only -- read/write cell values by range (A1 notation). No formatting, charts, or formulas
- **D-08:** Sheets subcommands: `list`, `read SPREADSHEET_ID RANGE`, `write SPREADSHEET_ID RANGE --values '[[...]]'`, `create --title NAME`
- **D-09:** Sheets API scope: `https://www.googleapis.com/auth/spreadsheets` (plus Drive readonly for list)
- **D-10:** Docs: Read text, create new docs, append text. No formatting manipulation
- **D-11:** Docs subcommands: `list`, `read DOC_ID`, `create --title NAME --body TEXT`, `append DOC_ID --body TEXT`
- **D-12:** Docs API scope: `https://www.googleapis.com/auth/documents` (plus Drive readonly for list)
- **D-13:** All four skills support `--as user@domain.com` flag
- **D-14:** All skills use existing google-auth server (port 8301)
- **D-15:** Follow established patterns exactly: ClawsClient for auth, raw httpx for Google APIs, argparse CLI, result/fail/crash output helpers
- **D-16:** Each skill is its own package: `claws-tasks`, `claws-contacts`, `claws-sheets`, `claws-docs`
- **D-17:** Entry points: `tasks`, `contacts`, `sheets`, `docs` in `claws.skills` group

### Claude's Discretion
- Error handling: follow `handle_*_error()` pattern from existing skills
- API base URLs and endpoint paths
- Internal helper function structure
- Test structure and coverage (follow existing test patterns)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

## Project Constraints (from CLAUDE.md)

- **Package naming:** `claws-*` (claws-tasks, claws-contacts, claws-sheets, claws-docs)
- **Build backend:** hatchling
- **HTTP client:** httpx via `ClawsClient` for auth server; raw httpx for Google APIs
- **Output:** Always use `result()`, `fail()`, `crash()` from `claws_common.output`
- **Host resolution:** `ClawsClient` handles automatically -- never hardcode IPs
- **Ports:** 8300+ range (auth server already on 8301)
- **Skill registration:** `[project.entry-points."claws.skills"]` in each pyproject.toml
- **Tests:** TDD with mocked boundaries -- mock ClawsClient for auth, mock httpx for Google API calls
- **Linting:** ruff (configured in root pyproject.toml)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | (workspace) | HTTP client for Google REST APIs | Already used by all existing skills |
| claws-common | workspace | ClawsClient, output helpers, host resolution | Shared library, mandatory |
| argparse | stdlib | CLI parsing with subcommands | Used by all existing skills |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Parse --values for Sheets write | Sheets skill only |
| hatchling | (build) | Build backend | All pyproject.toml files |

No new dependencies needed. All four skills use the same stack as gmail/calendar/drive.

## Architecture Patterns

### Recommended Project Structure (per skill)
```
skills/<name>/
├── pyproject.toml                    # Package config with entry point
├── src/claws_<name>/
│   ├── __init__.py                   # Empty
│   ├── <name>.py                     # API client: token, helpers, functions, errors
│   └── cli.py                        # CLI: argparse, subcommands, error routing
└── tests/
    ├── test_<name>.py                # API module tests (mock auth + httpx)
    └── test_<name>_cli.py            # CLI tests (monkeypatch sys.argv, patch functions)
```

### Pattern 1: API Client Module (e.g., tasks.py)
**What:** Module containing token acquisition, HTTP helpers, business functions, error handler
**When to use:** Every skill -- this is the canonical pattern
**Example:**
```python
# Source: skills/gmail/src/claws_gmail/gmail.py (established pattern)
import httpx
from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
SCOPE = "https://www.googleapis.com/auth/tasks"
BASE = "https://tasks.googleapis.com/tasks/v1"

def get_access_token(as_user: str | None = None) -> str:
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    body: dict = {"scopes": [SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def _get(path: str, token: str, params: dict | None = None) -> dict:
    resp = httpx.get(f"{BASE}{path}", params=params, headers=_headers(token), timeout=30.0)
    resp.raise_for_status()
    return resp.json()

def _post(path: str, token: str, body: dict) -> dict:
    resp = httpx.post(f"{BASE}{path}", json=body, headers=_headers(token), timeout=30.0)
    resp.raise_for_status()
    return resp.json()

# ... _put, _delete, _patch as needed

def handle_tasks_error(e: httpx.HTTPStatusError) -> None:
    # Same pattern as handle_gmail_error, handle_calendar_error, handle_drive_error
    ...
```

### Pattern 2: CLI Module (e.g., cli.py)
**What:** argparse with `--as` at parser level, subcommands via add_subparsers, try/except routing
**When to use:** Every skill
**Example:**
```python
# Source: skills/gmail/src/claws_gmail/cli.py (established pattern)
def main():
    parser = argparse.ArgumentParser(prog="claws-tasks", description="...")
    parser.add_argument("--as", dest="as_user", help="Act as this Google Workspace user (email)")
    subs = parser.add_subparsers(dest="command", required=True)
    # ... add subcommands ...
    args = parser.parse_args()
    try:
        # ... dispatch to API functions, call result() ...
    except httpx.HTTPStatusError as e:
        handle_tasks_error(e)
    except ConnectionError as e:
        crash(str(e))
    except TimeoutError as e:
        crash(str(e))
```

### Pattern 3: pyproject.toml
```toml
[project]
name = "claws-tasks"
version = "0.1.0"
description = "Google Tasks skill for Lobster Claws"
requires-python = ">=3.11"
dependencies = ["claws-common"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.entry-points."claws.skills"]
tasks = "claws_tasks.cli:main"

[tool.uv.sources]
claws-common = { workspace = true }
```

### Pattern 4: Root pyproject.toml Registration
Add to `[dependency-groups] dev` and `[tool.uv.sources]` for each new skill.

### Anti-Patterns to Avoid
- **Using google-api-python-client:** The project uses raw httpx for Google APIs, not the official client library. This is intentional -- thin wrapper, no heavy dependencies.
- **Importing requests:** Always use httpx. Never requests.
- **Hardcoding host IPs:** ClawsClient handles host resolution.
- **Missing --as flag:** Every public function must accept `as_user: str | None = None`.
- **Forgetting flush/exit codes:** Always use `result()`, `fail()`, `crash()` -- never bare `print()` or `sys.exit()`.

## Google API Specifics

### Google Tasks API v1
- **Base URL:** `https://tasks.googleapis.com/tasks/v1`
- **Scope:** `https://www.googleapis.com/auth/tasks`
- **Key endpoints:**
  - `GET /users/@me/lists` -- list all task lists
  - `POST /users/@me/lists` -- create task list
  - `GET /lists/{tasklist}/tasks` -- list tasks in a list
  - `POST /lists/{tasklist}/tasks` -- create task
  - `PATCH /lists/{tasklist}/tasks/{task}` -- update task (use PATCH for partial)
  - `DELETE /lists/{tasklist}/tasks/{task}` -- delete task
- **Complete a task:** PATCH with `{"status": "completed"}`
- **Task list ID:** The default task list is `@default`
- **Note:** Tasks belong to task lists. The `lists` subcommand lists task lists; other subcommands operate on tasks within a list (require `--list` to specify which, default to `@default`).

### Google People API v1 (Contacts)
- **Base URL:** `https://people.googleapis.com/v1`
- **Scope:** `https://www.googleapis.com/auth/contacts`
- **Key endpoints:**
  - `GET /people/me/connections?personFields=names,emailAddresses,phoneNumbers` -- list contacts
  - `GET /people:searchContacts?query=...&readMask=names,emailAddresses,phoneNumbers` -- search
  - `GET /people/{resourceName}?personFields=names,emailAddresses,phoneNumbers` -- get contact
  - `POST /people:createContact` (body: person object) -- create
  - `PATCH /people/{resourceName}:updateContact?updatePersonFields=...` (body: person with etag) -- update
  - `DELETE /people/{resourceName}:deleteContact` -- delete
- **Resource name format:** `people/c1234567890` (returned by API)
- **Etag requirement:** Updates require the contact's `etag` from metadata.sources to prevent concurrent modification conflicts. The `get` operation must return etag, and `update` must include it.
- **personFields/readMask:** Comma-separated field names like `names,emailAddresses,phoneNumbers`

### Google Sheets API v4
- **Base URL:** `https://sheets.googleapis.com/v4/spreadsheets`
- **Scope:** `https://www.googleapis.com/auth/spreadsheets` (read/write)
- **Drive readonly scope:** `https://www.googleapis.com/auth/drive.readonly` (for listing spreadsheets via Drive API)
- **Key endpoints:**
  - `POST /` (body: `{"properties": {"title": "..."}}`) -- create spreadsheet
  - `GET /{spreadsheetId}/values/{range}` -- read cell values
  - `PUT /{spreadsheetId}/values/{range}?valueInputOption=USER_ENTERED` (body: ValueRange) -- write values
- **ValueRange body:** `{"range": "Sheet1!A1:B2", "values": [["a", "b"], ["c", "d"]]}`
- **List spreadsheets:** Uses Drive API (`GET https://www.googleapis.com/drive/v3/files?q=mimeType='application/vnd.google-apps.spreadsheet'`) -- requires Drive readonly scope
- **Dual scope note:** get_access_token must request BOTH spreadsheets scope AND drive.readonly when the `list` subcommand is used. Simplest approach: always request both scopes.

### Google Docs API v1
- **Base URL:** `https://docs.googleapis.com/v1/documents`
- **Scope:** `https://www.googleapis.com/auth/documents`
- **Drive readonly scope:** `https://www.googleapis.com/auth/drive.readonly` (for listing docs)
- **Key endpoints:**
  - `POST /` (body: `{"title": "..."}`) -- create blank document
  - `GET /{documentId}` -- get document (returns structural JSON)
  - `POST /{documentId}:batchUpdate` -- apply edits
- **Reading plain text:** The GET response contains a `body.content` array of structural elements. Each paragraph has `elements` with `textRun.content`. Must walk the tree to extract text.
- **Appending text:** Use batchUpdate with InsertTextRequest: `{"insertText": {"text": "...", "endOfSegmentLocation": {}}}` to append at end of document body.
- **Creating with body text:** Create blank doc, then batchUpdate with InsertTextRequest.
- **List docs:** Uses Drive API (`GET https://www.googleapis.com/drive/v3/files?q=mimeType='application/vnd.google-apps.document'`) -- requires Drive readonly scope
- **Dual scope note:** Same as Sheets -- always request both scopes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth token acquisition | Custom OAuth2 flow | ClawsClient POST /token to auth server | Auth server already handles service account delegation, caching, scopes |
| HTTP error translation | Custom error parsing | `handle_*_error()` pattern | Consistent user-facing error messages across all skills |
| Output formatting | Custom JSON serialization | `result()` from claws_common.output | Handles flush, exit codes, JSON formatting |
| Host resolution in Docker | Hardcoded IPs or env vars | ClawsClient + resolve_host() | Automatic Docker/host detection |

## Common Pitfalls

### Pitfall 1: People API Etag for Updates
**What goes wrong:** Contact update fails with 400/412 because etag is missing from the request body.
**Why it happens:** The People API requires `person.metadata.sources[0].etag` in the update body to prevent concurrent modification.
**How to avoid:** The `get` function must return the full person object including metadata. The `update` function must first GET the contact to obtain the current etag, then include it in the PATCH body.
**Warning signs:** 400 errors on updateContact calls.

### Pitfall 2: Sheets Dual Scopes
**What goes wrong:** `list` subcommand fails with 403 because only the Sheets scope was requested, not Drive readonly.
**Why it happens:** Listing spreadsheets uses the Drive API, which requires its own scope.
**How to avoid:** Request both `spreadsheets` and `drive.readonly` scopes in get_access_token. Simplest: always request both.
**Warning signs:** 403 on Drive API calls from Sheets/Docs skills.

### Pitfall 3: Docs Document Structure Parsing
**What goes wrong:** Read returns raw structural JSON instead of plain text.
**Why it happens:** Docs API returns a complex nested structure (body > content > paragraph > elements > textRun > content).
**How to avoid:** Write an `extract_text()` helper that walks the document body and concatenates textRun.content strings.
**Warning signs:** Output contains structural JSON instead of readable text.

### Pitfall 4: Tasks Default List
**What goes wrong:** Task operations fail because no task list ID was provided.
**Why it happens:** Tasks API requires a task list ID for all task operations.
**How to avoid:** Use `@default` as the default task list ID when `--list` is not specified.
**Warning signs:** 404 errors on task endpoints.

### Pitfall 5: Sheets valueInputOption Required
**What goes wrong:** Write operation returns 400 because `valueInputOption` query parameter is missing.
**Why it happens:** The Sheets API requires `valueInputOption` for all write operations (PUT values).
**How to avoid:** Always include `?valueInputOption=USER_ENTERED` in write requests.
**Warning signs:** 400 error on spreadsheets.values.update calls.

### Pitfall 6: Docs Create + Write Needs Two API Calls
**What goes wrong:** Trying to create a doc with body text in a single API call.
**Why it happens:** `documents.create` only takes a title -- it creates a blank document. Text must be inserted via a second `batchUpdate` call.
**How to avoid:** Implement `create` as: (1) POST to create blank doc, (2) if --body provided, POST batchUpdate with InsertTextRequest.
**Warning signs:** Created documents are always empty despite --body being provided.

## Code Examples

### Docs: Extract Plain Text from Document Structure
```python
# Source: Google Docs API documentation structure
def extract_text(document: dict) -> str:
    """Extract plain text from Google Docs structural JSON."""
    content = document.get("body", {}).get("content", [])
    parts = []
    for element in content:
        paragraph = element.get("paragraph")
        if paragraph:
            for elem in paragraph.get("elements", []):
                text_run = elem.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))
    return "".join(parts)
```

### Docs: Append Text via batchUpdate
```python
# Source: Google Docs API batchUpdate reference
def append_text(doc_id: str, text: str, token: str) -> dict:
    body = {
        "requests": [
            {
                "insertText": {
                    "text": text,
                    "endOfSegmentLocation": {},
                }
            }
        ]
    }
    resp = httpx.post(
        f"{DOCS_BASE}/{doc_id}:batchUpdate",
        json=body,
        headers=_docs_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()
```

### Sheets: Write Values
```python
# Source: Google Sheets API v4 values.update reference
def write_values(spreadsheet_id: str, range_: str, values: list, token: str) -> dict:
    body = {"range": range_, "values": values}
    resp = httpx.put(
        f"{SHEETS_BASE}/{spreadsheet_id}/values/{range_}",
        params={"valueInputOption": "USER_ENTERED"},
        json=body,
        headers=_sheets_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()
```

### People API: Create Contact
```python
# Source: Google People API contacts guide
def create_contact(name: str, email: str | None, phone: str | None, token: str) -> dict:
    person: dict = {"names": [{"givenName": name}]}
    if email:
        person["emailAddresses"] = [{"value": email}]
    if phone:
        person["phoneNumbers"] = [{"value": phone}]
    resp = httpx.post(
        f"{PEOPLE_BASE}/people:createContact",
        json=person,
        headers=_contacts_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-api-python-client | Raw REST via httpx | Project convention | No heavy client library dependency; thin wrapper stays in control |
| OAuth2 in each skill | Shared auth server on port 8301 | Project Phase 08 | All skills use same token endpoint; scopes differ per skill |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0 |
| Config file | root pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest skills/tasks skills/contacts skills/sheets skills/docs -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Tasks: get_access_token with/without as_user | unit | `uv run pytest skills/tasks/tests/test_tasks.py -x` | Wave 0 |
| Tasks: list_task_lists, list_tasks, create, complete, update, delete | unit | same | Wave 0 |
| Tasks CLI: all subcommands route correctly | unit | `uv run pytest skills/tasks/tests/test_tasks_cli.py -x` | Wave 0 |
| Contacts: CRUD + search | unit | `uv run pytest skills/contacts/tests/test_contacts.py -x` | Wave 0 |
| Contacts CLI: all subcommands | unit | `uv run pytest skills/contacts/tests/test_contacts_cli.py -x` | Wave 0 |
| Sheets: create, read, write, list | unit | `uv run pytest skills/sheets/tests/test_sheets.py -x` | Wave 0 |
| Sheets CLI: all subcommands | unit | `uv run pytest skills/sheets/tests/test_sheets_cli.py -x` | Wave 0 |
| Docs: read (text extraction), create, append, list | unit | `uv run pytest skills/docs/tests/test_docs.py -x` | Wave 0 |
| Docs CLI: all subcommands | unit | `uv run pytest skills/docs/tests/test_docs_cli.py -x` | Wave 0 |
| Error handling: 401/403/404/429 per skill | unit | included in test_*.py | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest skills/<name> -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green (213 existing + new tests)

### Wave 0 Gaps
All test files are new (Wave 0 creates them alongside implementation):
- [ ] `skills/tasks/tests/test_tasks.py` -- API module tests
- [ ] `skills/tasks/tests/test_tasks_cli.py` -- CLI tests
- [ ] `skills/contacts/tests/test_contacts.py` -- API module tests
- [ ] `skills/contacts/tests/test_contacts_cli.py` -- CLI tests
- [ ] `skills/sheets/tests/test_sheets.py` -- API module tests
- [ ] `skills/sheets/tests/test_sheets_cli.py` -- CLI tests
- [ ] `skills/docs/tests/test_docs.py` -- API module tests
- [ ] `skills/docs/tests/test_docs_cli.py` -- CLI tests

No new framework install needed -- pytest already configured.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `skills/gmail/`, `skills/calendar/`, `skills/drive/` -- canonical implementation patterns
- [Google Tasks API REST reference](https://developers.google.com/workspace/tasks/reference/rest) -- endpoints, methods
- [Google People API REST reference](https://developers.google.com/people/api/rest) -- contacts endpoints
- [Google Sheets API v4 values reference](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values) -- read/write values
- [Google Docs API v1 reference](https://developers.google.com/workspace/docs/api/reference/rest) -- documents endpoints

### Secondary (MEDIUM confidence)
- [Google People API contacts guide](https://developers.google.com/people/v1/contacts) -- etag requirement, personFields usage

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- identical to existing skills, no new dependencies
- Architecture: HIGH -- exact pattern replication from gmail/calendar/drive
- Pitfalls: HIGH -- verified against official API docs (etag, dual scopes, valueInputOption, doc structure)
- API endpoints: HIGH -- verified against official REST reference docs

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable Google APIs, established project patterns)
