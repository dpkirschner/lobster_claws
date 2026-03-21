# Project Research Summary

**Project:** Lobster Claws v1.3 — Multi-Agent Identity + Google Drive Skill
**Domain:** Python CLI monorepo, Google Workspace API integration, Docker container skills
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

The v1.3 milestone adds two tightly coupled capabilities: per-agent Google Workspace identity (the `--as` flag) and a new Google Drive skill. Both features follow patterns already established by the Gmail and Calendar skills, meaning this milestone is primarily a targeted extension of proven architecture rather than greenfield development. Zero new dependencies are required. The recommended approach is to change the auth server first (making `subject` optional in `POST /token`, fixing the cache key), then update existing skills (Gmail, Calendar) to thread the flag, and finally build the Drive skill with the identity mechanism already proven.

The central risk is a silent security bug: if the token cache key is not updated to include the `subject` field, agents requesting the same scopes will receive each other's access tokens. This produces no errors — it silently routes Agent A to Agent B's data. This fix must be atomic with the auth server subject support change and must never ship separately. A secondary risk is that `base_creds` in the auth server currently bakes the delegation subject in at startup; this must be refactored to store subject-free base credentials and call `with_subject()` per request.

The Drive skill introduces two HTTP patterns not present in Gmail or Calendar: binary file downloads (as opposed to JSON responses) and `multipart/related` upload bodies (as opposed to JSON POST bodies). Google Workspace documents (Docs, Sheets, Slides) also require a separate `files.export` endpoint rather than `files.get?alt=media`. These differences are well-documented and testable, making Phase 3 MEDIUM risk rather than HIGH — the patterns are new to this codebase but not novel in the broader ecosystem.

## Key Findings

### Recommended Stack

No new packages are needed for v1.3. The existing stack — httpx, FastAPI, google-auth, pydantic, argparse, hatchling — provides everything required. The auth server already has `google-auth >= 2.49` which includes `Credentials.with_subject()`. Skills already use raw httpx for Google API calls. Drive's REST API v3 is plain HTTP, consistent with the Gmail and Calendar approach.

The one new artifact is a `claws-drive` package (`skills/drive/`) with a single dependency on `claws-common`. It registers via the `claws.skills` entry point group, exactly as other skills do.

**Core technologies:**
- httpx >= 0.28: HTTP client for auth server calls and Google API calls — already present in claws-common
- google-auth >= 2.49: `with_subject()` for per-request delegation — already on auth server host
- FastAPI + pydantic: Auth server framework; `TokenRequest` model gets optional `subject: str | None = None`
- argparse (stdlib): `--as` flag added to parent parser in Gmail, Calendar, and Drive CLIs
- hatchling: Build backend for new `claws-drive` package — no change from other skills

### Expected Features

**Must have (table stakes — v1.3 launch):**
- Auth server `POST /token` accepts optional `subject` field and defaults to `GOOGLE_DELEGATED_USER` — backward compatible, all existing calls work unchanged
- Token cache keyed by `(subject, frozenset(scopes))` — prevents cross-agent token collision
- `--as user@domain.com` on Gmail (all subcommands) — threads subject through to token request
- `--as user@domain.com` on Calendar (all subcommands) — identical pattern to Gmail
- `claws drive list` with optional `--query` and `--max` — GET /drive/v3/files
- `claws drive download <fileId>` with transparent export for Google Workspace documents
- `claws drive upload --name <name> <filepath>` — multipart/related upload
- `--as user@domain.com` on Drive (all subcommands)
- Structured JSON output, `handle_drive_error()`, and full test suite for Drive

**Should have (add when agent usage patterns emerge — v1.3.x):**
- `--folder <folderId>` filter on `drive list` — folder-scoped browsing
- `--mime-type` filter on `drive list` — type-specific searches
- Upload to specific folder via `--folder` — organized output
- `claws drive info <fileId>` — metadata without downloading content

**Defer (v2+):**
- Shared drive support (`--shared` flag)
- Resumable upload (only needed for files > 5 MB)
- Move/copy/rename operations
- Folder creation
- Download format selection (`--format`)

### Architecture Approach

The architecture is a strict two-tier pattern: thin CLIs in Docker containers call the host-side auth server for tokens (via `ClawsClient`), then call Google APIs directly using raw httpx with bearer tokens. The identity change extends this pattern by adding a `subject` dimension to the token request without changing any transport layer. The Drive skill introduces the same two-tier separation as Gmail/Calendar, with two implementation differences: binary response handling for downloads and manual `multipart/related` body construction for uploads.

**Major components:**
1. **google-auth-server** (modified) — accepts optional `subject` in `TokenRequest`, stores subject-free `base_creds`, mints per-request delegated credentials via `with_subject().with_scopes()`, caches by `(subject, scopes)` tuple
2. **claws-gmail + claws-calendar** (modified) — `get_access_token(subject)` threads the `--as` CLI arg through every public API function to the token POST body
3. **claws-drive** (new) — `drive.py` API module + `cli.py` with list/download/upload subcommands, `--as` built in from the start, full test suite

### Critical Pitfalls

1. **Token cache key missing subject** — If the cache key remains `frozenset(scopes)`, two agents requesting the same scope receive the same token. Agent A silently reads Agent B's data. Fix: change to `(frozenset(scopes), effective_subject)` in the same commit that adds subject support. Never ship one without the other.

2. **`base_creds` has subject baked in at startup** — The current auth server calls `from_service_account_file(key_path, subject=subject)` at startup. With multi-subject support, `with_scopes()` alone preserves the startup subject; you must also call `with_subject()` per request. Fix: store credentials without subject at startup; chain `with_subject(effective_subject).with_scopes(scopes)` per request.

3. **`--as` flag parsed but not threaded to API modules** — argparse receives `--as` in `cli.py` but `get_access_token()` in `gmail.py`/`calendar.py` takes no arguments. Eight+ function signatures need `subject: str | None = None` added. Fix: start with `get_access_token()`, then each public API function; verify with a test that asserts the mock auth server receives the `subject` field.

4. **Drive download vs export — two separate code paths** — `files.get?alt=media` works for binary files but returns an error for Google Workspace documents (Docs, Sheets, Slides). Must detect `application/vnd.google-apps.*` MIME types and route to `files.export`. Fix: fetch metadata first, branch on MIME type, handle transparently without requiring the caller to know the file type.

5. **Drive upload requires `multipart/related`, not `multipart/form-data`** — Drive's upload API requires a manually constructed two-part body: JSON metadata first, file bytes second, with `Content-Type: multipart/related; boundary=...`. Fix: use raw httpx directly for uploads, matching the pattern in gmail.py/calendar.py for external Google API calls.

## Implications for Roadmap

Based on research, the dependency graph is clear and dictates a strict build order. Nothing in Phase 2 or Phase 3 can work without Phase 1.

### Phase 1: Auth Server Identity + Existing Skill Updates

**Rationale:** Every downstream feature depends on the auth server accepting a per-request `subject`. This phase also fixes the cache key security bug, which must be atomic with the subject feature. Updating Gmail and Calendar to use `--as` validates the end-to-end flow before new code is written.

**Delivers:** Auth server with per-agent identity; Gmail and Calendar with `--as` flag; all existing tests continue to pass.

**Addresses:** Auth server `subject` field, token cache key, `--as` on Gmail, `--as` on Calendar, backward compatibility.

**Avoids:** Token cache cross-agent collision (Pitfall 1), `base_creds` subject baked in (Pitfall 2), backward compatibility break, `--as` not threaded to API modules (Pitfall 3), argparse `dest="as_user"` keyword conflict.

**Risk:** LOW. Well-scoped changes to existing files with strong test coverage.

### Phase 2: Google Drive Skill

**Rationale:** By this point, the identity mechanism is proven and the `--as` pattern is established in two existing skills. Drive can be built against a working auth server with no ambiguity about how identity flows. The new HTTP patterns (binary downloads, multipart/related uploads) are the main implementation challenges.

**Delivers:** `claws drive list`, `claws drive download`, `claws drive upload`, all with `--as` support. New `claws-drive` workspace member registered via entry point.

**Addresses:** All Drive table-stakes features from the MVP definition.

**Implements:** New `claws-drive` package following `claws-gmail` / `claws-calendar` package structure exactly.

**Avoids:** Drive download vs export ambiguity (Pitfall 4), export 10 MB limit error handling, upload multipart format (Pitfall 5), N+1 API calls on list (use `fields` param).

**Risk:** MEDIUM. Binary downloads and multipart/related uploads are new patterns in this codebase. Requires careful test coverage of both the binary path and the Google Workspace document export path.

### Phase Ordering Rationale

- Auth server must be first because `ClawsClient.post_json("/token", body)` is the foundation of every Google skill. Nothing can be tested end-to-end without it.
- Updating existing skills (Gmail, Calendar) before writing new code (Drive) validates the pattern works and catches any issues with the auth server change under real conditions.
- Drive skill is last because it is new code with no blockers once identity is working. Building it last means the `--as` pattern is mature and tested before being applied to harder HTTP patterns.

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1:** Auth server and existing skill changes are surgical and well-understood. The pattern is already proven. All changes are covered by existing tests. No additional research needed.

Phases needing careful task design during planning (not a full research phase):
- **Phase 2:** Drive download binary path and `multipart/related` upload body are the only novel elements. Task plans should explicitly account for MIME type routing logic and manual multipart construction. No additional research phase needed — STACK.md and PITFALLS.md cover these in sufficient detail.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies confirmed by direct codebase inspection; all required APIs exist in current versions |
| Features | HIGH | Based on official Google Drive API v3 documentation and cross-referenced with existing Gmail/Calendar patterns |
| Architecture | HIGH | Based on direct inspection of `app.py`, `gmail.py`, `calendar.py`; immutable credentials pattern confirmed against google-auth docs |
| Pitfalls | HIGH | Critical bugs (cache key, base_creds subject) identified from actual code line numbers; all API-level pitfalls confirmed against official documentation |

**Overall confidence:** HIGH

### Gaps to Address

- **Drive API scope in Google Workspace Admin:** The `https://www.googleapis.com/auth/drive` scope must be added to the service account's domain-wide delegation authorization in Google Workspace Admin > Security > API Controls. This is a manual admin step that cannot be automated. Must be documented as a prerequisite in Phase 2 task plans.

- **Export format coverage:** The hardcoded export MIME type mapping (`document -> text/plain`, `spreadsheet -> text/csv`, `presentation -> application/pdf`) covers the common cases but not all Google Workspace types (Forms, Sites, Drawings). These edge cases are acceptable for MVP but should be noted in task plans so error handling is implemented rather than producing silent failures.

- **Token cache TTL:** Research did not verify whether the current token cache has expiry logic. If cached tokens are never evicted, long-running auth server processes will accumulate stale tokens. This is existing behavior (not new to v1.3) but worth confirming during Phase 1 implementation.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `servers/google-auth/src/google_auth_server/app.py` — current auth server structure, cache key, credential flow
- Existing codebase: `skills/gmail/src/claws_gmail/gmail.py` — token acquisition pattern
- Existing codebase: `skills/calendar/src/claws_calendar/calendar.py` — confirms identical pattern to Gmail
- [Google Drive API v3 REST Reference](https://developers.google.com/workspace/drive/api/reference/rest/v3) — endpoint URLs, methods, response schemas
- [Google Drive files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) — query parameters, pagination, fields
- [Google Drive Upload Guide](https://developers.google.com/drive/api/guides/manage-uploads) — upload types, multipart/related format
- [Google Drive files.get with alt=media](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) — download, export for Google Docs
- [Google Drive API Scopes](https://developers.google.com/drive/api/guides/api-specific-auth) — scope options and sensitivity
- [Google Drive files.export reference](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/export) — 10 MB limit
- [Google Workspace MIME types](https://developers.google.com/workspace/drive/api/guides/mime-types) — `application/vnd.google-apps.*` types
- [google-auth Python library: service_account module](https://google-auth.readthedocs.io/en/master/reference/google.oauth2.service_account.html) — `with_subject()` and `with_scopes()` immutability
- [Domain-wide delegation best practices](https://support.google.com/a/answer/14437356?hl=en) — per-request impersonation
- [Using OAuth 2.0 for Server to Server Applications](https://developers.google.com/identity/protocols/oauth2/service-account) — delegation flow

---
*Research completed: 2026-03-21*
*Ready for roadmap: yes*
