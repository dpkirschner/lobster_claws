# Phase 6: Calendar Read Operations - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Calendar read skill (`claws calendar`) with `list` and `get` subcommands. Lists events by date range, gets event details by ID. Uses existing auth server (port 8301) for tokens, calls Google Calendar API directly with httpx + bearer token. Registered as `claws calendar` via entry-point discovery. Write operations (create, update, delete) are Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Date range interface
- **Convenience flags:** `--today`, `--week`, `--from YYYY-MM-DD`, `--to YYYY-MM-DD`
- **Default when no flags:** Claude's discretion (today or next 7 days — consider what's most useful for "what's happening" queries)
- **Max events:** `--max` flag with default of 25

### Scope strategy
- **Full calendar scope from Phase 6:** Use `https://www.googleapis.com/auth/calendar` (not `calendar.readonly`) so the same scope covers Phase 7 writes with zero changes

### Event output shape
- Claude's discretion — include at minimum: id, title (summary), start/end times, location, description. Attendees optional for list (include in get detail).

### Claude's Discretion
- Default date range (today vs next 7 days)
- Event output fields for list vs get (list can be summary, get can be full)
- Time format in output (ISO 8601 vs human-readable)
- Timezone handling
- All-day event representation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Gmail skill (reference implementation)
- `skills/gmail/src/claws_gmail/gmail.py` — Two-tier HTTP pattern: `get_access_token()` via ClawsClient, then raw httpx to Google API. Calendar module follows same structure.
- `skills/gmail/src/claws_gmail/cli.py` — argparse subcommand pattern, error handling, output via `result()`
- `skills/gmail/pyproject.toml` — Package structure, entry-point registration, workspace source

### Auth server
- `servers/google-auth/src/google_auth_server/app.py` — `POST /token` with `{"scopes": [...]}` returns `{"access_token", "expires_in", "token_type"}`

### Shared patterns
- `common/src/claws_common/client.py` — ClawsClient with `post_json()` for auth, `get(params=...)` for queries
- `common/src/claws_common/output.py` — `result()`, `fail()`, `crash()` conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClawsClient("google-auth", 8301).post_json("/token", {"scopes": [...]})` — exact same token acquisition pattern as Gmail
- `claws_common.output.result()` — wraps dict/str for stdout JSON output. Lists must be wrapped: `{"events": [...], "result_count": N}`
- Gmail's `gmail.py` — direct structural template for `calendar.py` (token function, API helper functions, error handler)
- Gmail's `cli.py` — direct structural template for Calendar's `cli.py` (argparse with subparsers)

### Established Patterns
- **Package layout:** `skills/calendar/src/claws_calendar/calendar.py` + `cli.py` + `pyproject.toml`
- **Entry point:** `calendar = "claws_calendar.cli:main"` in `[project.entry-points."claws.skills"]`
- **Test naming:** Use unique names (e.g., `test_calendar_api.py`, `test_calendar_cli.py`) to avoid importlib collisions
- **Error handling:** `httpx.HTTPStatusError` → `handle_calendar_error()`, `ConnectionError`/`TimeoutError` → `crash()`

### Integration Points
- Root `pyproject.toml`: Add `claws-calendar` as workspace member and dev dependency
- Auth server: Request `https://www.googleapis.com/auth/calendar` scope (full access, not readonly)
- Calendar API base: `https://www.googleapis.com/calendar/v3/calendars/primary/events`
- Meta-CLI: Auto-discovers via entry points — no changes needed

</code_context>

<specifics>
## Specific Ideas

- Phase 6 establishes the full package skeleton, API module, CLI registration — Phase 7 just adds more subcommands to the same package
- The Gmail skill had a conftest.py collision issue and test_cli.py naming collision — Calendar should use unique test file names from the start
- Calendar API uses RFC 3339 timestamps (e.g., `2026-03-20T10:00:00-07:00`) — need to handle timezone-aware datetime conversion for `--from`/`--to` flags

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-calendar-read-operations*
*Context gathered: 2026-03-20*
