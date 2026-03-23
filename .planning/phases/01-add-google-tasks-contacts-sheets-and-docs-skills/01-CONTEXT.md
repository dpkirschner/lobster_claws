# Phase 1: Add Google Tasks, Contacts, Sheets, and Docs skills - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add four new Google API skills to the lobster_claws monorepo: Tasks, Contacts, Sheets, and Docs. Each skill follows the established claw pattern: thin CLI in container → auth server token via ClawsClient → Google REST API with Bearer token → stdout result via output helpers. All four skills use the existing google-auth server on port 8301. No new servers needed.

</domain>

<decisions>
## Implementation Decisions

### Google Tasks Skill
- **D-01:** Full CRUD — list task lists, list tasks, create, complete (mark done), update, delete
- **D-02:** Nested subcommands for task list management: `claws tasks lists` (list task lists) and `claws tasks list/create/complete/update/delete` for task operations
- **D-03:** Google Tasks API scope: `https://www.googleapis.com/auth/tasks`

### Google Contacts Skill
- **D-04:** Full CRUD — list, search, get, create, update, delete contacts
- **D-05:** Subcommands: `list` (all contacts), `search` (by query), `get` (by resource name), `create` (with --name/--email/--phone), `update` (by resource name), `delete` (by resource name)
- **D-06:** Uses Google People API, scope: `https://www.googleapis.com/auth/contacts`

### Google Sheets Skill
- **D-07:** Data only — read/write cell values by range (A1 notation). No formatting, charts, or formulas
- **D-08:** Subcommands: `list` (list spreadsheets via Drive API), `read SPREADSHEET_ID RANGE`, `write SPREADSHEET_ID RANGE --values '[[...]]'`, `create --title NAME`
- **D-09:** Google Sheets API scope: `https://www.googleapis.com/auth/spreadsheets` (plus Drive readonly for list)

### Google Docs Skill
- **D-10:** Read text (extract plain text from structural JSON), create new docs with plain text, append text to existing docs. No formatting manipulation
- **D-11:** Subcommands: `list` (list docs via Drive API), `read DOC_ID` (extract plain text), `create --title NAME --body TEXT`, `append DOC_ID --body TEXT`
- **D-12:** Google Docs API scope: `https://www.googleapis.com/auth/documents` (plus Drive readonly for list)

### Cross-cutting
- **D-13:** All four skills support `--as user@domain.com` flag for multi-agent identity (established pattern)
- **D-14:** All skills use existing google-auth server (port 8301) — no new servers
- **D-15:** Follow established patterns exactly: ClawsClient for auth, raw httpx for Google APIs, argparse CLI, result/fail/crash output helpers
- **D-16:** Each skill is its own package: `claws-tasks`, `claws-contacts`, `claws-sheets`, `claws-docs`
- **D-17:** Entry points registered as `claws.skills` group: `tasks`, `contacts`, `sheets`, `docs`

### Claude's Discretion
- Error handling: follow the `handle_*_error()` pattern from existing skills (401→crash, 403→fail, 404→fail, 429→fail)
- API base URLs and endpoint paths
- Internal helper function structure (_get, _post, _put, _delete helpers per skill)
- Test structure and coverage (follow existing gmail/calendar/drive test patterns)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing skill implementations (reference patterns)
- `skills/gmail/src/claws_gmail/gmail.py` — Gmail API client pattern (token acquisition, HTTP helpers, error handling)
- `skills/gmail/src/claws_gmail/cli.py` — CLI entry point pattern (argparse, subcommands, --as flag, error routing)
- `skills/gmail/pyproject.toml` — Package configuration pattern (entry points, dependencies)
- `skills/gmail/tests/test_gmail.py` — API module test pattern (mock auth, mock httpx)
- `skills/gmail/tests/test_gmail_cli.py` — CLI test pattern (monkeypatch sys.argv, patch functions)
- `skills/calendar/src/claws_calendar/cli.py` — Calendar CLI pattern (create/update/delete subcommands)
- `skills/drive/src/claws_drive/drive.py` — Drive API client pattern (list files, download, upload)

### Shared library
- `common/src/claws_common/client.py` — ClawsClient (always use for auth server calls)
- `common/src/claws_common/output.py` — result(), fail(), crash() helpers

### Configuration
- `pyproject.toml` — Root workspace config (add new skills to dev deps and sources)
- `CLAUDE.md` — Project conventions and architecture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClawsClient` — HTTP wrapper for auth server communication, auto-resolves host
- `result()`, `fail()`, `crash()` — standardized output helpers
- `get_access_token()` pattern — identical in gmail.py, calendar.py, drive.py; copy for each new skill with appropriate scope
- `_*_headers()`, `_*_get()`, `_*_post()` — per-skill HTTP helper pattern

### Established Patterns
- Two-tier HTTP: ClawsClient for internal auth, raw httpx for external Google APIs
- Auth server POST /token with `{"scopes": [...], "subject": ...}` body
- argparse with top-level `--as` flag and `required=True` subcommands
- Tests mock ClawsClient for auth and httpx for Google API calls
- `handle_*_error()` translates HTTPStatusError to user-friendly messages

### Integration Points
- Root `pyproject.toml` — add to `[dependency-groups] dev` and `[tool.uv.sources]`
- Each skill's `pyproject.toml` — register `[project.entry-points."claws.skills"]`
- Google Workspace Admin — new scopes need domain-wide delegation grants

</code_context>

<specifics>
## Specific Ideas

No specific requirements — follow established Gmail/Calendar/Drive patterns exactly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-add-google-tasks-contacts-sheets-and-docs-skills*
*Context gathered: 2026-03-22*
