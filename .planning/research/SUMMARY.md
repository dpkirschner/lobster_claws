# Project Research Summary

**Project:** Lobster Claws v1.1 — Google Auth Server + Gmail Skill
**Domain:** Google Workspace API integration into a Docker-to-host CLI agent tooling monorepo
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

This v1.1 milestone adds Gmail capability to the Lobster Claws agent by introducing a Google auth server on the host and a thin Gmail CLI skill in the container. The core architectural pattern follows the established v1.0 approach — the host owns sensitive resources, the container runs thin logic — with one deliberate evolution: the auth server acts as a token vending machine rather than a full API proxy. The Gmail skill gets a short-lived access token from the host, then calls the Gmail REST API directly over HTTPS. This keeps the service account JSON key permanently on the host while avoiding the overhead of proxying all Gmail payloads through a host intermediary.

The recommended stack is minimal: `google-auth` (>=2.49) and `requests` are the only new dependencies, both confined to the host-side auth server. The Gmail skill in the container depends only on `claws-common`, the same as every existing skill. Direct Gmail REST API calls via `httpx` replace the heavier `google-api-python-client` library, which would introduce a parallel HTTP stack and ~15MB of transitive dependencies for what amounts to three stable REST endpoints. All four research files converge on the same conclusion: keep the container thin, keep Google complexity on the host, reuse established patterns.

The primary risks are configuration-level, not code-level. Domain-wide delegation requires two separate admin console steps (GCP Console and Google Workspace Admin Console), and missing either one produces opaque `401`/`403` errors that look like code bugs. The auth server must validate end-to-end delegation at startup — not just confirm the key file loads — and must bind to `127.0.0.1` rather than `0.0.0.0` to prevent any device on the local network from minting domain credentials. All other pitfalls (token caching, base64url encoding, subject parameter) are well-understood and straightforward to test against.

## Key Findings

### Recommended Stack

The auth server adds `google-auth>=2.49` (JWT signing, credential management, token exchange) and `requests>=2.32` (used exclusively as a transport adapter for `google-auth`'s credential refresh — not for direct HTTP calls). The `requests` addition alongside `httpx` is intentional and bounded: `google-auth` ships transports only for `requests` and `aiohttp`; writing a custom `httpx` transport adds complexity with no user-facing benefit. All other infrastructure — FastAPI, uvicorn, httpx, hatchling, pytest, ruff — is reused from v1.0 unchanged.

**Core technologies:**
- `google-auth>=2.49`: JWT signing + Google token endpoint exchange + `service_account.Credentials` management — the only correct library for this; no alternative for domain-wide delegation
- `requests>=2.32`: Transport adapter for `google-auth` credential refresh — confined to host auth server, never in container
- `FastAPI + uvicorn`: Auth server framework — same as whisper-server, no new patterns required
- `httpx`: Gmail REST API calls from skill — already present via `claws-common`
- `claws-common`: Gmail skill uses `ClawsClient` and output helpers — unchanged, no new methods needed

**What not to use:** `google-api-python-client` (heavy transitive dependencies, second HTTP stack), `google-auth-oauthlib` (OAuth consent flow, not needed for service accounts), `oauth2client` (deprecated 2017), any Google library in the container.

### Expected Features

**Must have (v1.1 table stakes):**
- Auth server: service account credentials + domain-wide delegation with `subject` impersonation
- Auth server: in-memory token caching keyed by `(subject, frozenset(scopes))` with 3500s TTL
- Auth server: `/token` endpoint accepting `scopes` query param; `/health` endpoint
- Auth server: multi-scope support via request parameter (enables Calendar/Drive later at zero server cost)
- Auth server: launchd plist for auto-start on reboot
- Gmail skill: `claws gmail read <id>`, `search <query>`, `send --to --subject --body` subcommands
- Gmail skill: structured JSON output (MIME payload flattening — From, To, Subject, Date, plain-text body)

**Should have (v1.1.x patches after validation):**
- Thread view (`claws gmail thread <id>`)
- Attachment metadata in message output (filename, mimeType, size)
- Label filtering on list/search
- Reply-to thread support (In-Reply-To + References headers)
- Mark as read/unread

**Defer (v2+):**
- Google Calendar skill (reuses auth server, new scopes)
- Google Drive skill
- Attachment download (requires consuming skill to process)
- Batch operations
- Trash/archive (defer until agent trust model is established)
- Push notifications (requires public webhook URL — not feasible from Mac mini behind NAT)

### Architecture Approach

The architecture is a deliberate evolution of v1.0's "thin CLI -> host server -> result" pattern into "thin CLI -> host auth server for token -> external API -> result". The host still owns the sensitive credential (service account JSON key); the container still has no secrets. The auth server on port 8301 is the sole holder of the key and mints short-lived (1-hour) access tokens on demand. The Gmail skill makes two types of HTTP calls: `ClawsClient` to the auth server (same host-server pattern as whisper), then raw `httpx` to `gmail.googleapis.com` with a bearer token. A `gmail.py` module within `claws_gmail` isolates Gmail API logic from CLI argument parsing in `cli.py`.

**Major components:**
1. `google-auth-server` (NEW, `servers/google-auth/`, port 8301) — holds service account key, vends short-lived access tokens via domain-wide delegation, caches tokens in memory
2. `claws-gmail` (NEW, `skills/gmail/`) — thin CLI skill; gets token via `ClawsClient`, calls Gmail REST API directly with `httpx`, formats output with `result()`/`fail()`/`crash()`
3. `launchd/com.lobsterclaws.google-auth.plist` (NEW) — auto-starts auth server on reboot, same pattern as whisper plist
4. `claws-common` (UNCHANGED) — existing `ClawsClient.get()` is sufficient for the `/token` endpoint call; no new methods needed
5. `claws-cli` (UNCHANGED) — discovers gmail skill automatically via entry points

### Critical Pitfalls

1. **Missing `subject` in delegated credentials** — Service account credentials without `.with_subject()` return `400 Precondition check failed` or `403 Forbidden` from Gmail with zero diagnostic context. The `/token` endpoint must require a `subject` parameter and return `400` with a clear message if omitted. Never default to the service account email.

2. **Two-console delegation setup** — Domain-wide delegation requires configuration in both GCP Console (enable delegation on the service account) AND Google Workspace Admin Console (authorize the service account client ID with specific scope strings). Missing the Workspace Admin Console step produces `401`/`403` errors that look like code bugs. The auth server must make a real Gmail API call at startup to validate end-to-end delegation, logging the exact Admin Console URL if it fails.

3. **Service account key leaking into containers or git** — The key grants permanent domain-wide delegation to all users' email, calendar, and drive. It must live only on the host filesystem outside the repo (`~/.config/lobster-claws/service-account.json`). Add `*service-account*` and `*credentials*.json` to `.gitignore` immediately. The entire architectural purpose of the auth server is that containers never touch the key.

4. **Auth server bound to `0.0.0.0`** — The whisper-server binds to all interfaces; copying this pattern for the auth server is wrong because the auth server mints credentials. Bind to `127.0.0.1` only. On Docker Desktop for Mac, `host.docker.internal` resolves to the host loopback, so container access still works. This prevents any device on the local network from requesting domain credentials.

5. **base64url vs standard base64 for Gmail send** — `base64.b64encode()` produces standard base64 (uses `+` and `/`, adds `=` padding); Gmail's `messages.send` requires base64url (`-_` characters, no padding). Use `base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")`. Write and test this helper before any send logic.

## Implications for Roadmap

The dependency graph drives a clear three-phase structure. The auth server is the prerequisite for all Gmail work. The Gmail skill depends on the auth server being independently testable. Security decisions (bind address, key file location, `.gitignore`) must be made before any code exists, not retrofitted.

### Phase 1: Google Auth Server

**Rationale:** The auth server is the prerequisite for all Gmail work. It holds the credential, vends tokens, and must be independently testable before the Gmail skill can be built. Security decisions (bind address, key file location, `.gitignore`) must be made before any code exists. Token caching is core server logic, not an optimization to add later.
**Delivers:** Working `/health` and `/token` endpoints on port 8301 with real domain-wide delegation; in-memory token caching; startup validation of end-to-end delegation; launchd plist for auto-start; multi-scope support via request parameter.
**Addresses:** All auth server table-stakes features (token serving, delegation, caching, health endpoint, multi-scope support, launchd plist).
**Avoids:** Key file leak (key storage and `.gitignore` established first), `0.0.0.0` bind address, missing subject validation, stale or missing token caching, two-console delegation confusion (startup health check surfaces it immediately with actionable error).

### Phase 2: Gmail Skill

**Rationale:** Depends on Phase 1's auth server being complete and testable. The skill is the agent-facing interface and cannot be meaningfully built or tested without a working token source. MIME payload flattening (structured output) must be built as a cross-cutting concern from the start — it is required by both list (header extraction) and read (body extraction) operations.
**Delivers:** `claws gmail read <id>`, `claws gmail search <query>`, `claws gmail send --to --subject --body` subcommands with structured JSON output; base64url encoding helper; Gmail API error mapping (401, 404, 429) to user-facing messages.
**Uses:** `claws-common` (ClawsClient, output helpers), `httpx` for Gmail REST API calls, `gmail.py` module for Gmail-specific logic isolation.
**Implements:** Two-tier HTTP pattern (ClawsClient to auth server + raw httpx to Gmail API); MIME payload flattening; subcommand CLI with argparse.
**Avoids:** base64url encoding bug (helper written and tested first), raw Google API errors surfaced to agent, full message bodies fetched during list operations (use `format=metadata` for listing, `format=full` only for individual reads).

### Phase 3: Integration and Hardening

**Rationale:** After both components exist independently, verify end-to-end flows, update workspace configuration, and document the port registry and setup steps. The `claws gmail check` diagnostic subcommand becomes feasible only after both components are working.
**Delivers:** Root `pyproject.toml` updated with new workspace members; CLAUDE.md port registry updated (port 8301 documented); setup documentation for service account + Admin Console steps with exact scope strings; `claws gmail check` diagnostic subcommand; `uv sync` verifies all tests pass end-to-end.
**Addresses:** Developer experience gaps — unclear error messages, undocumented setup steps, port registry, Admin Console scope string format.

### Phase Ordering Rationale

- Auth server before Gmail skill: Gmail skill cannot acquire tokens or be end-to-end tested without the auth server. Mocking is insufficient — delegation validation requires real Google API calls to confirm both GCP and Admin Console setup.
- Security decisions in Phase 1: Key file location, bind address, and `.gitignore` are architectural decisions that are expensive to change after code exists.
- Structured output (MIME flattening) built into Phase 2 from the start: It is required by both list and read operations; retrofitting it creates inconsistency.
- Workspace config and documentation in Phase 3: These are mechanical tasks that require both packages to exist and be tested.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Auth Server):** Token caching implementation details may need validation against `google-auth` library behavior — specifically, the expiry timestamp format on `Credentials.expiry` and thread safety of the in-memory cache under FastAPI's async model. The startup health check design (which endpoint to call, how to surface setup instructions) warrants careful planning.
- **Phase 2 (Gmail Skill):** MIME multipart parsing edge cases (nested parts, missing text/plain with HTML-only body, messages with only attachments) may need additional research. Pagination handling for large inboxes (`nextPageToken`) needs explicit design before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 3 (Integration):** Pure configuration and documentation work. Established patterns from v1.0 apply directly (pyproject.toml workspace additions, CLAUDE.md updates, launchd plist structure).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | google-auth is the only viable library; all decisions backed by official Google documentation; version compatibility confirmed against Python 3.12 |
| Features | HIGH | Gmail REST API is stable and well-documented; feature scope is conservative and tightly bounded; MVP definition is well-reasoned |
| Architecture | HIGH | Token vending machine pattern is well-established; existing codebase provides strong precedent; all data flows are fully traced including error paths |
| Pitfalls | HIGH | Multiple sources confirm the domain-wide delegation two-console trap; base64url encoding trap is documented in Gmail API guides; all pitfalls have clear, testable prevention strategies |

**Overall confidence:** HIGH

### Gaps to Address

- **Token caching thread safety:** FastAPI runs async; the in-memory token cache (module-level dict) is safe for single-threaded synchronous request handling but needs confirmation if the server uses async handlers with concurrent requests. Validate during Phase 1 implementation.
- **`host.docker.internal` on Linux Docker:** Auth server binding to `127.0.0.1` works on Docker Desktop for Mac. If the project ever moves to Linux Docker, `host.docker.internal` behavior differs and firewall rules may be needed. Document as a known limitation; not a gap to resolve now.
- **Gmail API quota under agent use:** The 250 quota units/user/second limit is unlikely to be hit by a single-user agent, but batch inbox reads (fetching headers for 20+ messages sequentially) could approach it. Research quota impact if the agent develops inbox-scanning patterns. Use `format=metadata` for listing to minimize quota cost.
- **Minimal scope selection:** Research recommends `gmail.readonly` for reading and `gmail.send` for sending rather than the broader `gmail.modify`. The Admin Console authorization must exactly match the scopes the skill actually requests. Document which scope is used for which operation to prevent mismatch.

## Sources

### Primary (HIGH confidence)
- [google-auth PyPI](https://pypi.org/project/google-auth/) — version 2.49.1 confirmed 2026-03-12; compatibility and API surface
- [google.oauth2.service_account docs](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.service_account.html) — `Credentials.from_service_account_file()`, `.with_subject()`, `.with_scopes()`
- [Gmail REST API reference](https://developers.google.com/workspace/gmail/api/reference/rest) — endpoint URLs, parameters, formats, quota units per operation
- [Google OAuth2 server-to-server guide](https://developers.google.com/identity/protocols/oauth2/service-account) — domain-wide delegation JWT flow
- [Google Workspace Admin: Domain-wide delegation setup](https://support.google.com/a/answer/162106?hl=en) — two-console setup requirement, scope string format
- [Domain-wide delegation best practices](https://support.google.com/a/answer/14437356?hl=en) — security recommendations
- [Google: Best practices for service account keys](https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys) — key storage guidance
- [Gmail API: Create and send email messages](https://developers.google.com/workspace/gmail/api/guides/sending) — base64url encoding requirement
- [Gmail API Usage Limits and Quotas](https://developers.google.com/workspace/gmail/api/reference/quota) — quota unit costs per endpoint

### Secondary (MEDIUM confidence)
- [GitHub: google-auth #1785](https://github.com/googleapis/google-auth-library-python/issues/1785) — confirms ADC does not work for domain-wide delegation; explicit credential management required
- [GitHub: googleapis/google-api-python-client #984](https://github.com/googleapis/google-api-python-client/issues/984) — `Precondition check failed` root cause confirmed as missing subject

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
