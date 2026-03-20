---
phase: 04-google-auth-server
verified: 2026-03-19T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 4: Google Auth Server Verification Report

**Phase Goal:** Skills can obtain short-lived Google access tokens from a host-side server that holds the service account key
**Verified:** 2026-03-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ClawsClient can send POST requests with JSON bodies and GET requests with query parameters | VERIFIED | `post_json()` and `get(params=...)` both exist in `client.py`; 5 new tests cover all paths; all pass |
| 2 | Auth server loads a service account key and mints access tokens with domain-wide delegation for a specified subject | VERIFIED | `lifespan()` calls `service_account.Credentials.from_service_account_file(key_path, subject=subject)`; `test_startup_loads_key` asserts the exact call |
| 3 | Auth server caches tokens and serves cached tokens on repeated requests within the TTL window | VERIFIED | `frozenset(req.scopes)` cache key, `expires_at > now + 60` guard; `test_token_caching` confirms `refresh.call_count == 2` (startup + first request only); `test_token_cache_expired` confirms re-mint when <60s left |
| 4 | Auth server responds to health checks on port 8301 (bound to 127.0.0.1 only) | VERIFIED | `DEFAULT_HOST = "127.0.0.1"`, `DEFAULT_PORT = 8301` in `app.py`; plist `--host 127.0.0.1 --port 8301`; `test_default_bind` and `test_google_auth_plist_binds_localhost` both assert this |
| 5 | Auth server starts automatically on boot via launchd and restarts on crash | VERIFIED | `launchd/com.lobsterclaws.google-auth.plist` contains `RunAtLoad=true`, `KeepAlive=true`; validated by `test_google_auth_plist_run_at_load` and `test_google_auth_plist_keep_alive` |

**Score:** 5/5 success criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `common/src/claws_common/client.py` | post_json() and get() with params support | VERIFIED | Both methods exist, substantive, use `httpx.post(..., json=data)` and `httpx.get(..., params=params)` |
| `common/tests/test_client.py` | Tests for post_json and get with params | VERIFIED | 5 new tests present: `test_post_json_success`, `test_post_json_connection_error`, `test_post_json_timeout`, `test_get_with_params`, `test_get_without_params_unchanged` |
| `servers/google-auth/src/google_auth_server/app.py` | FastAPI auth server with /token and /health endpoints | VERIFIED | Full implementation: lifespan, TokenRequest model, caching, retry, `main()` at 127.0.0.1:8301 |
| `servers/google-auth/pyproject.toml` | Package definition with google-auth, requests, fastapi, uvicorn deps | VERIFIED | name="google-auth-server", all required deps present, entry point configured |
| `servers/google-auth/tests/test_google_auth_app.py` | Unit tests with mocked google-auth credentials | VERIFIED | 11 tests; renamed from test_app.py to avoid module collision (documented deviation) |
| `servers/google-auth/tests/conftest.py` | Shared fixtures (added during execution) | VERIFIED | `mock_creds` and `app_client` fixtures properly isolate google-auth from real credentials |
| `launchd/com.lobsterclaws.google-auth.plist` | macOS launchd plist for auto-starting auth server | VERIFIED | Label, RunAtLoad, KeepAlive, 127.0.0.1:8301, GOOGLE_SERVICE_ACCOUNT_KEY, GOOGLE_DELEGATED_USER, log paths all present |
| `tests/test_launchd.py` | Plist validation tests for both whisper and google-auth | VERIFIED | Refactored to cover both plists; 12 google-auth tests + 8 whisper tests = 20 total |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `client.py` | httpx | `httpx.post(url, json=data)` and `httpx.get(url, params=params)` | WIRED | Both calls present with correct signatures on lines 42 and 25 |
| `app.py` | `google.oauth2.service_account` | `Credentials.from_service_account_file()` | WIRED | Import on line 16, call in `lifespan()` on line 44 |
| `app.py` | `google.auth.transport.requests` | `credentials.refresh(Request())` | WIRED | `google_auth_transport.Request()` called in both lifespan (line 52) and `get_token()` (line 108) |
| `launchd/com.lobsterclaws.google-auth.plist` | `servers/google-auth/src/google_auth_server/app.py` | `ProgramArguments: uvicorn google_auth_server.app:app` | WIRED | Plist line 12 contains `google_auth_server.app:app` |
| `pyproject.toml` (root) | `google-auth-server` workspace member | `[tool.uv.sources]` and dev dependency group | WIRED | Both `dependency-groups.dev` and `[tool.uv.sources]` contain `google-auth-server` |

### Requirements Coverage

All 9 requirement IDs from plan frontmatter verified against REQUIREMENTS.md:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-01 | 04-01 | ClawsClient supports POST with JSON body | SATISFIED | `post_json()` method in client.py; test_post_json_* tests pass |
| CLI-02 | 04-01 | ClawsClient supports GET with query parameters | SATISFIED | `get(params=...)` signature; test_get_with_params passes |
| AUTH-01 | 04-02 | Auth server loads service account JSON key from configured path | SATISFIED | `from_service_account_file(key_path)` in lifespan; test_startup_loads_key verifies exact call |
| AUTH-02 | 04-02 | Auth server mints access tokens using domain-wide delegation with configurable subject | SATISFIED | `subject=subject` passed to `from_service_account_file`; `GOOGLE_DELEGATED_USER` env var drives this |
| AUTH-03 | 04-02 | Auth server caches tokens and refreshes before expiry (~55 min TTL) | SATISFIED | frozenset cache with `expires_at > now + 60` guard; test_token_caching and test_token_cache_expired confirm |
| AUTH-04 | 04-02 | Auth server accepts arbitrary scope sets via request parameter | SATISFIED | `TokenRequest(scopes: list[str])` body; test_token_different_scopes confirms separate cache entries per scope set |
| AUTH-05 | 04-02 | Auth server exposes GET /health endpoint | SATISFIED | `@app.get("/health")` returns status, service, subject, verified_scopes; test_health asserts all keys |
| AUTH-06 | 04-02 | Auth server binds to 127.0.0.1:8301 (not 0.0.0.0) | SATISFIED | `DEFAULT_HOST = "127.0.0.1"`, `DEFAULT_PORT = 8301`; test_default_bind asserts call args; plist confirmed localhost-only |
| AUTH-07 | 04-03 | Auth server managed by launchd plist with auto-start and restart | SATISFIED | plist has RunAtLoad=true, KeepAlive=true, correct module path and env vars |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps CLI-01, CLI-02, AUTH-01 through AUTH-07 exclusively to Phase 4. All 9 are claimed by plans 04-01, 04-02, 04-03. No orphaned requirements.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments. No stub implementations. No empty return values. Ruff linter: all checks passed.

### Human Verification Required

#### 1. Real Google Workspace delegation

**Test:** Configure `GOOGLE_SERVICE_ACCOUNT_KEY` and `GOOGLE_DELEGATED_USER` with a real service account that has domain-wide delegation. Run `google-auth-server` and call `POST /token`.
**Expected:** Server starts, lifespan validation succeeds, `/token` returns a real `ya29.xxx` access token usable with Gmail API.
**Why human:** Requires live Google credentials. Cannot mock actual delegation grant or verify the returned token is accepted by Google's APIs.

#### 2. launchd boot auto-start behavior

**Test:** Load the plist with `launchctl load ~/Library/LaunchAgents/com.lobsterclaws.google-auth.plist` and reboot (or kill the process).
**Expected:** Server starts automatically at login and restarts within seconds of a crash.
**Why human:** launchd behavior requires a real macOS boot cycle or process kill to observe.

### Gaps Summary

No gaps. All automated checks passed.

---

## Test Run Results

```
42 passed in 1.22s

  common/tests/test_client.py        11 passed
  servers/google-auth/tests/         11 passed
  tests/test_launchd.py             20 passed
```

Ruff: `All checks passed!`

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_
