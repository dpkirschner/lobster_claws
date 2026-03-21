# Phase 7: Calendar Write Operations - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add create, update, and delete subcommands to the existing `claws calendar` CLI. The package, auth, API helpers, and entry point all exist from Phase 6. This phase adds `_calendar_post()`, `_calendar_put()`, `_calendar_delete()` HTTP helpers, the business logic functions (`create_event`, `update_event`, `delete_event`), and wires them into cli.py as new argparse subcommands.

</domain>

<decisions>
## Implementation Decisions

### Delete behavior
- **Confirmation:** Claude's discretion — no interactive prompts (agent is autonomous), but a `--force` flag is acceptable if it adds safety
- **Delete response:** Claude's discretion — at minimum confirm deletion with event_id

### Claude's Discretion
- Create event interface — which fields are required flags (--title, --start, --end) vs optional (--location, --description, --attendees)
- Time format for create/update — ISO 8601 strings, or YYYY-MM-DD HH:MM format
- Update interface — partial update (only change specified fields) vs full replacement
- Attendees syntax for create — comma-separated emails on --attendees flag
- Delete confirmation behavior (no-confirm vs --force)
- Delete response shape
- All-day event creation support (--all-day flag with --date instead of --start/--end)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing calendar code (Phase 6 output — MUST READ)
- `skills/calendar/src/claws_calendar/calendar.py` — Existing API module with `get_access_token()`, `_calendar_get()`, `format_event_summary/detail()`, `handle_calendar_error()`. Add `_calendar_post()`, `_calendar_put()`, `_calendar_delete()` + business logic here.
- `skills/calendar/src/claws_calendar/cli.py` — Existing CLI with list/get subcommands. Add create/update/delete subcommands here.
- `skills/calendar/pyproject.toml` — Package already configured, entry point registered.

### Gmail write pattern (reference)
- `skills/gmail/src/claws_gmail/gmail.py` — `send_message()` as reference for write operations: token acquisition, httpx POST, response handling

### Shared patterns
- `common/src/claws_common/output.py` — `result()`, `fail()`, `crash()` conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_access_token()` in `calendar.py` — already works, same for writes
- `_calendar_get()` — pattern to follow for `_calendar_post()`, `_calendar_put()`, `_calendar_delete()`
- `format_event_detail()` — use for returning created/updated event details
- `handle_calendar_error()` — already handles 401, 403, 404, 429 — works for write errors too
- `date_to_rfc3339()` — useful for converting create/update time inputs

### Established Patterns
- `CALENDAR_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary"` — already defined
- CLI uses argparse subparsers — add `create`, `update`, `delete` parsers to existing `subs`
- Error handling: `httpx.HTTPStatusError` → `handle_calendar_error()`, connection/timeout → `crash()`

### Integration Points
- `calendar.py`: Add 3 HTTP helpers + 3 business logic functions
- `cli.py`: Add 3 subcommand parsers + routing in main()
- Tests: Add to existing test files or create new ones (unique naming)
- No root pyproject.toml changes needed (already configured)
- No new packages or dependencies

</code_context>

<specifics>
## Specific Ideas

- Phase 7 is purely additive to Phase 6 code — no refactoring, just new functions and subcommands
- Calendar API `events.insert` (POST) and `events.update` (PUT) both return the created/updated event — pass through `format_event_detail()` for consistent output
- Calendar API `events.delete` returns 204 No Content — must construct response manually since there's no body

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-calendar-write-operations*
*Context gathered: 2026-03-20*
