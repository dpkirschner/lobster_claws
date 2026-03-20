# Phase 5: Gmail Skill - Research

**Researched:** 2026-03-19
**Domain:** Gmail CLI skill -- thin CLI calling Gmail REST API directly with httpx + bearer token from auth server
**Confidence:** HIGH

## Summary

Phase 5 builds a `claws-gmail` CLI skill with four subcommands (`inbox`, `read`, `send`, `search`) that gets an access token from the Phase 4 auth server (port 8301) and calls the Gmail REST API directly using httpx. This is a **skill-only phase** -- no new server is needed. The auth server already exists and handles token vending.

The main technical challenges are: (1) MIME payload tree-walking to extract plain-text bodies from Gmail's nested message format, (2) base64url encoding for message send (not standard base64), (3) the two-tier HTTP pattern where ClawsClient talks to the auth server while raw httpx talks to Gmail API, and (4) `result()` from `claws_common.output` only accepts `str | dict`, so list outputs (inbox, search) must be wrapped in a dict.

**Primary recommendation:** Build a `gmail.py` module within the skill that encapsulates all Gmail API interaction (token acquisition, message listing, reading, sending, searching, MIME parsing), keeping `cli.py` as a thin argparse wrapper that delegates to `gmail.py` and calls `result()`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Subcommands:** `inbox`, `read <id>`, `send`, `search <query>`
- **Auth scope:** `https://www.googleapis.com/auth/gmail.modify` (single scope covers all operations)
- **Token flow:** Fresh token from auth server on every CLI invocation via `ClawsClient("google-auth", 8301).post_json("/token", {"scopes": [...]})`
- **API calls:** Direct calls to `gmail.googleapis.com` with httpx + Bearer header (not proxied through a server)
- **Default page size:** 10 messages for inbox and search, with `--max` flag to override
- **CC/BCC:** Supported via optional `--cc` and `--bcc` flags
- **Body input:** `--body` flag for inline text, stdin fallback for long bodies (read from stdin if `--body` not provided and stdin is not a TTY)
- **Send response:** Return `{"message_id": "...", "thread_id": "..."}` on success

### Claude's Discretion
- Inbox output field selection (minimum: id, from, subject, date, snippet)
- Read body truncation behavior
- Output format (JSON array vs JSONL) -- note: `result()` takes `dict`, not `list`, so wrapping in a dict is required
- Dry-run flag for send
- MIME multipart parsing implementation details
- base64url encoding for send
- Error message formatting for Gmail API errors

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GMAIL-01 | User can list inbox messages with sender, subject, date, and snippet | Gmail `messages.list` + `messages.get` with `format=metadata`; two-step fetch pattern documented in Architecture Patterns |
| GMAIL-02 | User can read a message by ID with full plain-text body extracted from MIME | Gmail `messages.get` with `format=full`; MIME tree-walking algorithm in Code Examples |
| GMAIL-03 | User can send an email with to, subject, and body | Gmail `messages.send` with base64url-encoded RFC 2822; `email.mime` stdlib for MIME construction |
| GMAIL-04 | User can search messages using Gmail query syntax | Same `messages.list` endpoint with `q` parameter; httpx handles URL encoding via `params=` |
| GMAIL-05 | Gmail skill outputs structured JSON via stdout using claws_common.output | All outputs go through `result()` as dicts; `result()` only accepts `str | dict` so lists must be wrapped |
| GMAIL-06 | Gmail CLI registered as `claws gmail` via entry-point discovery | Entry point in pyproject.toml: `[project.entry-points."claws.skills"]` gmail = "claws_gmail.cli:main" |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | (already in workspace via claws-common) | Gmail API HTTP calls with Bearer token | Already the project HTTP client; direct REST calls match architecture decision |
| claws-common | workspace | ClawsClient for auth server + output helpers | Established project dependency for all skills |
| email.mime.text (stdlib) | Python 3.12+ stdlib | Construct RFC 2822 MIME messages for send | No external dependency needed; stdlib handles MIME construction |
| base64 (stdlib) | Python 3.12+ stdlib | base64url encode MIME messages for Gmail send API | `urlsafe_b64encode` with padding stripped |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse (stdlib) | Python 3.12+ stdlib | CLI argument parsing with subparsers | Established pattern from claws-transcribe |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct httpx to Gmail | google-api-python-client | Heavy dependency (15+ transitive), conflicts with httpx pattern, adds discovery doc fetch latency. Rejected in REQUIREMENTS.md out-of-scope. |
| email.mime (stdlib) | Manual string formatting | Fragile, breaks with non-ASCII, misses required headers. Stdlib handles edge cases. |

**Installation:**
```bash
# No new dependencies needed -- claws-gmail depends only on claws-common (which brings httpx)
# Just add to root pyproject.toml workspace members and dev dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
skills/gmail/
├── pyproject.toml              # depends on: claws-common
├── src/claws_gmail/
│   ├── __init__.py
│   ├── cli.py                  # argparse with subparsers: inbox, read, send, search
│   └── gmail.py                # Gmail API client: token acquisition, API calls, MIME parsing
└── tests/
    ├── __init__.py
    ├── test_cli.py             # Mock gmail module, test argparse routing + output
    └── test_gmail.py           # Mock httpx responses, test MIME parsing, base64url encoding
```

### Pattern 1: Two-Tier HTTP
**What:** ClawsClient talks to the auth server on the host (internal HTTP), then raw httpx talks to Gmail API (external HTTPS with Bearer token).
**When to use:** Every Gmail API call requires this flow: get token, then call API.
**Example:**
```python
# Source: existing auth server at servers/google-auth/src/google_auth_server/app.py
# and CONTEXT.md integration points

from claws_common.client import ClawsClient
import httpx

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"

def get_token() -> str:
    """Get access token from auth server."""
    auth = ClawsClient(service="google-auth", port=8301)
    resp = auth.post_json("/token", {"scopes": [GMAIL_SCOPE]})
    return resp["access_token"]

def gmail_get(path: str, params: dict | None = None) -> dict:
    """GET request to Gmail API with bearer token."""
    token = get_token()
    resp = httpx.get(
        f"{GMAIL_BASE}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()
```

### Pattern 2: Subcommand CLI with argparse
**What:** argparse with `add_subparsers()` routing to handler functions.
**When to use:** Skills with multiple operations (Gmail has 4 subcommands).
**Example:**
```python
# Source: established pattern from claws-transcribe, extended with subparsers

import argparse

def main():
    parser = argparse.ArgumentParser(prog="claws-gmail", description="Gmail skill")
    subs = parser.add_subparsers(dest="command", required=True)

    # inbox
    inbox_p = subs.add_parser("inbox", help="List inbox messages")
    inbox_p.add_argument("--max", type=int, default=10, help="Max messages")

    # read
    read_p = subs.add_parser("read", help="Read a message")
    read_p.add_argument("id", help="Message ID")

    # send
    send_p = subs.add_parser("send", help="Send an email")
    send_p.add_argument("--to", required=True, help="Recipient")
    send_p.add_argument("--subject", required=True, help="Subject")
    send_p.add_argument("--body", help="Message body")
    send_p.add_argument("--cc", help="CC recipients")
    send_p.add_argument("--bcc", help="BCC recipients")

    # search
    search_p = subs.add_parser("search", help="Search messages")
    search_p.add_argument("query", help="Gmail search query")
    search_p.add_argument("--max", type=int, default=10, help="Max results")

    args = parser.parse_args()
    # dispatch to handler...
```

### Pattern 3: MIME Payload Tree-Walking
**What:** Gmail `format=full` returns nested `payload.parts[]` where each part may itself contain `parts[]`. Must recursively find `text/plain`.
**When to use:** The `read` subcommand for extracting message body.
**Example:**
```python
# Source: Gmail API reference - Message.payload structure

import base64

def extract_body(payload: dict) -> str:
    """Extract plain-text body from Gmail MIME payload."""
    # Simple message (no parts)
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    # Multipart: walk parts tree
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        # Recursive for nested multipart
        if part.get("parts"):
            body = extract_body(part)
            if body:
                return body

    return ""  # No text/plain found; caller should fall back to snippet
```

### Anti-Patterns to Avoid
- **Using `result()` with a list:** `result()` only accepts `str | dict`. Passing a list will not serialize correctly. Wrap list outputs: `result({"messages": [...], "count": N})`.
- **Calling `messages.get` with `format=full` during listing:** Burns 5 quota units per message instead of using `format=metadata` which costs less. Use `format=metadata` with `metadataHeaders` for inbox/search, `format=full` only for `read`.
- **Hand-building RFC 2822 messages as strings:** Use `email.mime.text.MIMEText` from stdlib. It handles encoding, required headers, line wrapping correctly.
- **Standard base64 for send:** Must use `urlsafe_b64encode` with `=` padding stripped. Regular `b64encode` produces `+/` characters that Gmail rejects.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RFC 2822 message construction | String concatenation of headers + body | `email.mime.text.MIMEText` + `email.mime.multipart.MIMEMultipart` (stdlib) | Non-ASCII subjects need RFC 2047 encoding; line length limits; header folding |
| base64url encoding | Custom character replacement | `base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")` | One-liner, well-tested, no edge cases |
| URL encoding of Gmail search queries | Manual `+` and `%20` replacement | httpx `params={"q": query}` parameter | httpx handles URL encoding automatically |
| Gmail header extraction | Manual dict scanning | Helper function once, reuse everywhere | Headers are `[{"name": "From", "value": "..."}]` format, need case-insensitive lookup |

**Key insight:** The Gmail API surface is small (4 endpoints) but the data transformation (MIME parsing, header extraction, base64url encoding) is where complexity lives. Use stdlib for MIME and be meticulous about base64url vs base64.

## Common Pitfalls

### Pitfall 1: base64url vs base64
**What goes wrong:** `messages.send` returns `400 Invalid Message` because the `raw` field uses standard base64 (`+/=`) instead of base64url (`-_` no padding).
**Why it happens:** Python's `b64encode()` and `urlsafe_b64encode()` differ by one function name. Padding `=` must also be stripped.
**How to avoid:** Write and unit-test a dedicated `encode_raw()` helper. Test that output contains no `+`, `/`, or `=`.
**Warning signs:** Send fails with 400 but all other operations work.

### Pitfall 2: messages.list returns IDs only
**What goes wrong:** Developer assumes `messages.list` returns full message details. It returns only `{"id": "...", "threadId": "..."}` per message.
**Why it happens:** Gmail API splits listing from fetching for efficiency. You must call `messages.get` for each message ID to get headers/body.
**How to avoid:** For inbox/search: call `messages.list` for IDs, then batch `messages.get` with `format=metadata&metadataHeaders=From,Subject,Date` for each. For read: single `messages.get` with `format=full`.
**Warning signs:** Inbox output shows only IDs with no subject/sender information.

### Pitfall 3: result() only accepts str or dict
**What goes wrong:** Calling `result([msg1, msg2, ...])` does not produce valid JSON output because `result()` checks `isinstance(data, dict)` and falls through to `print(data)` which produces Python repr, not JSON.
**Why it happens:** `result()` was designed for single-value outputs. Gmail list operations return multiple items.
**How to avoid:** Always wrap list outputs in a dict: `result({"messages": messages, "result_count": len(messages)})`.
**Warning signs:** Output contains Python repr syntax (`[{'id': ...}]`) instead of JSON (`[{"id": ...}]`).

### Pitfall 4: Gmail API error responses are not httpx-friendly
**What goes wrong:** `resp.raise_for_status()` throws `httpx.HTTPStatusError` with the raw response body, which contains a nested Google error JSON structure that is not user-readable.
**Why it happens:** Google returns `{"error": {"code": 404, "message": "...", "errors": [...]}}`. The httpx exception message includes the full response body as a string but does not parse it.
**How to avoid:** Catch `httpx.HTTPStatusError`, parse the response JSON, extract the human-readable `error.message` field, and pass it to `fail()` or `crash()` with context.
**Warning signs:** Error output shows raw JSON blobs instead of actionable messages.

### Pitfall 5: Empty search results
**What goes wrong:** `messages.list` with no matches returns `{}` (no `messages` key), not `{"messages": []}`. Code that does `resp["messages"]` throws `KeyError`.
**Why it happens:** Gmail API omits the `messages` key entirely when there are zero results.
**How to avoid:** Use `resp.get("messages", [])` everywhere.
**Warning signs:** `KeyError: 'messages'` when searching for terms that match nothing.

### Pitfall 6: MIME body in nested multipart
**What goes wrong:** Simple test emails have `text/plain` at `payload.body.data`. Real-world emails from Gmail, newsletters, and forwarded messages have deeply nested `multipart/mixed` > `multipart/alternative` > `text/plain` structures.
**Why it happens:** MIME is a tree, not a flat list. The `text/plain` part can be 2-3 levels deep.
**How to avoid:** Recursive tree-walking function that searches all levels. Fall back to `snippet` field (~200 chars, always present) when no `text/plain` found.
**Warning signs:** Works for test emails but returns empty body for real-world emails.

## Code Examples

### Token Acquisition
```python
# Source: auth server API (servers/google-auth/src/google_auth_server/app.py)
from claws_common.client import ClawsClient

AUTH_PORT = 8301
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"

def get_access_token() -> str:
    """Get Gmail access token from auth server."""
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    resp = client.post_json("/token", {"scopes": [GMAIL_SCOPE]})
    return resp["access_token"]
```

### Gmail Header Extraction
```python
# Source: Gmail API Message.payload.headers format
def get_header(headers: list[dict], name: str) -> str:
    """Extract header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if h["name"].lower() == name_lower:
            return h["value"]
    return ""
```

### Message Send with base64url
```python
# Source: Gmail API messages.send reference
import base64
from email.mime.text import MIMEText

def build_raw_message(to: str, subject: str, body: str,
                       cc: str | None = None, bcc: str | None = None) -> str:
    """Build base64url-encoded RFC 2822 message for Gmail send API."""
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")
```

### Inbox Listing (two-step fetch)
```python
# Source: Gmail API messages.list + messages.get pattern
import httpx

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

def list_inbox(token: str, max_results: int = 10) -> list[dict]:
    """List inbox messages with metadata."""
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Get message IDs
    resp = httpx.get(
        f"{GMAIL_BASE}/messages",
        params={"q": "in:inbox", "maxResults": max_results},
        headers=headers,
        timeout=30.0,
    )
    resp.raise_for_status()
    message_ids = resp.json().get("messages", [])

    # Step 2: Fetch metadata for each
    messages = []
    for msg_ref in message_ids:
        detail = httpx.get(
            f"{GMAIL_BASE}/messages/{msg_ref['id']}",
            params={
                "format": "metadata",
                "metadataHeaders": ["From", "Subject", "Date"],
            },
            headers=headers,
            timeout=30.0,
        )
        detail.raise_for_status()
        data = detail.json()
        hdrs = data.get("payload", {}).get("headers", [])
        messages.append({
            "id": data["id"],
            "thread_id": data["threadId"],
            "from": get_header(hdrs, "From"),
            "subject": get_header(hdrs, "Subject"),
            "date": get_header(hdrs, "Date"),
            "snippet": data.get("snippet", ""),
        })
    return messages
```

### Error Handling Pattern
```python
# Source: established pattern from claws-transcribe + Gmail API error structure
import httpx
from claws_common.output import fail, crash

def handle_gmail_error(e: httpx.HTTPStatusError) -> None:
    """Translate Gmail API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash("Gmail authentication failed. Token may be expired or delegation misconfigured.")
    elif status == 403:
        fail(f"Gmail access denied: {message}")
    elif status == 404:
        fail(f"Message not found: {message}")
    elif status == 429:
        fail("Gmail rate limit exceeded. Try again later.")
    else:
        crash(f"Gmail API error ({status}): {message}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-api-python-client discovery | Direct REST via httpx | Project decision (2026-03) | No heavy dependency; 4 endpoints are simple REST |
| OAuth2 web flow with refresh tokens | Service account + domain-wide delegation | Project decision (2026-03) | No browser interaction; set-once admin config |
| Gmail proxy server on host | Skill calls Gmail API directly | Architecture decision (2026-03) | No unnecessary server; auth server just vends tokens |

**Deprecated/outdated:**
- `google-api-python-client`: Explicitly out of scope per REQUIREMENTS.md. Would pull 15+ transitive dependencies.
- `gmail.readonly` + `gmail.send` separate scopes: Decision to use single `gmail.modify` scope which covers all operations.

## Open Questions

1. **Stdin body reading for send**
   - What we know: `--body` flag for inline, stdin fallback when not a TTY
   - What's unclear: Should there be a max body size limit? What about encoding issues with piped input?
   - Recommendation: Read stdin with `.read()`, no size limit (the agent controls input). Decode as UTF-8 with error handling.

2. **Pagination for inbox/search beyond --max**
   - What we know: Gmail API returns `nextPageToken` for pagination. Default is 10 messages.
   - What's unclear: Should we support fetching more than one page? The agent might want 50+ messages.
   - Recommendation: For v1.1, honor `--max` up to whatever Gmail returns in one page (max 500). Do not implement multi-page pagination yet -- single page with `maxResults` parameter is sufficient.

3. **Rate limiting on parallel messages.get calls**
   - What we know: Inbox listing requires N+1 API calls (1 list + N get). Gmail quota is 250 units/user/sec.
   - What's unclear: Will fetching 10 messages sequentially be fast enough, or do we need async/concurrent fetching?
   - Recommendation: Sequential fetching for v1.1. 10 messages x ~200ms each = ~2 seconds, acceptable for CLI. Optimize later if needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ |
| Config file | Root `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest skills/gmail/tests/ -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GMAIL-01 | List inbox with sender, subject, date, snippet | unit | `uv run pytest skills/gmail/tests/test_gmail.py::test_list_inbox -x` | Wave 0 |
| GMAIL-02 | Read message with plain-text body from MIME | unit | `uv run pytest skills/gmail/tests/test_gmail.py::test_read_message -x` | Wave 0 |
| GMAIL-02 | MIME tree walking for nested multipart | unit | `uv run pytest skills/gmail/tests/test_gmail.py::test_extract_body_nested -x` | Wave 0 |
| GMAIL-03 | Send email with to, subject, body | unit | `uv run pytest skills/gmail/tests/test_gmail.py::test_send_message -x` | Wave 0 |
| GMAIL-03 | base64url encoding (no +, /, =) | unit | `uv run pytest skills/gmail/tests/test_gmail.py::test_encode_raw_message -x` | Wave 0 |
| GMAIL-04 | Search messages with Gmail query | unit | `uv run pytest skills/gmail/tests/test_gmail.py::test_search -x` | Wave 0 |
| GMAIL-05 | All outputs use result() as dicts | unit | `uv run pytest skills/gmail/tests/test_cli.py -x` | Wave 0 |
| GMAIL-06 | Entry point discovery as `claws gmail` | unit | `uv run pytest skills/gmail/tests/test_cli.py::test_entry_point -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest skills/gmail/tests/ -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `skills/gmail/tests/__init__.py` -- package init
- [ ] `skills/gmail/tests/test_cli.py` -- CLI subcommand routing, output verification
- [ ] `skills/gmail/tests/test_gmail.py` -- Gmail API client, MIME parsing, base64url encoding
- [ ] `skills/gmail/pyproject.toml` -- package definition with entry point
- [ ] `skills/gmail/src/claws_gmail/__init__.py` -- package init
- [ ] Root `pyproject.toml` update -- add `claws-gmail` to workspace dev deps and uv sources

## Sources

### Primary (HIGH confidence)
- Existing codebase: `skills/transcribe/` (CLI pattern), `servers/google-auth/` (auth server API), `common/src/claws_common/` (client + output)
- `.planning/research/FEATURES.md` -- Gmail API endpoints, MIME payload structure, search syntax
- `.planning/research/ARCHITECTURE.md` -- Two-tier HTTP pattern, project structure, data flows
- `.planning/research/PITFALLS.md` -- base64url, MIME parsing, empty results, error handling
- `.planning/phases/05-gmail-skill/05-CONTEXT.md` -- User decisions on output format, send behavior, auth flow

### Secondary (MEDIUM confidence)
- Gmail API REST Reference (https://developers.google.com/workspace/gmail/api/reference/rest) -- endpoint documentation
- Gmail API Search Guide (https://developers.google.com/workspace/gmail/api/guides/filtering) -- query syntax

### Tertiary (LOW confidence)
- None -- all findings verified against codebase and prior research documents

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed; all are stdlib or already in workspace
- Architecture: HIGH -- follows established patterns with one well-understood extension (two-tier HTTP)
- Pitfalls: HIGH -- thoroughly documented in prior research phase; base64url and MIME parsing are well-known issues
- Test patterns: HIGH -- directly mirrors existing test structure from transcribe and auth server

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain; Gmail API v1 is mature)
