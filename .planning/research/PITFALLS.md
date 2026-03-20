# Pitfalls Research

**Domain:** Google service account auth server + Gmail skill for Docker-to-host CLI architecture
**Researched:** 2026-03-19
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Missing `subject` (impersonated user) in delegated credentials

**What goes wrong:**
Service account credentials are created without specifying which domain user to impersonate. Gmail API calls return `400 Precondition check failed` or `403 Forbidden`. This is the single most common failure when integrating Gmail with service accounts. The error message gives zero indication that the fix is adding a `subject` parameter.

**Why it happens:**
Domain-wide delegation requires two things: (1) the service account has delegation enabled in GCP, and (2) every API call specifies which domain user to act as via `credentials.with_subject("user@domain.com")`. Developers assume the service account can access Gmail directly -- it cannot. Gmail has no concept of a service account's own mailbox. The service account must always impersonate a real user.

**How to avoid:**
The auth server's `/token` endpoint must require a `subject` parameter (the email to impersonate) whenever the requested scopes include Gmail (or any user-scoped Google API). Return `400` with a clear message if `subject` is missing. Never default `subject` to the service account email.

**Warning signs:**
- `Precondition check failed` from Gmail API
- `403 Forbidden` with no further detail
- Token generation succeeds but downstream API calls fail
- "Works" for Drive/Calendar but fails for Gmail (all require subject, but Gmail gives the worst errors)

**Phase to address:**
Auth server design -- the `/token` endpoint contract must require `subject` for user-scoped APIs from the start.

---

### Pitfall 2: Service account JSON key file leaking into containers or git

**What goes wrong:**
The service account key file (JSON containing a private RSA key) gets committed to git, baked into a Docker image, or passed as an environment variable. This key never expires and grants full delegation access to every user in the Google Workspace domain -- all email, all calendar, all drive -- forever.

**Why it happens:**
The key looks harmless (just JSON). The path of least resistance is to copy it wherever it is needed. In this architecture specifically, the temptation is to mount the key into the Docker container so the Gmail skill can authenticate directly, bypassing the auth server entirely.

**How to avoid:**
The key file lives ONLY on the host Mac mini, readable only by the auth server process. Store it outside the repo entirely: `~/.config/lobster-claws/service-account.json`. The entire architectural purpose of the auth server is that containers never touch the key -- they request short-lived (1-hour) access tokens over HTTP. Add `*service-account*` and `*credentials*.json` patterns to `.gitignore` immediately.

**Warning signs:**
- Any `.json` key file reference in Dockerfile, docker-compose, or skill code
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable set in container context
- Key file anywhere inside the repo directory tree
- Skill code importing `google.oauth2.service_account` directly

**Phase to address:**
Auth server foundation -- key storage location must be decided before any code exists.

---

### Pitfall 3: Two-console delegation setup -- GCP Console is not enough

**What goes wrong:**
Code is correct, service account exists, delegation checkbox is enabled in GCP Console, but Gmail API calls fail with `401 Unauthorized` or `403 Insufficient Permission`. The developer spends hours debugging code when the problem is an admin console configuration step they never performed.

**Why it happens:**
Domain-wide delegation requires configuration in TWO separate admin consoles:
1. **GCP Console:** Create service account, check "Enable domain-wide delegation"
2. **Google Workspace Admin Console:** Security > API Controls > Domain-wide Delegation > Add the service account's Client ID + authorize specific OAuth scope strings

Developers complete step 1 and assume step 2 happened automatically. It did not. The scope strings must match exactly, including the full `https://www.googleapis.com/auth/gmail.readonly` URL format.

**How to avoid:**
The auth server must validate delegation works on startup by making a real API call (e.g., `GET https://gmail.googleapis.com/gmail/v1/users/{subject}/profile`). If it fails, log the exact error and the exact Admin Console URL where scopes need to be configured. Document the setup steps with the exact scope strings needed.

**Warning signs:**
- Auth server starts without errors but all token-consuming API calls fail
- Works for one scope but not another (partial scope authorization)
- `401` or `403` only when calling Google APIs, not during token generation itself

**Phase to address:**
Auth server implementation -- startup health check must validate end-to-end delegation, not just key file loading.

---

### Pitfall 4: Token caching done wrong -- stale tokens or no caching

**What goes wrong:**
Two failure modes: (A) No caching -- every CLI invocation generates a new JWT, exchanges it for an access token via Google's token endpoint, adding 200-500ms latency per call and risking rate limits. (B) Tokens cached past their 3600-second lifetime -- API calls fail with `401 Invalid Credentials` and the skill has no retry path.

**Why it happens:**
Google access tokens expire after exactly 1 hour (3600 seconds). The `google-auth` library handles refresh automatically when used with the Google API client library, but this project uses direct REST calls via httpx (matching the established pattern). Token lifecycle must be managed manually in the auth server.

**How to avoid:**
Cache tokens in the auth server keyed by `(subject, frozenset(scopes))`. Set expiry conservatively to 3500 seconds (100-second safety buffer). Return both the token and its expiry timestamp from the `/token` endpoint so skills can cache locally and skip redundant auth server calls. Use `google.oauth2.service_account.Credentials` for JWT creation and signing -- do not hand-roll JWT construction.

**Warning signs:**
- Noticeable latency (~500ms) on every `claws gmail` command (no caching)
- Intermittent `401` errors after ~1 hour of continuous use (stale cache)
- High request volume to `oauth2.googleapis.com` visible in server logs

**Phase to address:**
Auth server implementation -- token caching is core server logic, not an optimization to add later.

---

### Pitfall 5: Gmail send requires base64url encoding, not standard base64

**What goes wrong:**
Emails sent via `POST /gmail/v1/users/{userId}/messages/send` are rejected with `400 Invalid Message` or arrive garbled. The `raw` field must be base64**url**-encoded (RFC 4648 section 5, using `-_` instead of `+/`, no `=` padding), but developers use Python's `base64.b64encode()` which produces standard base64.

**Why it happens:**
A one-character function name difference: `b64encode()` vs `urlsafe_b64encode()`. Standard base64 uses `+` and `/` characters which are not URL-safe. The Gmail API docs mention "base64url" but do not emphasize the difference from standard base64. Python's `urlsafe_b64encode()` still adds `=` padding which must also be stripped.

**How to avoid:**
Write a dedicated helper and test it:
```python
import base64
def encode_message(mime_bytes: bytes) -> str:
    return base64.urlsafe_b64encode(mime_bytes).decode("ascii").rstrip("=")
```
Unit test: verify output contains no `+`, `/`, or `=` characters.

**Warning signs:**
- `400` errors when sending but not when reading mail
- Sent emails with garbled subjects or body content
- Tests pass with mocked API but fail against real Gmail

**Phase to address:**
Gmail skill implementation -- encoding helper should be written and tested before any send logic.

---

### Pitfall 6: ClawsClient lacks methods needed for JSON API calls

**What goes wrong:**
The Gmail skill needs to POST JSON bodies (sending mail), make GET requests with custom headers (Bearer auth), and potentially DELETE. The existing `ClawsClient` only has `get()` and `post_file()`. Developers either hack around the limitation with raw httpx calls or extend ClawsClient inconsistently per-skill, breaking the established error handling patterns.

**Why it happens:**
`ClawsClient` was designed for whisper's simple use case: health check GET and file upload POST. The auth server and Gmail skill need `post_json()`, and the Gmail skill needs to pass Bearer tokens to the auth server's responses through to Google. The client was never designed for this flow.

**How to avoid:**
Extend `ClawsClient` in `claws-common` BEFORE building the auth server or Gmail skill. Add `post_json(path, data, headers=None)` at minimum. Keep the same `ConnectionError`/`TimeoutError` wrapping with service-aware messages. This is a prerequisite for the auth and Gmail work.

**Warning signs:**
- Raw `httpx.post()` or `httpx.get()` calls appearing in skill code
- Duplicated try/except blocks outside ClawsClient
- Inconsistent timeout behavior between skills

**Phase to address:**
Common library update -- must happen before auth server or Gmail skill work begins.

---

### Pitfall 7: Auth server bound to 0.0.0.0 exposes token minting to entire network

**What goes wrong:**
The auth server listens on `0.0.0.0:8301` (following the whisper server pattern of binding to all interfaces). Any device on the local network can request access tokens for any user in the domain. On a home network this might be acceptable risk; on a shared network it is a full domain compromise.

**Why it happens:**
The whisper server binds to `0.0.0.0` because Docker containers need to reach it via `host.docker.internal`, which on Docker Desktop for Mac resolves to the host's IP on the Docker bridge. Developers copy this pattern for the auth server without considering that the auth server is fundamentally more sensitive -- it mints credentials rather than just processing audio.

**How to avoid:**
Bind the auth server to `127.0.0.1` only. On Docker Desktop for Mac, `host.docker.internal` resolves to `127.0.0.1` from the container's perspective (the host loopback), so binding to localhost still allows container access. This is a Docker Desktop for Mac specific behavior -- document it clearly. If the project ever moves to Linux Docker, this will need revisiting with firewall rules.

**Warning signs:**
- `netstat` or `lsof` showing the auth server listening on `*:8301` or `0.0.0.0:8301`
- Auth server accessible from other devices on the network
- No authentication between skill and auth server

**Phase to address:**
Auth server foundation -- bind address decision must be made at server creation time.

---

### Pitfall 8: Gmail API not enabled in the service account's GCP project

**What goes wrong:**
API calls fail with `403 Access Not Configured` or `403 Gmail API has not been used in project XXXXX`. The service account belongs to one GCP project, but the Gmail API is enabled in a different project, or not enabled at all.

**Why it happens:**
GCP projects proliferate. Developers enable APIs in whichever project they have open. The Gmail API must be enabled in the same project that owns the service account. This is a 30-second fix once identified, but can waste hours of debugging because the error message references a project number (not name) that may not be immediately recognizable.

**How to avoid:**
The auth server startup health check (same one that validates delegation) will catch this. Log the project ID from the service account key file at startup so it is always clear which project is in play.

**Warning signs:**
- Error messages mentioning "project" or "API not enabled"
- Service account email address domain (`xxx@project-id.iam.gserviceaccount.com`) does not match expected project

**Phase to address:**
Auth server implementation -- covered by the same startup health check as Pitfall 3.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded impersonation subject in auth server | Skip parameterization, faster to build | Cannot add Calendar/Drive skills for other users; locks to one email address | Never -- always parameterize subject on the `/token` endpoint |
| Using `google-api-python-client` in the container skill | Familiar API, handles pagination and discovery | Pulls 15+ transitive dependencies into the container (protobuf, google-auth, uritemplate, etc.), conflicts with the thin-CLI httpx-only pattern | Never -- use direct REST via httpx to match existing architecture |
| Skipping token caching | Simpler auth server implementation | 200-500ms latency per CLI call, risk hitting Google token endpoint rate limits | Only during initial prototyping; must be added before any skill uses it |
| Single hardcoded scope set | Simpler token endpoint | Cannot request different scopes for different operations (read-only vs send) | Acceptable for v1.1 while only Gmail exists; refactor when Calendar is added |
| No retry on Google API 429/5xx | Simpler skill code | Agent hits rate limits during batch inbox reads | Acceptable for v1.1 -- single user, low volume; add when batch operations are needed |
| Inlining MIME construction | Fewer abstractions | Cannot reuse for Calendar invites, Drive sharing notifications | Acceptable for v1.1; extract when second email-sending use case appears |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Service account JWT signing | Hand-rolling JWT with PyJWT or similar | Use `google.oauth2.service_account.Credentials` -- handles claims format, RS256 signing, and token exchange correctly |
| Gmail `messages.list` | Assuming response contains full message bodies | `messages.list` returns only message IDs and thread IDs; must call `messages.get` per message for headers/body |
| Gmail `messages.send` userId | Using literal string `"me"` as userId | `"me"` works IF the access token was created with correct `subject`; use the actual impersonated email for clarity and debuggability |
| Gmail message format | Requesting `format=full` for inbox listing | Use `format=metadata` with `metadataHeaders=["From","Subject","Date"]` for listing; `format=full` only for individual message reads -- saves 20x quota |
| Auth server port | Using port 8300 (already taken by whisper-server) | Use 8301 for google-auth server; document in CLAUDE.md port registry |
| Gmail OAuth scopes | Using `https://mail.google.com/` (unrestricted full access) | Use minimal scopes: `gmail.readonly` for reading, `gmail.send` for sending, `gmail.modify` for label changes |
| Token endpoint design | Returning only the access token string | Return `{"access_token": "...", "expires_at": 1234567890}` so skills can cache locally and know when to refresh |
| Gmail search queries | Building complex query strings without URL encoding | Use httpx `params={"q": query}` which handles encoding automatically; do not manually construct query strings |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No token caching in auth server | Every CLI call takes 500ms+ for auth roundtrip | Cache tokens by `(subject, frozenset(scopes))` with 3500s TTL | Noticeable immediately on every single command |
| Fetching full message bodies in list operations | Slow inbox queries, burns 5 quota units per message instead of 5 for the whole list | Use `messages.list` for IDs, then selective `messages.get` with `format=metadata` | More than 10 messages per query |
| No skill-side token caching | Every CLI call hits auth server even when token is still valid | Auth server returns `expires_at`; skill caches token locally until near-expiry | Noticeable when running multiple gmail commands in sequence |
| Synchronous token refresh blocking requests | Auth server hangs while refreshing an expired token; concurrent requests queue behind it | Refresh proactively when token is within 5 minutes of expiry, not on-demand | Under concurrent use (multiple skills calling auth server simultaneously) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Service account key in repo or Docker image | Full domain-wide delegation to all users' email, calendar, drive -- forever (key never expires) | Key lives only on host filesystem outside repo; `.gitignore` blocks `*service-account*` and `*credentials*.json`; auth server is sole consumer |
| Overly broad OAuth scopes in Admin Console | Service account can read, modify, and delete all users' email | Authorize minimum scopes in Admin Console: `gmail.readonly`, `gmail.send`, `gmail.modify`; never `https://mail.google.com/` |
| Auth server on 0.0.0.0 | Any device on local network can mint tokens for any domain user | Bind to `127.0.0.1`; Docker Desktop for Mac reaches host loopback via `host.docker.internal` |
| Logging access tokens | Tokens visible in server logs, launchd stdout/stderr logs, Console.app | Never log token values; log token metadata only: subject, scopes, expiry time, request timestamp |
| No audit trail for token requests | Cannot determine which skill impersonated which user, or when | Log every `/token` request with timestamp, requested subject, scopes, and requesting IP |
| Passing token via query parameter | Token visible in server access logs, browser history, proxy logs | Always pass tokens in `Authorization: Bearer` header, never in URLs |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Passing raw Google API errors to the agent | Agent gets `400 Precondition check failed` with no context | Translate Google errors: "Gmail delegation not configured for user@domain.com. Admin must authorize scopes in Workspace Admin Console." |
| No way to verify auth setup | Agent tries Gmail, gets cryptic error, cannot tell if setup or runtime issue | `claws gmail check` subcommand that validates: auth server running, delegation configured, Gmail API enabled, test email fetch works |
| Email send appears to succeed but is queued | Agent reports "sent" but email is stuck | Verify `messages.send` response contains `id` and `labelIds` includes `SENT`; report actual status |
| Gmail search syntax undocumented | Agent cannot construct queries | Skill `--help` and error output should include common query examples: `from:boss@co.com`, `subject:invoice`, `newer_than:1d`, `is:unread` |
| No inbox summary -- just raw message dumps | Agent overwhelmed by full message content for every email | Default `list` to showing From, Subject, Date, snippet; require explicit `read <id>` for full body |

## "Looks Done But Isn't" Checklist

- [ ] **Auth server token endpoint:** Returns tokens -- but does it handle expiry and refresh? Test by waiting > 1 hour with a cached token.
- [ ] **Auth server health check:** Starts without error -- but does it validate actual delegation with a real API call, or just check the key file exists?
- [ ] **Gmail send:** Sends one test email -- but does it handle CC/BCC, reply-to-thread (`threadId`), and HTML bodies? Verify MIME construction covers these.
- [ ] **Gmail list:** Returns messages -- but does it handle pagination for inboxes with > 100 messages? Check `nextPageToken` handling.
- [ ] **Gmail search:** Returns results -- but does it handle zero results without erroring? Must return empty list, not crash.
- [ ] **Admin Console scopes:** Delegation works for `gmail.readonly` -- but are ALL required scopes authorized? Missing `gmail.send` means send silently fails.
- [ ] **Port 8301:** Auth server runs -- but is the port documented in CLAUDE.md, launchd plist, and the skill's default config?
- [ ] **Error handling:** Skill handles auth server connection errors -- but does it distinguish "auth server down" from "Google API rejected the request" from "invalid subject email"?
- [ ] **Token in logs:** Server runs fine -- but check launchd stdout/stderr log files for any token values leaking into plaintext logs.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Key file committed to git | HIGH | Revoke key immediately in GCP Console, generate new key, use BFG Repo-Cleaner to purge from all history, force-push, rotate any tokens that may have been generated with the compromised key |
| Wrong scopes in Admin Console | LOW | Update in Admin Console > Security > API Controls > Domain-wide Delegation; takes effect within minutes, no code changes needed |
| Token caching bug (stale tokens) | LOW | Restart auth server to clear in-memory cache; add `/cache/clear` admin endpoint for future incidents |
| base64 vs base64url encoding | LOW | Fix encoding function, add unit test; no data loss since Gmail API rejects malformed messages outright |
| Gmail API not enabled in GCP project | LOW | Enable in GCP Console > APIs & Services > Enable APIs; takes effect immediately |
| Auth server on 0.0.0.0 | MEDIUM | Change bind to 127.0.0.1, restart; audit launchd logs for any external IP token requests |
| Subject not required on token endpoint | MEDIUM | Add validation, update all skill calls; existing tokens still expire in < 1 hour so exposure is time-limited |
| ClawsClient missing methods | LOW | Add methods to claws-common, bump version; all skills using it get the fix on next `uv sync` |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Missing subject in credentials | Auth server design | `/token` returns 400 when `subject` is omitted for Gmail scopes |
| Key file security | Auth server foundation | Key path is outside repo; `.gitignore` blocks credentials patterns; no key references in Dockerfile |
| Two-console delegation setup | Auth server implementation | Startup health check makes real Gmail API call; fails loudly with setup instructions if delegation is broken |
| Token caching | Auth server implementation | Integration test: two `/token` requests within 1 second return same token; only one Google token exchange occurs |
| base64url encoding | Gmail skill implementation | Unit test: encoded MIME output contains no `+`, `/`, or `=` characters |
| ClawsClient extension | Common library update (prerequisite) | `post_json()` method exists with same error handling as `get()` and `post_file()` |
| Gmail API not enabled | Auth server implementation | Covered by startup health check (same as delegation validation) |
| Auth server bind address | Auth server foundation | `lsof -i :8301` shows `127.0.0.1` not `*` after server starts |
| Port conflict with whisper | Auth server foundation | Port 8301 documented in CLAUDE.md; no collision with whisper on 8300 |

## Sources

- [Google: Domain-wide delegation best practices](https://support.google.com/a/answer/14437356?hl=en)
- [Google: Control API access with domain-wide delegation](https://support.google.com/a/answer/162106?hl=en)
- [Google: Best practices for managing service account keys](https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)
- [Google: Best practices for using service accounts securely](https://docs.cloud.google.com/iam/docs/best-practices-service-accounts)
- [Google: Using OAuth 2.0 for Server to Server Applications](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Google: Gmail API Usage Limits and Quotas](https://developers.google.com/workspace/gmail/api/reference/quota)
- [Google: Create and send email messages (Gmail API)](https://developers.google.com/workspace/gmail/api/guides/sending)
- [GitHub: Precondition check failed with service account (googleapis/google-api-python-client#984)](https://github.com/googleapis/google-api-python-client/issues/984)
- [GitHub: google-auth-library-python user guide](https://github.com/googleapis/google-auth-library-python/blob/main/docs/user-guide.rst)
- [Google: Token types and lifetimes](https://docs.cloud.google.com/docs/authentication/token-types)

---
*Pitfalls research for: Google auth server + Gmail skill integration into lobster_claws*
*Researched: 2026-03-19*
