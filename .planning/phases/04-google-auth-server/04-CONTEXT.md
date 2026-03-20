# Phase 4: Google Auth Server - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Service account token vending server on the Mac mini host, plus ClawsClient extensions (`post_json`, `get` with query params). Skills POST to the auth server to get short-lived Google access tokens. The auth server holds the service account key, handles domain-wide delegation, caches tokens, and serves them to any requesting skill. Gmail skill (Phase 5) is the first consumer.

</domain>

<decisions>
## Implementation Decisions

### Token API contract
- **Endpoint:** `POST /token` with JSON body `{"scopes": [...]}`
- **Scope format:** Claude's discretion — short aliases (e.g., `gmail.modify`) with server expansion to full URLs, or full URLs passed through
- **Response shape:** Claude's discretion — include access_token + expires_in at minimum; metadata (scopes, subject) optional for debugging
- **Server role:** Claude's discretion — token vending only (skills call Google APIs directly with the token) vs proxying API calls. Consider that token vending is simpler, keeps auth server single-responsibility, and lets skills use httpx directly which matches existing patterns

### Health + diagnostics
- **Startup:** Full end-to-end check — mint a real token on startup to verify key file + delegation are correctly configured
- **`/health` response:** Include status, service name, impersonated subject, and verified scopes — more useful for debugging than the minimal whisper-server pattern
- **Startup failure behavior:** Claude's discretion — exit with error (fail fast, launchd restarts) vs start degraded (allows log inspection without restart loops)

### Error behavior
- **Error format:** HTTP status codes — 400 for bad requests (missing scopes), 503 for Google unreachable, 500 for key/delegation issues. Skills use existing ClawsClient error handling.
- **Error verbosity:** Claude's discretion — actionable troubleshooting hints in error responses are preferred when they help the user fix configuration issues
- **Retry policy:** One retry with short backoff for transient Google errors (network blips, 500s). Fail after that.

### Claude's Discretion
- Token response shape details (metadata beyond access_token + expires_in)
- Scope format (short aliases vs full URLs)
- Token vending vs API proxy architecture (token vending is the leaning)
- Startup failure behavior (fail fast vs degraded start)
- Error response detail level
- Token cache implementation (TTL, eviction strategy)
- Configuration approach (env vars vs config file for key path and subject)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Google auth patterns
- `.planning/research/STACK.md` — Library choices (`google-auth >=2.49`, `requests` as transport), rationale for avoiding google-api-python-client
- `.planning/research/ARCHITECTURE.md` — Token vending pattern, data flow diagrams, component layout
- `.planning/research/PITFALLS.md` — Critical pitfalls: `subject` param required, two-console delegation setup, bind address security, token caching as core logic

### Existing server patterns
- `servers/whisper/src/whisper_server/app.py` — Reference FastAPI server: lifespan preloading, `/health` endpoint, uvicorn entry point
- `launchd/com.lobsterclaws.whisper.plist` — Reference plist: RunAtLoad, KeepAlive, log paths, env vars
- `common/src/claws_common/client.py` — ClawsClient to extend with `post_json()` and `get()` params

### Integration reference
- `data.md` — OpenClaw Docker environment, networking, env var conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClawsClient` (`common/src/claws_common/client.py`): HTTP wrapper to extend with `post_json()` and `get()` with query params. ~15 lines each following existing error-handling pattern.
- `whisper_server/app.py`: Reference FastAPI server pattern — lifespan for preloading, health endpoint, uvicorn entry point. Auth server follows same structure.
- `com.lobsterclaws.whisper.plist`: Reference plist to copy for auth server — same structure but port 8301, bind 127.0.0.1, different working directory.
- `claws_common.output`: Result/fail/crash helpers — not used by servers directly but used by skills consuming the auth server.

### Established Patterns
- **Server structure:** FastAPI + uvicorn, lifespan for startup work, `/health` endpoint returns `{"status": "ok", "service": "..."}` plus service-specific fields
- **Package layout:** `servers/<name>/src/<name>_server/app.py` with `pyproject.toml` using hatchling
- **Plist pattern:** Label `com.lobsterclaws.<name>`, RunAtLoad + KeepAlive, logs to `~/Library/Logs/lobsterclaws/`
- **Error handling:** ClawsClient catches `ConnectError` and `TimeoutException`, raises `ConnectionError`/`TimeoutError` with service-aware messages

### Integration Points
- Root `pyproject.toml`: Add `google-auth-server` as workspace member and dev dependency
- `common/pyproject.toml`: No changes needed (ClawsClient extension is in existing package)
- `launchd/`: New plist for auth server
- Skills (Phase 5): Will use `ClawsClient("google-auth", 8301)` to get tokens

</code_context>

<specifics>
## Specific Ideas

- Auth server health endpoint should show more detail than whisper-server — include subject being impersonated and what scopes were verified at startup
- The research flagged that whisper-server binds `0.0.0.0` but auth server MUST bind `127.0.0.1` since it serves security-sensitive tokens
- User emphasized "set up once and never touch" — startup validation is critical to catch misconfiguration early

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-google-auth-server*
*Context gathered: 2026-03-19*
