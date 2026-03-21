# Milestones

## v1.3 Multi-Agent Identity + Google Drive (Shipped: 2026-03-21)

**Phases completed:** 2 phases, 4 plans, 15 commits

**Key accomplishments:**

- Auth server refactored for per-request subject delegation — `with_subject()` per request, subject-free `base_creds`, cache key `(scopes, subject)`
- `--as user@domain.com` flag added to Gmail (4 functions) and Calendar (5 functions) with full backward compatibility
- Google Drive skill with list, download (binary + Google Docs auto-export), upload (multipart/related construction)
- `claws drive` CLI with list/download/upload subcommands and `--as` identity support from day one
- 207 total tests (56 new), zero regressions across 8 packages

---

## v1.2 Google Calendar (Shipped: 2026-03-21)

**Phases completed:** 2 phases, 4 plans, 12 commits, ~1,700 LOC Python in calendar package

**Key accomplishments:**

- Calendar API module with list_events, get_event (read operations with date range support, all-day event handling)
- Calendar write operations: create_event with timed + all-day support, update_event with partial updates, delete_event
- `claws calendar` CLI with 5 subcommands: list (--today/--week/--from/--to/--max), get, create, update, delete
- Reused existing Google auth server on port 8301 — zero auth changes needed, just different scope
- 51 calendar-specific tests (31 API + 20 CLI), 151 total workspace tests

---

## v1.1 Google Integration + Gmail (Shipped: 2026-03-20)

**Phases completed:** 2 phases, 5 plans, 17 commits, ~520 LOC Python added

**Key accomplishments:**

- ClawsClient extended with `post_json()` and `get(params=...)` for JSON API communication
- Google auth token vending server (FastAPI) with service account domain-wide delegation and in-memory token caching
- Startup validation that mints a real token to verify delegation before accepting requests
- Launchd plist for auth server auto-start on boot, bound to 127.0.0.1:8301
- Gmail API module with inbox listing, message reading (recursive MIME tree walking), email sending (base64url RFC 2822), and search
- `claws gmail` CLI with inbox/read/send/search subcommands, --cc/--bcc/--max flags, stdin body support

---

## v1.0 MVP (Shipped: 2026-03-18)

**Phases completed:** 3 phases, 7 plans, 38 commits, 904 LOC Python

**Key accomplishments:**

- Monorepo foundation with uv workspaces and hatchling build backend for dual pip/uv compatibility
- Shared client library (claws-common) with Docker-aware host resolution, service-named HTTP errors, flush-safe structured output
- Whisper transcription server (FastAPI + mlx-whisper) with model preloading and MLX cache clearing on Apple Silicon
- Transcribe CLI skill with --model and --format flags, proxying through ClawsClient
- launchd plist for whisper server auto-start and crash recovery on Mac mini
- Meta-CLI with entry-point skill discovery and 233-line project README

---
