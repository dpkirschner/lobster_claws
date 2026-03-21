# Stack Research

**Domain:** Multi-agent identity + Google Drive skill for Python CLI monorepo
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

This milestone requires zero new dependencies. The existing stack (httpx, argparse, ClawsClient, google-auth, FastAPI) already provides everything needed for both features. The multi-agent identity feature is a data-plumbing change (adding `subject` to token requests), and the Drive skill follows the exact same pattern as Gmail and Calendar: raw httpx calls to Google REST APIs with bearer tokens from the auth server.

## Recommended Stack Changes

### New Dependencies: None

No new packages are needed. Here is why:

| Capability | Existing Solution | Why Sufficient |
|------------|-------------------|----------------|
| Drive list/download/upload | httpx >=0.28 (already in claws-common) | Drive REST API v3 is plain HTTP. Gmail and Calendar already use raw httpx for Google APIs. |
| Auth token with per-request subject | google-auth >=2.49 (already in auth server) | `Credentials.with_subject()` is a built-in method on service account credentials. |
| CLI argument parsing | argparse (stdlib) | `--as` flag is one `add_argument` call per skill. |
| File upload multipart | httpx >=0.28 (already in claws-common) | Manual multipart/related body construction is ~10 lines. |
| File download streaming | httpx >=0.28 (already in claws-common) | `httpx.stream()` handles binary downloads. |

### Existing Stack (Unchanged)

| Technology | Version | Package | Role in v1.3 |
|------------|---------|---------|--------------|
| httpx | >=0.28 | claws-common | HTTP client for auth server + Drive REST API |
| FastAPI | >=0.135 | google-auth-server | Auth server framework (add `subject` to TokenRequest model) |
| google-auth | >=2.49 | google-auth-server | `with_subject()` for per-agent delegation |
| pydantic | (via FastAPI) | google-auth-server | TokenRequest model gets optional `subject` field |
| argparse | stdlib | all skills | `--as` flag added to gmail, calendar, drive CLIs |
| hatchling | build-system | all packages | No change |
| pytest + pytest-httpx | dev deps | all packages | No change |
| ruff | dev dep | all packages | No change |

## Feature-Specific Stack Details

### Multi-Agent Identity (--as flag)

**Auth server change**: Add optional `subject: str | None = None` to the `TokenRequest` Pydantic model. When present, use `base_creds.with_subject(subject)` before `with_scopes()`. When absent, fall back to `GOOGLE_DELEGATED_USER` (current behavior).

**Key API** (google-auth library, HIGH confidence):
```python
# google.oauth2.service_account.Credentials
creds = base_creds.with_subject("agent@domain.com")  # Returns NEW Credentials instance
creds = creds.with_scopes(["https://..."])
creds.refresh(transport_request)
```

`with_subject()` returns a new `Credentials` instance -- it does not mutate. This means `base_creds` stays untouched and the cache key must include the subject.

**Skill-side change**: Each Google skill's `get_access_token()` function adds `subject` to the POST body when `--as` is provided. The flow is: CLI `--as` arg -> function parameter -> POST `/token` body -> auth server `with_subject()`.

**Cache key change**: Currently `frozenset(scopes)`. Must become `(subject_or_default, frozenset(scopes))` tuple to avoid returning Agent A's token to Agent B.

### Google Drive Skill

**API**: Google Drive REST API v3. No client library needed -- raw httpx with bearer token, identical pattern to Gmail and Calendar.

**Base URL**: `https://www.googleapis.com/drive/v3`

**Scope**: `https://www.googleapis.com/auth/drive` -- the full read/write scope. Using `drive.file` would limit access to files created by the app, which is too restrictive for a general-purpose Drive skill. The service account with domain-wide delegation already constrains access per-user via the subject field.

**Endpoints needed**:

| Operation | Method | URL | Notes |
|-----------|--------|-----|-------|
| List files | GET | `/drive/v3/files` | `q` param for search, `pageSize`, `fields` for sparse response |
| Download file | GET | `/drive/v3/files/{id}?alt=media` | Returns raw bytes. For Google Docs: use `/files/{id}/export?mimeType=...` |
| Upload file | POST | `/upload/drive/v3/files?uploadType=multipart` | multipart/related: JSON metadata + file bytes |

**Download output**: Write bytes to stdout or a specified `--output` file path. The agent can pipe stdout to a file. For Google Workspace documents (Docs, Sheets, Slides), the `export` endpoint converts to a requested format (PDF, DOCX, etc.).

**Upload implementation**: httpx does not have built-in `multipart/related` support (its `files=` parameter produces `multipart/form-data`). Two options:

1. **Manual multipart/related body** (~10 lines): Construct boundary, JSON metadata part, file bytes part. Simple and no dependencies.
2. **Two-step upload**: POST metadata to create file, then PATCH with `uploadType=media` to add content. More HTTP calls but avoids manual multipart construction.

Recommend option 1 (manual construction) because it matches how Google's own docs show the format, and it is a single HTTP call.

### New Package: claws-drive

```toml
# skills/drive/pyproject.toml
[project]
name = "claws-drive"
version = "0.1.0"
description = "Google Drive skill for Lobster Claws"
requires-python = ">=3.12"
dependencies = ["claws-common"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.entry-points."claws.skills"]
drive = "claws_drive.cli:main"

[tool.uv.sources]
claws-common = { workspace = true }
```

Dependencies: only `claws-common` (which brings httpx). Same as Gmail and Calendar.

## Token Vending vs API Proxy Architecture

**Important context**: The v1.1 research recommended the auth server as an API proxy (making Gmail API calls on behalf of skills). However, the actual implementation chose **token vending** instead -- the auth server mints tokens via `POST /token`, and skills call Google APIs directly with those tokens using raw httpx.

This is the correct pattern for Drive too. The Drive skill will:
1. Call `POST /token` on auth server (via ClawsClient) with Drive scope and optional subject
2. Use the returned bearer token to call Drive REST API directly (via raw httpx)

This matches Gmail (`gmail.py` calls `get_access_token()` then uses `_gmail_get`/`_gmail_post`) and Calendar (same pattern).

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Raw httpx for Drive API | google-api-python-client | Gmail and Calendar already use raw httpx. Adding google-api-python-client would introduce ~6 transitive deps (httplib2, protobuf, uritemplate, google-api-core, google-auth-httplib2, googleapis-common-protos). Contradicts "thin CLI" principle. |
| `drive` full scope | `drive.file` narrow scope | `drive.file` only accesses files created by the app or explicitly shared. A general-purpose Drive skill needs to list/download any file the delegated user has access to. |
| `drive` full scope | `drive.readonly` + separate write scope | One scope is simpler. The service account delegation already constrains per-user access. |
| Manual multipart/related | requests-toolbelt | Extra dependency for one upload endpoint. The format is trivial to construct manually. |
| Write bytes to stdout/file | Return base64 in JSON | Binary files can be large. Streaming to stdout or a file path is the Unix way and avoids 33% base64 bloat. |
| Optional `subject` field (default to env var) | Required `subject` field | Breaking change. Existing Gmail/Calendar calls do not pass subject. Default-to-env-var preserves backward compatibility. |

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| google-api-python-client | Heavy (~6 transitive deps), overkill for 3 HTTP endpoints. Contradicts existing pattern of raw httpx. | Raw httpx + bearer token |
| google-auth-httplib2 | Only needed by google-api-python-client. httpx is the HTTP client. | httpx |
| requests (in skills) | Already have httpx. `requests` is only in auth server for google-auth transport. | httpx for all outbound API calls in skills |
| pydrive2 or gdown | Third-party Drive wrappers that assume OAuth user flow. Not compatible with service account delegation. | Direct REST calls |
| Any Google library in container | Container stays thin. All Google auth complexity is on the host. | ClawsClient + raw httpx with bearer token |

## Integration Points

### Auth Server Token Cache Key Update

Current cache key: `frozenset(scopes)`
Required cache key: `(subject or default_subject, frozenset(scopes))`

This is the most critical integration change. Without it, Agent A receives Agent B's cached token when requesting the same scopes. The fix is small (change the cache key type) but forgetting it is a security issue.

### Google Workspace Admin Console

The `https://www.googleapis.com/auth/drive` scope must be added to the service account's domain-wide delegation authorization in Google Workspace Admin > Security > API Controls > Domain-wide Delegation. Without this, token minting for Drive will fail with a 403.

### ClawsClient -- No Changes Needed

The Drive skill calls the auth server via `ClawsClient.post_json()` (same as Gmail/Calendar) and calls Drive API via raw httpx (same as Gmail/Calendar). No new methods needed on ClawsClient.

For downloads, the skill uses `httpx.stream()` directly (not ClawsClient) since ClawsClient.get() returns `.json()` and downloads are binary. This is consistent with how Gmail/Calendar already bypass ClawsClient for Google API calls.

### Workspace Root pyproject.toml Update

Add `"claws-drive"` to `[dependency-groups] dev` and `claws-drive = { workspace = true }` to `[tool.uv.sources]`.

Test paths already covered by `"skills"` in `testpaths`.

## Version Compatibility

| Package | Current Pin | v1.3 Compatible | Notes |
|---------|-------------|-----------------|-------|
| httpx | >=0.28 | Yes | `httpx.stream()` available since 0.23. Multipart support stable. |
| google-auth | >=2.49 | Yes | `with_subject()` available since 2.x. Stable, unchanged API. |
| FastAPI | >=0.135 | Yes | Pydantic model update (optional field) is straightforward. |
| pydantic | (via FastAPI) | Yes | `str | None = None` default works in all recent pydantic v2 versions. |
| Python | >=3.12 | Yes | All syntax used (union types, f-strings, etc.) works. |

## Drive API Scope Authorization

The service account's domain-wide delegation must be updated in Google Workspace Admin to include the Drive scope. Current authorized scopes (from v1.1/v1.2):

| Scope | Added In |
|-------|----------|
| `https://www.googleapis.com/auth/gmail.modify` | v1.1 |
| `https://www.googleapis.com/auth/calendar` | v1.2 |
| `https://www.googleapis.com/auth/drive` | v1.3 (NEW) |

This is a manual admin step, not a code change. Document in setup instructions.

## Sources

- [Google Drive API v3 REST Reference](https://developers.google.com/workspace/drive/api/reference/rest/v3) -- endpoint URLs, methods, response schemas (HIGH confidence)
- [Google Drive files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) -- query parameters, pagination, required scopes (HIGH confidence)
- [Google Drive Upload Guide](https://developers.google.com/drive/api/guides/manage-uploads) -- upload types (simple, multipart, resumable), size limits (HIGH confidence)
- [Google Drive files.get with alt=media](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) -- download mechanism, export for Google Docs (HIGH confidence)
- [Google Drive API Scopes](https://developers.google.com/drive/api/guides/api-specific-auth) -- scope options and sensitivity levels (HIGH confidence)
- Existing codebase: `gmail.py`, `calendar/calendar.py`, `app.py`, `client.py` -- established patterns for token vending + raw httpx (HIGH confidence, direct code review)

---
*Stack research for: v1.3 Multi-Agent Identity + Google Drive*
*Researched: 2026-03-21*
