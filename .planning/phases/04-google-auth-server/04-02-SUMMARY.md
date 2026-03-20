---
phase: 04-google-auth-server
plan: 02
subsystem: auth
tags: [google-auth, fastapi, service-account, domain-delegation, token-cache]

requires:
  - phase: 01-foundation
    provides: FastAPI server pattern (whisper-server), hatchling build, uv workspace

provides:
  - Google auth token vending server (POST /token, GET /health)
  - Token caching with scope-based keys and 60s expiry buffer
  - Startup delegation validation
  - Server binding to 127.0.0.1:8301

affects: [05-gmail-skill, launchd-plist]

tech-stack:
  added: [google-auth, requests]
  patterns: [token-vending-machine, lifespan-validation, scope-based-cache]

key-files:
  created:
    - servers/google-auth/pyproject.toml
    - servers/google-auth/src/google_auth_server/__init__.py
    - servers/google-auth/src/google_auth_server/app.py
    - servers/google-auth/tests/__init__.py
    - servers/google-auth/tests/conftest.py
    - servers/google-auth/tests/test_google_auth_app.py
  modified:
    - pyproject.toml

key-decisions:
  - "Renamed test file to test_google_auth_app.py to avoid importlib module collision with whisper test_app.py"
  - "Extracted test fixtures to conftest.py for proper pytest discovery"
  - "Used datetime.UTC alias per ruff UP017 rule"

patterns-established:
  - "Token vending: base_creds loaded once, with_scopes() per request, frozenset cache key"
  - "Startup validation: lifespan mints a real token to verify delegation before accepting requests"
  - "Security bind: auth servers use 127.0.0.1, not 0.0.0.0"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06]

duration: 5min
completed: 2026-03-20
---

# Phase 04 Plan 02: Auth Server Summary

**FastAPI token vending server with domain-wide delegation, scope-based caching, and retry logic on 127.0.0.1:8301**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T05:27:38Z
- **Completed:** 2026-03-20T05:33:10Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- POST /token accepts arbitrary scopes, returns access_token + expires_in + token_type with Bearer format
- Token caching with frozenset(scopes) key, returns cached token when >60s remains before expiry
- One retry with 0.5s backoff for transient Google errors, 503 on double failure
- Lifespan startup validates delegation end-to-end before accepting requests
- Server binds to 127.0.0.1:8301 (not 0.0.0.0) for security
- 11 tests with mocked google-auth credentials, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth server package scaffolding** - `9480c64` (chore)
2. **Task 2 RED: Add failing tests** - `3413724` (test)
3. **Task 2 GREEN: Implement auth server** - `c09b862` (feat)

## Files Created/Modified
- `servers/google-auth/pyproject.toml` - Package definition with google-auth, requests, fastapi, uvicorn
- `servers/google-auth/src/google_auth_server/__init__.py` - Package init
- `servers/google-auth/src/google_auth_server/app.py` - FastAPI app with /token and /health endpoints
- `servers/google-auth/tests/__init__.py` - Test package init
- `servers/google-auth/tests/conftest.py` - Shared test fixtures (mock_creds, app_client)
- `servers/google-auth/tests/test_google_auth_app.py` - 11 unit tests covering all endpoints and behaviors
- `pyproject.toml` - Added google-auth-server to dev deps and uv sources

## Decisions Made
- Renamed test file from `test_app.py` to `test_google_auth_app.py` to avoid module name collision with whisper-server's `test_app.py` under `--import-mode=importlib`
- Extracted test fixtures to `conftest.py` for proper pytest fixture discovery across test directories
- Used `datetime.UTC` alias instead of `timezone.utc` per ruff UP017 rule

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test module name collision**
- **Found during:** Task 2 (test verification)
- **Issue:** Both whisper-server and google-auth-server had `tests/test_app.py`. With `--import-mode=importlib`, pytest imported the google-auth module under the whisper test path, causing fixture `app_client` not found errors.
- **Fix:** Renamed to `test_google_auth_app.py` and moved fixtures to `conftest.py`
- **Files modified:** `servers/google-auth/tests/test_google_auth_app.py`, `servers/google-auth/tests/conftest.py`
- **Verification:** `uv run pytest` -- all 60 tests pass
- **Committed in:** c09b862

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for full test suite to pass. No scope creep.

## Issues Encountered
None beyond the test naming collision documented above.

## User Setup Required
None - no external service configuration required for the code itself. (Google service account and domain-wide delegation setup is a separate operational concern addressed in plan 04-03.)

## Next Phase Readiness
- Auth server implementation complete, ready for launchd plist (plan 04-03)
- ClawsClient extensions (plan 04-01) can proceed independently
- Server can be tested with real credentials once env vars are configured

---
*Phase: 04-google-auth-server*
*Completed: 2026-03-20*
