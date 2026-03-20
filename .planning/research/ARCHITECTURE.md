# Architecture Research

**Domain:** Google auth server + Gmail skill integration into existing claws monorepo
**Researched:** 2026-03-19
**Confidence:** HIGH

## System Overview

```
Container (Docker, no GPU)                Host (Mac mini, Apple Silicon)
┌──────────────────────────────┐          ┌────────────────────────────────┐
│                              │          │                                │
│  claws gmail read            │──HTTP──> │  google-auth-server :8301      │
│  claws gmail send            │          │  (FastAPI, token vending)      │
│  claws gmail search          │          │                                │
│  (claws-gmail CLI)           │          │  Holds: service-account.json   │
│                              │          │  Issues: short-lived tokens    │
│  Uses ClawsClient from       │          │  Managed by launchd            │
│  claws-common                │          └──────────┬─────────────────────┘
│                              │                     │
│                              │                     │ JWT -> access token
│                              │                     v
│                              │          ┌────────────────────────────────┐
│                              │──HTTPS─> │  Gmail REST API                │
│                              │          │  gmail.googleapis.com          │
│                              │          └────────────────────────────────┘
└──────────────────────────────┘
```

## Key Architectural Decision: Where Gmail API Calls Happen

Three options were evaluated:

**Option A: Auth server on host, Gmail calls direct from container -- REJECTED.** Breaks the established pattern ("every skill proxies through host servers") and means the container makes external API calls with no host involvement beyond auth.

**Option B: Full Gmail proxy server on host -- REJECTED.** A dedicated gmail-server would proxy all Gmail API calls. Adds an unnecessary server since Gmail needs no host resources (no GPU, no local files, no macOS APIs). Pure HTTP proxying with no added value.

**Option C: Auth server as token vending machine, skill calls Gmail directly -- CHOSEN.** The auth server's only job is vending access tokens. The Gmail skill gets a token from the auth server on the host, then calls `gmail.googleapis.com` directly from the container.

**Rationale for Option C:**

1. Gmail API needs no host resources -- no GPU, no local files, no macOS APIs
2. The auth server centralizes the secret -- service account JSON key never leaves the host
3. The pattern generalizes -- future Google skills (Calendar, Drive) reuse the same auth server with zero changes
4. Matches the architecture spirit -- the host holds secrets and heavy resources; the container runs logic

This is a deliberate evolution of the v1.0 pattern. Instead of "thin CLI -> host server -> result", it becomes "thin CLI -> host auth server for token -> external API -> result". The host still owns the sensitive material. The container still has no secrets.

## New Components

### 1. google-auth-server (NEW -- `servers/google-auth/`)

FastAPI server on the host. Holds the service account key file, mints access tokens via domain-wide delegation, caches them until near-expiry.

| Attribute | Value |
|-----------|-------|
| Port | 8301 |
| Package name | `google-auth-server` |
| Import name | `google_auth_server` |
| Dependencies | `fastapi`, `uvicorn`, `google-auth` |
| Key file location | Configured via env var `GOOGLE_SERVICE_ACCOUNT_KEY` |
| Delegation subject | Configured via env var `GOOGLE_DELEGATED_USER` |

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/token` | Returns `{"access_token": "...", "expires_in": N}` for requested scopes |
| GET | `/health` | Standard health check |

**Query parameters for /token:**

| Param | Required | Description |
|-------|----------|-------------|
| `scopes` | Yes | Comma-separated OAuth scopes (e.g., `https://www.googleapis.com/auth/gmail.modify`) |

**Token caching strategy:** Cache tokens in memory keyed by `(subject, frozenset(scopes))`. Return cached token if it has >60 seconds remaining. Otherwise refresh via `credentials.refresh()`. The `google-auth` library handles JWT signing and Google's token endpoint exchange internally.

**Implementation sketch:**

```python
from google.oauth2 import service_account
import google.auth.transport.requests

# At startup: load base credentials from service account key file
credentials_base = service_account.Credentials.from_service_account_file(key_path)

# Per-request token vending (with caching layer on top):
def get_token(scopes: list[str], subject: str) -> dict:
    creds = credentials_base.with_subject(subject).with_scopes(scopes)
    creds.refresh(google.auth.transport.requests.Request())
    return {"access_token": creds.token, "expires_in": seconds_remaining(creds.expiry)}
```

### 2. claws-gmail (NEW -- `skills/gmail/`)

Thin CLI skill. Gets a token from the auth server, calls Gmail REST API directly with httpx.

| Attribute | Value |
|-----------|-------|
| Package name | `claws-gmail` |
| Import name | `claws_gmail` |
| Dependencies | `claws-common` (for ClawsClient, output helpers) |
| Entry point | `gmail = "claws_gmail.cli:main"` in `claws.skills` group |

**Subcommands:**

| Command | Gmail API Endpoint | Description |
|---------|--------------------|-------------|
| `claws gmail read <message_id>` | `GET /gmail/v1/users/me/messages/{id}` | Read a specific email |
| `claws gmail send --to --subject --body` | `POST /gmail/v1/users/me/messages/send` | Send an email |
| `claws gmail search <query>` | `GET /gmail/v1/users/me/messages?q=...` | Search inbox |

**How the skill gets a token:**

```python
# Use ClawsClient to talk to google-auth-server on host
auth_client = ClawsClient(service="google-auth", port=8301)
token_response = auth_client.get("/token?scopes=https://www.googleapis.com/auth/gmail.modify")
access_token = token_response["access_token"]
```

**How the skill calls Gmail API:**

```python
# Direct httpx call to Gmail (not through ClawsClient -- different base URL and auth model)
import httpx

headers = {"Authorization": f"Bearer {access_token}"}
resp = httpx.get(
    f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={query}",
    headers=headers,
    timeout=30.0,
)
```

The Gmail API calls use raw httpx, not ClawsClient. ClawsClient is for host-server communication (same base URL pattern, same error semantics). Gmail API is an external service with its own base URL, auth model, and error structure. A small helper class within `claws_gmail` (e.g., `gmail.py`) should handle Gmail-specific HTTP calls, error mapping, and response parsing.

### 3. Launchd plist (NEW -- `launchd/com.lobsterclaws.google-auth.plist`)

Follows the exact same pattern as the whisper plist: uvicorn, 0.0.0.0 binding, KeepAlive, RunAtLoad. Key differences: port 8301, env vars for key file path and delegated user email.

### 4. Modifications to Existing Components

| Component | Change Required |
|-----------|----------------|
| `claws-common` | **NONE.** ClawsClient already supports GET requests. No new methods needed. |
| `claws-cli` | **NONE.** Discovers gmail skill automatically via entry points. |
| `root pyproject.toml` | **MINOR.** Add `claws-gmail` and `google-auth-server` to dev dependencies and UV sources. |

## Component Responsibilities

| Component | Responsibility | Status |
|-----------|---------------|--------|
| google-auth-server | Hold service account key, vend short-lived access tokens, cache tokens | NEW |
| claws-gmail CLI | Parse args, get token from auth server, call Gmail API, format output | NEW |
| claws-common | Shared client/output helpers | UNCHANGED |
| claws-cli | Entry-point discovery and routing | UNCHANGED |
| launchd plist | Auto-start google-auth-server | NEW |

## Data Flow

### Gmail Read Flow

```
User: claws gmail read <id>
  |
  v
claws-gmail CLI (container)
  |
  |-- 1. ClawsClient.get("/token?scopes=gmail.modify")
  |       --> google-auth-server (host:8301)
  |       <-- {"access_token": "ya29...", "expires_in": 3580}
  |
  |-- 2. httpx.get("https://gmail.googleapis.com/gmail/v1/users/me/messages/<id>",
  |       headers={"Authorization": "Bearer ya29..."})
  |       <-- {message JSON with payload, headers, body}
  |
  |-- 3. Parse message: decode body, extract headers (From, To, Subject, Date)
  |
  |-- 4. result(formatted_message)  --> stdout
```

### Gmail Send Flow

```
User: claws gmail send --to user@example.com --subject "Hi" --body "Hello"
  |
  v
claws-gmail CLI (container)
  |
  |-- 1. Get token (same as read flow)
  |
  |-- 2. Build RFC 2822 message, base64url encode it
  |
  |-- 3. httpx.post(".../messages/send",
  |       json={"raw": base64_encoded_message},
  |       headers={"Authorization": "Bearer ya29..."})
  |       <-- {"id": "...", "threadId": "...", "labelIds": [...]}
  |
  |-- 4. result({"id": ..., "threadId": ...})  --> stdout
```

### Gmail Search Flow

```
User: claws gmail search "from:boss subject:urgent"
  |
  v
claws-gmail CLI (container)
  |
  |-- 1. Get token (same as read flow)
  |
  |-- 2. httpx.get(".../messages?q=from:boss+subject:urgent&maxResults=10")
  |       <-- {"messages": [{"id": "...", "threadId": "..."}, ...]}
  |
  |-- 3. For each message ID: GET .../messages/{id}?format=metadata
  |       (fetches headers: From, Subject, Date for display)
  |
  |-- 4. result(formatted_list)  --> stdout
```

### Error Flow

```
claws-gmail CLI
  |
  ├── Auth server unreachable → crash("Cannot connect to google-auth server...")
  |                              exit code: 2
  |
  ├── Auth server returns error → crash("Token error: ...")
  |   (bad key, bad subject)     exit code: 2
  |
  ├── Gmail API 401 → fail("Authentication failed. Token may be expired.")
  |                    exit code: 1
  |
  ├── Gmail API 404 → fail("Message not found: <id>")
  |                    exit code: 1
  |
  ├── Gmail API 429 → fail("Gmail rate limit exceeded. Try again later.")
  |                    exit code: 1
  |
  └── Success → result(data) → stdout, exit code: 0
```

## Project Structure (New Files Only)

```
lobster_claws/
├── servers/
│   └── google-auth/                        # NEW
│       ├── pyproject.toml                  # depends on: google-auth, fastapi, uvicorn
│       ├── src/google_auth_server/
│       │   ├── __init__.py
│       │   └── app.py                      # FastAPI app: /token, /health
│       └── tests/
│           └── test_app.py                 # Mock google.oauth2 credentials
├── skills/
│   └── gmail/                              # NEW
│       ├── pyproject.toml                  # depends on: claws-common
│       ├── src/claws_gmail/
│       │   ├── __init__.py
│       │   ├── cli.py                      # argparse: read, send, search subcommands
│       │   └── gmail.py                    # Gmail API wrapper (httpx + bearer token)
│       └── tests/
│           ├── test_cli.py                 # Mock auth client + Gmail API calls
│           └── test_gmail.py               # Mock httpx calls to Gmail API
├── launchd/
│   └── com.lobsterclaws.google-auth.plist  # NEW
└── pyproject.toml                          # MODIFIED: add new workspace members
```

### Structure Rationale

- **`gmail.py` separate from `cli.py`:** Isolates Gmail API logic (message formatting, base64 encoding, pagination) from CLI argument parsing. The transcribe skill was simple enough for a single file; Gmail has enough API surface to warrant separation.
- **`google_auth_server` not `claws_google_auth`:** Servers use their own naming convention (e.g., `whisper_server`), not the `claws_*` pattern which is reserved for skills.
- **No `claws-common` changes:** The existing `ClawsClient.get()` method is sufficient for the `/token` endpoint call. No new HTTP methods needed.

## Architectural Patterns

### Pattern 1: Token Vending Machine

**What:** The auth server's only job is issuing access tokens. It holds no business logic. Skills use the tokens however they need.

**When to use:** When multiple skills need Google API access (Gmail now, Calendar later, Drive later).

**Trade-offs:**
- Pro: Single credential storage point, token caching shared across skills
- Pro: Adding a new Google skill requires zero auth server changes
- Con: Skills must handle Google API errors themselves (not centralized)
- Con: Container makes outbound HTTPS calls (evolution from v1.0 proxy-only pattern)

### Pattern 2: Scope-per-Request

**What:** The `/token` endpoint accepts scopes as a query parameter rather than having pre-configured scope sets per skill.

**When to use:** Per the "open token model" decision in PROJECT.md -- internal network, trusted skills only.

**Trade-offs:**
- Pro: Zero auth server changes when adding new skills or expanding scope needs
- Con: Any skill can request any scope (acceptable per project decision; internal network only)

### Pattern 3: Two-Tier HTTP in a Single Skill

**What:** The Gmail skill makes two different kinds of HTTP calls: (1) ClawsClient to the auth server on the host, (2) raw httpx to the Gmail REST API externally.

**When to use:** When a skill needs both host-server resources (auth token) and external API access.

**Trade-offs:**
- Pro: Keeps ClawsClient focused on host-server communication with its service-aware errors
- Pro: Gmail API errors get domain-specific handling (quota, rate limits, message formatting)
- Con: More complex than the pure v1.0 pattern (one HTTP call type per skill)

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Google OAuth2 Token Endpoint | `google-auth` library handles JWT -> access token exchange | Outbound from host only; service account key stays on host |
| Gmail REST API v1 | Direct HTTPS from container with bearer token | Base URL: `https://gmail.googleapis.com/gmail/v1/` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| claws-gmail -> google-auth-server | ClawsClient HTTP GET (existing pattern) | Port 8301, GET /token?scopes=... |
| claws-gmail -> Gmail API | Raw httpx HTTPS with bearer token | Not through ClawsClient |
| google-auth-server -> Google OAuth2 | `google-auth` library (outbound from host) | JWT-based, no user interaction |

### New Environment Variables

| Variable | Set Where | Purpose | Example |
|----------|-----------|---------|---------|
| `GOOGLE_SERVICE_ACCOUNT_KEY` | launchd plist env | Path to JSON key file on host | `/Users/little-dank/.config/lobsterclaws/service-account.json` |
| `GOOGLE_DELEGATED_USER` | launchd plist env | Workspace user email to impersonate | `agent@yourdomain.com` |

## Anti-Patterns

### Anti-Pattern 1: Service Account Key in Container

**What people do:** Mount or bake the service account JSON key into the Docker image/container.
**Why it's wrong:** The key grants domain-wide access to all Workspace data. If the container is compromised, the attacker has full Google Workspace access. The key is a long-lived credential.
**Do this instead:** Keep the key on the host only. The auth server vends short-lived (1-hour) access tokens. If a token leaks, it expires automatically.

### Anti-Pattern 2: Using google-api-python-client for Gmail

**What people do:** Install the full `google-api-python-client` (~20MB, discovery-based) to call Gmail.
**Why it's wrong:** Adds heavy dependencies for 3 HTTP endpoints. The discovery document fetch adds startup latency. It pulls in `google-auth-httplib2` which conflicts with the httpx-based approach used throughout the codebase.
**Do this instead:** Call the Gmail REST API directly with httpx + bearer token. The endpoints are stable and well-documented. This matches the existing pattern of using httpx for all HTTP.

### Anti-Pattern 3: Per-Skill Auth Servers

**What people do:** Create a separate auth+proxy server for each Google service (gmail-server, calendar-server).
**Why it's wrong:** Duplicates credential management, token caching, and delegation logic across servers.
**Do this instead:** One auth server that vends tokens for any scope. Skills handle API calls themselves.

### Anti-Pattern 4: Hardcoding Scopes in the Auth Server

**What people do:** Configure allowed scopes in the auth server, requiring server changes for each new skill.
**Why it's wrong:** Creates coupling between the auth server and individual skills. Every new Google skill requires an auth server change and redeployment.
**Do this instead:** Accept scopes as a request parameter (per the "open token model" decision).

## Build Order (Dependency-Driven)

```
Phase 1: google-auth-server
    │     (standalone; no dependency on Gmail skill)
    │     Order: health endpoint -> token endpoint with mocked creds ->
    │            real credential loading -> token caching
    │
    └──> Phase 2: claws-gmail
              │   (depends on auth server for token vending)
              │   Order: CLI arg parsing skeleton ->
              │          auth token acquisition via ClawsClient ->
              │          Gmail API wrapper (gmail.py) ->
              │          integration: CLI -> auth -> Gmail -> output
              │
              └──> Phase 3: launchd plist + root pyproject.toml updates
                        (depends on packages existing)
```

**Critical path:** google-auth-server must be built and testable first. The Gmail skill depends on being able to get tokens. The launchd plist and workspace config are mechanical tasks that come last.

## Scaling Considerations

Not a traditional scaling concern (single user, single host), but relevant patterns:

| Concern | At 1 Google skill | At 5 Google skills |
|---------|--------------------|--------------------|
| Token requests per command | 1 | 1 (same auth server, different scopes) |
| Token caching benefit | Minimal | High (multiple skills share cached tokens for overlapping scopes) |
| Auth server changes needed | N/A | Zero (scope-per-request design) |
| Gmail API quota | 250 quota units/user/sec | Shared per-user quota across skills |

## Sources

- [Gmail API REST Reference](https://developers.google.com/workspace/gmail/api/reference/rest) -- endpoint documentation (HIGH confidence)
- [google.oauth2.service_account docs](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.service_account.html) -- Python credential management (HIGH confidence)
- [Domain-wide delegation setup](https://support.google.com/a/answer/162106?hl=en) -- Google Admin console configuration (HIGH confidence)
- [OAuth 2.0 Server to Server](https://developers.google.com/identity/protocols/oauth2/service-account) -- JWT-based auth flow (HIGH confidence)
- Existing codebase: `common/src/claws_common/client.py`, `servers/whisper/src/whisper_server/app.py`, `skills/transcribe/src/claws_transcribe/cli.py` (HIGH confidence)

---
*Architecture research for: Google auth + Gmail integration into lobster_claws*
*Researched: 2026-03-19*
