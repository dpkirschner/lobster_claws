# Phase 4: Google Auth Server - Research

**Researched:** 2026-03-19
**Domain:** Google service account token vending server + ClawsClient extensions
**Confidence:** HIGH

## Summary

Phase 4 builds a FastAPI token vending server on the Mac mini host that loads a Google service account JSON key, mints short-lived access tokens via domain-wide delegation, caches them, and serves them to skills in Docker containers. It also extends ClawsClient with `post_json()` and `get()` with query parameter support. The auth server follows the exact same structural pattern as the existing whisper-server (FastAPI + uvicorn + lifespan + launchd plist) but with a critical security difference: it MUST bind to `127.0.0.1` only, not `0.0.0.0`.

The `google-auth` library (v2.49.1) handles all credential management, JWT signing, and token exchange. The `requests` library is required solely as a transport adapter for `google-auth`'s `credentials.refresh()` method -- there is no httpx transport available. Token caching is core server logic, not an optimization: without it, every CLI invocation adds 200-500ms of latency for a Google token endpoint round-trip.

**Primary recommendation:** Build in order: (1) ClawsClient extensions in claws-common, (2) auth server package with health + token endpoints, (3) launchd plist. Mock `google.oauth2.service_account.Credentials` in all tests -- no real Google calls in the test suite.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Token API contract:** `POST /token` with JSON body `{"scopes": [...]}`
- **Health + diagnostics startup:** Full end-to-end check -- mint a real token on startup to verify key file + delegation are correctly configured
- **`/health` response:** Include status, service name, impersonated subject, and verified scopes
- **Error format:** HTTP status codes -- 400 for bad requests (missing scopes), 503 for Google unreachable, 500 for key/delegation issues. Skills use existing ClawsClient error handling.
- **Retry policy:** One retry with short backoff for transient Google errors (network blips, 500s). Fail after that.
- **Auth server bind:** MUST bind `127.0.0.1` (not `0.0.0.0`)
- **Health detail:** More detail than whisper-server -- include subject being impersonated and what scopes were verified at startup

### Claude's Discretion
- Token response shape details (metadata beyond access_token + expires_in)
- Scope format (short aliases vs full URLs)
- Token vending vs API proxy architecture (token vending is the leaning)
- Startup failure behavior (fail fast vs degraded start)
- Error response detail level
- Token cache implementation (TTL, eviction strategy)
- Configuration approach (env vars vs config file for key path and subject)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | ClawsClient supports POST with JSON body (`post_json` method) | Extend existing `ClawsClient` in `common/src/claws_common/client.py` following `post_file()` error-handling pattern. Use `httpx.post(url, json=data)`. |
| CLI-02 | ClawsClient supports GET with query parameters | Extend existing `get()` method to accept optional `params` dict, passed to `httpx.get(url, params=params)`. |
| AUTH-01 | Auth server loads service account JSON key from configured path | Use `service_account.Credentials.from_service_account_file(path)` from `google-auth`. Path from env var `GOOGLE_SERVICE_ACCOUNT_KEY`. |
| AUTH-02 | Auth server mints access tokens using domain-wide delegation with configurable subject | Use `credentials.with_subject(subject).with_scopes(scopes)` then `credentials.refresh(Request())`. Subject from env var `GOOGLE_DELEGATED_USER`. |
| AUTH-03 | Auth server caches tokens and refreshes before expiry (~55 min TTL) | In-memory dict keyed by `frozenset(scopes)` (subject is server-wide config). Return cached if >60s remaining. |
| AUTH-04 | Auth server accepts arbitrary scope sets via request parameter | `POST /token` accepts JSON body `{"scopes": ["..."]}`. No hardcoded scope whitelist. |
| AUTH-05 | Auth server exposes GET /health endpoint | FastAPI `@app.get("/health")` returning status, service name, subject, verified scopes. |
| AUTH-06 | Auth server binds to 127.0.0.1:8301 (not 0.0.0.0) | uvicorn `--host 127.0.0.1 --port 8301` in both `main()` and launchd plist. |
| AUTH-07 | Auth server managed by launchd plist with auto-start and restart | Copy whisper plist pattern: RunAtLoad + KeepAlive, port 8301, host 127.0.0.1, env vars for key path + subject. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-auth | >=2.49 (current: 2.49.1) | Service account credentials, JWT signing, domain-wide delegation | Official Google library. Provides `Credentials.from_service_account_file()`, `.with_subject()`, `.with_scopes()`, `.refresh()`. No alternative exists. |
| requests | >=2.32 | HTTP transport for google-auth token refresh | `google.auth.transport.requests.Request` is the standard transport for `credentials.refresh()`. google-auth has NO httpx transport. Only used in auth server, never in container. |
| FastAPI | >=0.135 | Auth server framework | Same as whisper-server. Already in workspace. |
| uvicorn | >=0.42 | ASGI server | Same as whisper-server. Already in workspace. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.28 | Already used by ClawsClient | No new dependency -- extending existing client |
| pytest | >=9.0 | Test framework | Already in workspace dev deps |
| pytest-httpx | >=0.36 | Mock httpx calls in ClawsClient tests | Already in workspace dev deps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| google-auth + requests | google-api-python-client | Pulls 15MB+ transitive deps (protobuf, httplib2, uritemplate). Overkill for token minting. |
| requests (transport) | aiohttp (async transport) | Adds complexity for no benefit -- single-user, sequential requests. |
| In-memory token cache | Redis/disk cache | Over-engineering for single-process, single-user server. |

**Installation (auth server pyproject.toml):**
```toml
dependencies = [
    "fastapi>=0.135",
    "uvicorn>=0.42",
    "google-auth>=2.49",
    "requests>=2.32",
]
```

**Version verification:** google-auth 2.49.1 confirmed on PyPI (2026-03-12). requests 2.32.x confirmed current. FastAPI and uvicorn already in workspace at compatible versions.

## Architecture Patterns

### Recommended Project Structure
```
servers/google-auth/
    pyproject.toml
    src/google_auth_server/
        __init__.py
        app.py              # FastAPI app: POST /token, GET /health, lifespan
    tests/
        __init__.py
        test_app.py          # Mock google.oauth2 credentials
launchd/
    com.lobsterclaws.google-auth.plist
common/src/claws_common/
    client.py               # MODIFIED: add post_json() and get() with params
common/tests/
    test_client.py           # MODIFIED: add tests for new methods
```

### Pattern 1: Token Vending Machine
**What:** Auth server's only job is issuing access tokens. It holds no business logic. Skills use the tokens to call Google APIs directly.
**When to use:** This phase and all future Google API skills.
**Example:**
```python
# Source: google-auth official docs + architecture research
from google.oauth2 import service_account
import google.auth.transport.requests

# At startup
base_creds = service_account.Credentials.from_service_account_file(
    key_path,
    subject=delegated_user,
)

# Per-request (with caching layer on top)
def mint_token(scopes: list[str]) -> dict:
    creds = base_creds.with_scopes(scopes)
    creds.refresh(google.auth.transport.requests.Request())
    return {
        "access_token": creds.token,
        "expires_in": int((creds.expiry - datetime.utcnow()).total_seconds()),
    }
```

### Pattern 2: Lifespan Startup Validation
**What:** Use FastAPI lifespan to load credentials and validate delegation end-to-end before accepting requests.
**When to use:** Auth server startup.
**Example:**
```python
# Source: whisper-server pattern + CONTEXT.md decision
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load key file
    creds = service_account.Credentials.from_service_account_file(key_path, subject=subject)
    # Mint a real token to validate delegation works
    scoped = creds.with_scopes(["https://www.googleapis.com/auth/gmail.readonly"])
    scoped.refresh(google.auth.transport.requests.Request())
    # Store on app.state for request handlers
    app.state.base_creds = creds
    app.state.token_cache = {}
    yield
```

### Pattern 3: ClawsClient Extension
**What:** Add `post_json()` and update `get()` to accept query params, following the exact same error-handling pattern as existing methods.
**When to use:** Before building auth server or any skill that consumes it.
**Example:**
```python
# Source: existing client.py pattern
def post_json(self, path: str, data: dict) -> dict:
    url = f"{self.base_url}{path}"
    try:
        resp = httpx.post(url, json=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise ConnectionError(
            f"Cannot connect to {self.service} server at {url}. "
            f"Is the server running? Check: curl {self.base_url}/health"
        )
    except httpx.TimeoutException:
        raise TimeoutError(
            f"Request to {self.service} timed out after {self.timeout}s ({url})"
        )

def get(self, path: str, params: dict | None = None) -> dict:
    url = f"{self.base_url}{path}"
    try:
        resp = httpx.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise ConnectionError(...)
    except httpx.TimeoutException:
        raise TimeoutError(...)
```

### Anti-Patterns to Avoid
- **Binding auth server to 0.0.0.0:** Exposes token minting to entire network. MUST use 127.0.0.1.
- **Service account key in container:** Key never leaves the host. Auth server is the sole consumer.
- **Hardcoding scopes in auth server:** Accept scopes per-request. No whitelist.
- **Hand-rolling JWT construction:** Use `google.oauth2.service_account.Credentials` for all JWT creation and signing.
- **Logging access tokens:** Log metadata only (subject, scopes, expiry), never token values.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT signing for Google OAuth | PyJWT + manual claims | `google.oauth2.service_account.Credentials` | Google-specific claim format, RS256 with service account private key, token exchange endpoint. Library handles all of it. |
| Token exchange with Google | Manual HTTP POST to oauth2.googleapis.com | `credentials.refresh(Request())` | Handles nonce, timestamp, retry, response parsing. |
| HTTP transport for refresh | Custom httpx adapter | `google.auth.transport.requests.Request()` | google-auth only ships transports for requests and aiohttp. No httpx transport exists. |
| Service-aware HTTP errors | Raw try/except in each skill | `ClawsClient` with `post_json()` / `get()` | Centralized error wrapping with service name context. |

**Key insight:** The `google-auth` library is a thin wrapper around JWT + HTTP -- but the claim format, signing algorithm, and token endpoint protocol are Google-specific with edge cases that a custom implementation would get wrong.

## Common Pitfalls

### Pitfall 1: Missing `subject` in delegated credentials
**What goes wrong:** Credentials created without `with_subject()`. Gmail API calls return `400 Precondition check failed` or `403 Forbidden` with no indication that the fix is adding a subject.
**Why it happens:** Developers assume service accounts can access Gmail directly. They cannot -- Gmail has no concept of a service account mailbox. Every call must impersonate a real domain user.
**How to avoid:** Configure subject via `GOOGLE_DELEGATED_USER` env var. Apply it at credential creation time: `Credentials.from_service_account_file(path, subject=user)`. The startup health check validates delegation works end-to-end.
**Warning signs:** Token generation succeeds but downstream API calls fail with 400/403.

### Pitfall 2: Two-console delegation setup
**What goes wrong:** Code is correct but Gmail calls fail. Developer debugs code for hours when the problem is an admin console configuration step they never performed.
**Why it happens:** Domain-wide delegation requires configuration in TWO admin consoles: (1) GCP Console -- enable delegation on service account, (2) Google Workspace Admin Console -- authorize the service account's Client ID for specific OAuth scope URLs.
**How to avoid:** Startup health check must mint a real token and make a test API call. If it fails, log the exact Admin Console URL and the exact scope strings that need authorization.
**Warning signs:** Auth server starts without errors but all token-consuming API calls fail.

### Pitfall 3: Token caching done wrong
**What goes wrong:** (A) No caching -- 200-500ms latency per CLI call, risk of rate limits. (B) Tokens cached past 3600s lifetime -- 401 Invalid Credentials.
**Why it happens:** google-auth handles refresh automatically when used with google-api-python-client, but this project uses direct token management.
**How to avoid:** Cache in-memory keyed by `frozenset(scopes)`. Set conservative TTL (~3500s, 100s buffer). Return `expires_in` from the endpoint so consumers know token lifetime.
**Warning signs:** Noticeable latency on every `claws` command, or intermittent 401s after ~1 hour.

### Pitfall 4: Auth server bound to 0.0.0.0
**What goes wrong:** Any device on local network can request access tokens for any domain user.
**Why it happens:** Copying the whisper-server bind pattern without considering that auth server is security-sensitive.
**How to avoid:** Bind to `127.0.0.1` only. Docker Desktop for Mac's `host.docker.internal` resolves to host loopback, so container access still works.
**Warning signs:** `lsof -i :8301` showing `*:8301` instead of `localhost:8301`.

### Pitfall 5: ClawsClient `get()` does not support query params
**What goes wrong:** Skills manually construct URLs with query strings, bypassing httpx's parameter encoding and breaking on special characters.
**Why it happens:** Current `get()` only takes a `path` string. No `params` argument.
**How to avoid:** Extend `get()` to accept optional `params: dict | None = None` and pass to `httpx.get(url, params=params)`.
**Warning signs:** Manual string concatenation like `f"/token?scopes={','.join(scopes)}"` in skill code.

## Code Examples

### Token Endpoint Handler
```python
# Source: google-auth docs + CONTEXT.md contract
from fastapi import FastAPI, Request
from pydantic import BaseModel

class TokenRequest(BaseModel):
    scopes: list[str]

@app.post("/token")
async def get_token(req: TokenRequest):
    cache_key = frozenset(req.scopes)
    cached = app.state.token_cache.get(cache_key)
    if cached and cached["expires_at"] > time.time() + 60:
        return {
            "access_token": cached["access_token"],
            "expires_in": int(cached["expires_at"] - time.time()),
        }

    creds = app.state.base_creds.with_scopes(req.scopes)
    creds.refresh(google.auth.transport.requests.Request())

    expires_at = creds.expiry.timestamp()
    app.state.token_cache[cache_key] = {
        "access_token": creds.token,
        "expires_at": expires_at,
    }
    return {
        "access_token": creds.token,
        "expires_in": int(expires_at - time.time()),
    }
```

### Health Endpoint
```python
# Source: CONTEXT.md decision + whisper-server pattern
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "google-auth-server",
        "subject": app.state.delegated_user,
        "verified_scopes": app.state.verified_scopes,
    }
```

### Launchd Plist Structure
```xml
<!-- Source: com.lobsterclaws.whisper.plist pattern -->
<key>ProgramArguments</key>
<array>
    <string>/Users/little-dank/code/lobster_claws/.venv/bin/uvicorn</string>
    <string>google_auth_server.app:app</string>
    <string>--host</string>
    <string>127.0.0.1</string>    <!-- SECURITY: not 0.0.0.0 -->
    <string>--port</string>
    <string>8301</string>
</array>

<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>GOOGLE_SERVICE_ACCOUNT_KEY</key>
    <string>/Users/little-dank/.config/lobster-claws/service-account.json</string>
    <key>GOOGLE_DELEGATED_USER</key>
    <string>user@domain.com</string>
</dict>
```

### Testing Pattern: Mock google-auth Credentials
```python
# Source: whisper-server test pattern adapted for google-auth
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

@pytest.fixture
def mock_credentials():
    creds = MagicMock()
    creds.token = "fake-access-token"
    creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    creds.with_scopes.return_value = creds
    creds.refresh.return_value = None  # refresh mutates creds in place
    return creds

@pytest.fixture
def client(mock_credentials):
    with patch("google_auth_server.app.service_account.Credentials") as MockCreds:
        MockCreds.from_service_account_file.return_value = mock_credentials
        mock_credentials.with_subject.return_value = mock_credentials
        # Re-import to pick up mocks
        from google_auth_server.app import app
        with TestClient(app) as tc:
            yield tc
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| oauth2client | google-auth >=2.0 | 2017 | oauth2client deprecated. Use `google.oauth2.service_account.Credentials`. |
| google-api-python-client for everything | Direct REST + google-auth for simple APIs | Ongoing | Avoids heavy transitive dependencies when only token minting is needed. |
| Manual JWT construction | `service_account.Credentials` | google-auth 1.0+ | Library handles claim format, signing, and exchange. |

**Deprecated/outdated:**
- `oauth2client`: Deprecated since 2017. Replaced by `google-auth`.
- `google-auth-httplib2`: Only needed with google-api-python-client. Not used here.
- `google-auth-oauthlib`: For interactive OAuth consent flows. Service accounts do not use consent.

## Open Questions

1. **Startup failure behavior: fail fast vs degraded start**
   - What we know: Launchd with KeepAlive will restart crashed processes. Fail-fast is simpler and guarantees the server is always healthy when running.
   - What's unclear: Whether restart loops on misconfiguration will flood logs and make debugging harder.
   - Recommendation: Fail fast with a clear error message. Launchd's `ThrottleInterval` (default 10s) prevents tight restart loops. A degraded server that accepts requests but cannot mint tokens is worse than no server at all.

2. **Scope format: short aliases vs full URLs**
   - What we know: Google APIs require full URL scopes (e.g., `https://www.googleapis.com/auth/gmail.readonly`). Short aliases would need a mapping table.
   - What's unclear: Whether the convenience of short aliases is worth the maintenance of a mapping table.
   - Recommendation: Accept full URL scopes. Skills are not humans -- they can pass full URLs without friction. A mapping table creates coupling between auth server and individual Google APIs.

3. **Token response metadata beyond access_token + expires_in**
   - What we know: `access_token` and `expires_in` are required per CONTEXT.md.
   - What's unclear: Whether additional fields (scopes, subject) help with debugging.
   - Recommendation: Include `token_type: "Bearer"` (standard OAuth convention) and nothing else. Skills already know the scopes they requested and the subject is server-wide. Keep the response minimal.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0 + pytest-httpx >=0.36 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (root level) |
| Quick run command | `uv run pytest servers/google-auth/tests/ common/tests/ -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | ClawsClient.post_json() sends JSON body, handles errors | unit | `uv run pytest common/tests/test_client.py::test_post_json_success -x` | No -- Wave 0 |
| CLI-02 | ClawsClient.get() accepts params dict | unit | `uv run pytest common/tests/test_client.py::test_get_with_params -x` | No -- Wave 0 |
| AUTH-01 | Server loads service account key from env var path | unit | `uv run pytest servers/google-auth/tests/test_app.py::test_loads_key_file -x` | No -- Wave 0 |
| AUTH-02 | Server mints tokens with domain-wide delegation | unit | `uv run pytest servers/google-auth/tests/test_app.py::test_token_with_delegation -x` | No -- Wave 0 |
| AUTH-03 | Server caches tokens, returns cached within TTL | unit | `uv run pytest servers/google-auth/tests/test_app.py::test_token_caching -x` | No -- Wave 0 |
| AUTH-04 | POST /token accepts arbitrary scopes in JSON body | unit | `uv run pytest servers/google-auth/tests/test_app.py::test_token_arbitrary_scopes -x` | No -- Wave 0 |
| AUTH-05 | GET /health returns status + metadata | unit | `uv run pytest servers/google-auth/tests/test_app.py::test_health -x` | No -- Wave 0 |
| AUTH-06 | Server binds 127.0.0.1:8301 | unit | `uv run pytest servers/google-auth/tests/test_app.py::test_default_bind -x` | No -- Wave 0 |
| AUTH-07 | Launchd plist is valid and has correct config | unit | `uv run pytest tests/test_plist.py -x` (extend existing) | Partially -- existing plist test framework |

### Sampling Rate
- **Per task commit:** `uv run pytest servers/google-auth/tests/ common/tests/ -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `servers/google-auth/tests/__init__.py` -- empty init
- [ ] `servers/google-auth/tests/test_app.py` -- covers AUTH-01 through AUTH-06
- [ ] `common/tests/test_client.py` -- extend with CLI-01, CLI-02 tests (file exists, needs new test functions)
- [ ] `tests/test_plist.py` -- extend for google-auth plist validation (file exists, extend pattern)
- [ ] Framework install: none needed -- pytest + pytest-httpx already in dev deps

## Sources

### Primary (HIGH confidence)
- [google-auth PyPI](https://pypi.org/project/google-auth/) -- version 2.49.1, released 2026-03-12. Verified via `pip index versions`.
- [google.oauth2.service_account docs](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.service_account.html) -- Credentials API, with_subject(), with_scopes(), refresh()
- [google-auth transport.requests docs](https://google-auth.readthedocs.io/en/latest/reference/google.auth.transport.requests.html) -- Request class for token refresh
- Existing codebase: `common/src/claws_common/client.py`, `servers/whisper/src/whisper_server/app.py`, `launchd/com.lobsterclaws.whisper.plist` -- established patterns

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md` -- prior research documents from milestone planning, cross-verified with official docs
- [Google OAuth 2.0 Server-to-Server](https://developers.google.com/identity/protocols/oauth2/service-account) -- domain-wide delegation flow

### Tertiary (LOW confidence)
- None -- all findings verified with official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- google-auth is the only library for this job, version confirmed on PyPI
- Architecture: HIGH -- follows established whisper-server pattern with well-documented modifications
- Pitfalls: HIGH -- sourced from official Google docs and verified community reports

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain -- google-auth and FastAPI move slowly)
