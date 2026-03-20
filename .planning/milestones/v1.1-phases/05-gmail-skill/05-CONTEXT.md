# Phase 5: Gmail Skill - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Thin CLI skill (`claws gmail`) with four subcommands: `inbox`, `read <id>`, `send`, `search <query>`. Gets a token from the auth server (port 8301), calls Gmail REST API directly with httpx + bearer token, outputs structured JSON via `claws_common.output`. Registered as `claws gmail` via entry-point discovery.

</domain>

<decisions>
## Implementation Decisions

### Output formatting
- **Inbox fields:** Claude's discretion — include at minimum id, from, subject, date, snippet for each message
- **Default page size:** 10 messages for inbox and search, with `--max` flag to override
- **Read output:** Claude's discretion — full body or truncate with `--full` flag. Consider that truncating long newsletters saves tokens for the agent.
- **Output format:** Claude's discretion — JSON array or JSONL. Consider that `result()` from claws_common.output handles dict→JSON serialization.

### Email sending behavior
- **CC/BCC:** Supported via optional `--cc` and `--bcc` flags
- **Body input:** `--body` flag for inline text, stdin fallback for long bodies (read from stdin if `--body` not provided and stdin is not a TTY)
- **Send response:** Return `{"message_id": "...", "thread_id": "..."}` on success — useful for follow-ups and threading
- **Safeguards:** Claude's discretion — `--dry-run` flag is acceptable if it adds minimal complexity

### Gmail API auth flow
- **Scope:** Use `https://www.googleapis.com/auth/gmail.modify` (single scope covers all operations)
- **Token management:** Fresh token from auth server on every CLI invocation — auth server handles caching, skill stays stateless
- **API calls:** Claude's discretion — direct calls to `googleapis.com` with httpx + Bearer header is the leaning (matches token-vending architecture, keeps auth server single-responsibility)

### Claude's Discretion
- Inbox output field selection (minimum: id, from, subject, date, snippet)
- Read body truncation behavior
- Output format (JSON array vs JSONL)
- Dry-run flag for send
- Direct Gmail API calls vs auth server proxy (direct is the leaning)
- MIME multipart parsing implementation details
- base64url encoding for send
- Error message formatting for Gmail API errors

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auth server (Phase 4 output)
- `servers/google-auth/src/google_auth_server/app.py` — Token vending API: `POST /token` with `{"scopes": [...]}`, returns `{"access_token", "expires_in", "token_type"}`
- `.planning/phases/04-google-auth-server/04-CONTEXT.md` — Auth server decisions: full URL scopes, HTTP status codes for errors, one retry policy

### Existing skill patterns
- `skills/transcribe/src/claws_transcribe/cli.py` — Reference CLI skill: argparse, ClawsClient usage, output helpers, error handling with fail/crash
- `common/src/claws_common/client.py` — ClawsClient with `post_json()` for auth server, `get(params=...)` for parameterized requests
- `common/src/claws_common/output.py` — `result()`, `fail()`, `crash()` — stdout/stderr/exit code conventions

### Gmail API
- `.planning/research/FEATURES.md` — Gmail REST API endpoints, MIME payload structure, search query syntax, scope reference
- `.planning/research/ARCHITECTURE.md` — Two-tier HTTP pattern (ClawsClient to auth server + raw httpx to Gmail API)
- `.planning/research/PITFALLS.md` — base64url encoding, MIME multipart tree walking, Gmail quota units

### Integration
- `data.md` — OpenClaw Docker environment, networking conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClawsClient` (`common/src/claws_common/client.py`): Use `post_json("/token", {"scopes": [...]})` to get access token from auth server at port 8301
- `claws_common.output` (`result/fail/crash`): All Gmail output goes through these helpers — `result(dict)` for JSON, `fail()` for user errors, `crash()` for infra errors
- `claws-transcribe/cli.py`: Reference for argparse setup, ClawsClient instantiation, error handling pattern with try/except ConnectionError/TimeoutError

### Established Patterns
- **Skill CLI structure:** argparse with `prog="claws-<name>"`, `ClawsClient(service=..., port=...)`, output via `result()`
- **Package layout:** `skills/<name>/src/claws_<name>/cli.py` with `pyproject.toml` using hatchling, entry-point in `claws.skills` group
- **Error handling:** `ConnectionError` → `crash()`, `TimeoutError` → `crash()`, validation errors → `fail()`
- **Two-tier HTTP for Gmail:** ClawsClient talks to auth server (internal), raw httpx talks to Gmail API (external) with Bearer token

### Integration Points
- Root `pyproject.toml`: Add `claws-gmail` as workspace member and dev dependency
- `cli/src/claws_cli/main.py`: Auto-discovers via entry points — no changes needed
- Auth server: `ClawsClient("google-auth", 8301).post_json("/token", {"scopes": ["https://www.googleapis.com/auth/gmail.modify"]})`
- Gmail API: `httpx.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers={"Authorization": f"Bearer {token}"})`

</code_context>

<specifics>
## Specific Ideas

- The Gmail skill uses a two-tier HTTP pattern unique to external-API skills: ClawsClient for internal auth server, raw httpx for external Gmail API. This is different from transcribe which only uses ClawsClient.
- Send response includes message_id and thread_id so the agent can reference sent emails later (useful for Calendar integration in v1.2 where the agent might send meeting invites and track responses).
- Body input supports both `--body` flag and stdin — the agent will typically use `--body` for short messages but stdin gives flexibility for programmatic use.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-gmail-skill*
*Context gathered: 2026-03-20*
