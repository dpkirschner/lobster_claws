# Architecture Research

**Domain:** Multi-agent identity (`--as` flag) + Google Drive skill integration
**Researched:** 2026-03-21
**Confidence:** HIGH

## System Overview: Current vs Target

### Current Architecture (v1.2)

```
Container (Docker)                    Host (Mac mini)
┌────────────────────────────┐       ┌───────────────────────────────┐
│                            │       │                               │
│  claws gmail inbox         │       │  google-auth-server :8301     │
│  claws calendar list       │       │  ┌───────────────────────┐   │
│                            │       │  │ GOOGLE_DELEGATED_USER │   │
│  get_access_token()        │       │  │ = hardcoded subject   │   │
│    │                       │       │  │                       │   │
│    ├─ClawsClient──POST────────────>│  │ POST /token           │   │
│    │  /token {scopes:[..]} │       │  │ {scopes: [...]}       │   │
│    │                       │       │  │                       │   │
│    v                       │       │  │ base_creds.with_scopes│   │
│  raw httpx + Bearer token  │       │  │ -> always same subject│   │
│    │                       │       │  └───────────────────────┘   │
│    └──────GET/POST────────────────>│  Gmail/Calendar Google APIs  │
│                            │       │                               │
└────────────────────────────┘       └───────────────────────────────┘
```

**Key observation:** The auth server loads `GOOGLE_DELEGATED_USER` once at startup and bakes it into `base_creds` via `Credentials.from_service_account_file(key_path, subject=subject)`. Every token minted delegates as that single user. The cache key is `frozenset(scopes)` with no user dimension.

### Target Architecture (v1.3)

```
Container (Docker)                    Host (Mac mini)
┌────────────────────────────┐       ┌───────────────────────────────┐
│                            │       │                               │
│  claws gmail inbox         │       │  google-auth-server :8301     │
│    --as alice@domain.com   │       │  ┌───────────────────────┐   │
│  claws calendar list       │       │  │ POST /token           │   │
│    --as bob@domain.com     │       │  │ {scopes: [...],       │   │
│  claws drive list          │       │  │  subject: "alice@.."} │   │
│    --as alice@domain.com   │       │  │                       │   │
│                            │       │  │ subject provided?     │   │
│  get_access_token(subject) │       │  │  YES -> use it        │   │
│    │                       │       │  │  NO  -> use env default│  │
│    ├─ClawsClient──POST────────────>│  │                       │   │
│    │  /token {scopes:[..], │       │  │ cache_key = (scopes,  │   │
│    │   subject: "alice@"}  │       │  │             subject)  │   │
│    │                       │       │  └───────────────────────┘   │
│    v                       │       │                               │
│  raw httpx + Bearer token  │       │                               │
│    │                       │       │                               │
│    └──────GET/POST────────────────>│  Gmail/Calendar/Drive APIs   │
│                            │       │                               │
│  claws drive download      │       │                               │
│    │                       │       │                               │
│    └──────GET alt=media───────────>│  Drive API (binary response) │
│                            │       │                               │
└────────────────────────────┘       └───────────────────────────────┘
```

## What Changes, What Stays

### Unchanged Components

| Component | Why It Stays The Same |
|-----------|----------------------|
| `claws-common/host.py` | Host resolution has nothing to do with identity |
| `claws-common/client.py` | General HTTP wrapper; identity is app-level, not transport-level |
| `claws-common/output.py` | Output formatting unchanged |
| `whisper-server` | Transcription has no Google auth |
| `claws-transcribe` | No Google dependency |
| `claws-cli/main.py` | Meta-CLI discovers skills via entry points; no auth awareness needed |
| launchd plists | Same server management, no new servers |

### Modified Components

| Component | File | Change | Size |
|-----------|------|--------|------|
| **google-auth-server** | `app.py` | Accept optional `subject` in `TokenRequest`, per-subject credential creation, subject-aware cache key | MEDIUM |
| **claws-gmail** | `gmail.py` | `get_access_token()` accepts optional `subject`, passes to token request | SMALL |
| **claws-gmail** | `cli.py` | Add `--as` argument to parent parser, thread through to API functions | SMALL |
| **claws-calendar** | `calendar.py` | Same as gmail: `get_access_token()` accepts `subject` | SMALL |
| **claws-calendar** | `cli.py` | Add `--as` argument to parent parser | SMALL |

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **claws-drive** | `skills/drive/` | Google Drive skill: list, download, upload |

## Detailed Change: Auth Server

### TokenRequest Model

**Current:**
```python
class TokenRequest(BaseModel):
    scopes: list[str]
```

**Target:**
```python
class TokenRequest(BaseModel):
    scopes: list[str]
    subject: str | None = None
```

Adding `subject` as optional with `None` default means existing callers that only send `{"scopes": [...]}` continue to work with zero changes. Full backward compatibility.

### Credential Minting

Currently the server calls `Credentials.from_service_account_file(key_path, subject=subject)` at startup, baking the subject into `base_creds`. Then per-request it calls `base_creds.with_scopes(scopes)`.

The `google-auth` library's `Credentials` object supports `with_subject()` which returns a new `Credentials` instance with a different subject. This is the mechanism to use:

```python
# At startup: store credentials WITHOUT subject baked in
app.state.base_creds = service_account.Credentials.from_service_account_file(key_path)
app.state.default_subject = subject  # from GOOGLE_DELEGATED_USER env var

# Per request:
effective_subject = req.subject or app.state.default_subject
creds = app.state.base_creds.with_subject(effective_subject).with_scopes(list(req.scopes))
creds.refresh(google_auth_transport.Request())
```

**Startup validation** continues using `GOOGLE_DELEGATED_USER` as the default subject. This validates delegation works for at least one user. No need to validate every possible subject at startup. Google's token endpoint rejects delegation for non-existent users with a clear error anyway.

### Cache Key

**Current:**
```python
cache_key = frozenset(req.scopes)
```

**Target:**
```python
effective_subject = req.subject or app.state.default_subject
cache_key = (frozenset(req.scopes), effective_subject)
```

This means `alice@domain.com` requesting `gmail.modify` and `bob@domain.com` requesting `gmail.modify` get separate cached tokens. Correct behavior -- they are different delegated identities.

## Detailed Change: Skill-Side Token Acquisition

### Current Pattern (identical in gmail.py and calendar.py)

```python
def get_access_token() -> str:
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    resp = client.post_json("/token", {"scopes": [SCOPE]})
    return resp["access_token"]
```

### Target Pattern

```python
def get_access_token(subject: str | None = None) -> str:
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    body: dict = {"scopes": [SCOPE]}
    if subject:
        body["subject"] = subject
    resp = client.post_json("/token", body)
    return resp["access_token"]
```

Every API function in the module (`list_inbox`, `read_message`, `list_events`, `create_event`, etc.) gains an optional `subject: str | None = None` parameter that flows through to `get_access_token()`. The change is mechanical: add the parameter, pass it down.

### CLI --as Flag

Add `--as` to the **parent parser** (before subcommands), not to each subcommand individually:

```python
parser = argparse.ArgumentParser(prog="claws-gmail", ...)
parser.add_argument("--as", dest="subject",
                    help="Act as this Google Workspace user (email)")
subs = parser.add_subparsers(dest="command", required=True)
```

**Why parent parser:** Single definition, available to all subcommands. Consistent position in help text. The `--as` flag is skill-level, not subcommand-level. argparse handles this correctly: both `claws gmail --as alice inbox` and `claws gmail inbox --as alice` work.

Then in the dispatch:
```python
messages = list_inbox(max_results=args.max, subject=args.subject)
```

## New Component: Drive Skill

### Package Structure

```
skills/drive/
├── pyproject.toml              # depends on claws-common
├── src/claws_drive/
│   ├── __init__.py
│   ├── cli.py                  # argparse: list, download, upload subcommands
│   └── drive.py                # Drive API client module
└── tests/
    ├── __init__.py
    ├── test_drive_cli.py       # CLI tests (mock drive.py functions)
    └── test_drive.py           # API tests (mock httpx + ClawsClient)
```

### Subcommands

| Command | Google API | HTTP | Notes |
|---------|-----------|------|-------|
| `claws drive list` | `GET /drive/v3/files` | GET, JSON response | Query with `--query` param |
| `claws drive download FILE_ID` | `GET /drive/v3/files/{id}?alt=media` | GET, **binary** response | Write to file with `-o` |
| `claws drive upload FILE_PATH` | `POST /upload/drive/v3/files?uploadType=multipart` | POST, multipart/related | Different base URL than metadata |

### Scope

Use `https://www.googleapis.com/auth/drive` (full access). The `drive.file` scope only covers files created by or shared with the app, which is too restrictive for an agent that needs to access any file in a user's Drive. Since this is a service account with domain-wide delegation on an internal-only network, the broad scope is appropriate and consistent with using `gmail.modify` for Gmail.

### Drive API Differences from Gmail/Calendar

The Drive skill follows the same two-tier HTTP pattern but has two important differences:

**1. Download returns binary, not JSON:**
```python
def download_file(file_id: str, output_path: str, subject: str | None = None) -> dict:
    token = get_access_token(subject)
    resp = httpx.get(
        f"{DRIVE_BASE}/files/{file_id}",
        params={"alt": "media"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,  # larger timeout for big files
    )
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return {"file_id": file_id, "path": output_path, "size": len(resp.content)}
```

**2. Upload uses a different base URL and multipart/related encoding:**
```python
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
```

The upload endpoint (`/upload/drive/v3/files`) is distinct from the metadata endpoint (`/drive/v3/files`). The request body uses `multipart/related` with a JSON metadata part followed by the file bytes. This is Google-specific and different from standard multipart/form-data.

## Data Flow

### Token Flow (Updated)

```
CLI: claws gmail inbox --as alice@domain.com
    |
    v
get_access_token(subject="alice@domain.com")
    |
    v
ClawsClient.post_json("/token", {"scopes": [...], "subject": "alice@..."})
    |
    v
Auth server: base_creds.with_subject("alice@...").with_scopes(scopes)
    |
    v
Google OAuth2: mint token delegating as alice@domain.com
    |
    v
Token returned to skill -> used for Google API calls as alice
```

When `--as` is omitted, `subject` is `None`, the auth server falls back to `GOOGLE_DELEGATED_USER`, and behavior is identical to v1.2.

### Drive Download Flow

```
claws drive download FILE_ID -o /tmp/output.pdf --as alice@domain.com
    |
    v
get_access_token("alice@domain.com")
    |
    v
GET https://www.googleapis.com/drive/v3/files/FILE_ID?alt=media
    Authorization: Bearer ya29...
    |
    v
Binary response -> write to /tmp/output.pdf
    |
    v
result({"file_id": "...", "path": "/tmp/output.pdf", "size": 42381})
```

### Drive Upload Flow

```
claws drive upload /tmp/report.pdf --as alice@domain.com
    |
    v
get_access_token("alice@domain.com")
    |
    v
POST https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart
    Authorization: Bearer ya29...
    Content-Type: multipart/related; boundary=...
    Body: [JSON metadata part] + [file bytes part]
    |
    v
JSON response -> format -> result({"id": "...", "name": "report.pdf"})
```

## Anti-Patterns

### Anti-Pattern: Separate Auth Endpoint Per Subject

**What people might do:** Create `/token/{subject}` or a separate endpoint for per-user tokens.
**Why it's wrong:** Breaks the existing contract. All skills POST to `/token`. Adding a field to the request body is backward compatible and idiomatic.
**Do this instead:** Add `subject` as an optional field to the existing `TokenRequest` model.

### Anti-Pattern: Storing Subject in ClawsClient

**What people might do:** Make ClawsClient subject-aware, storing identity and injecting it into token requests.
**Why it's wrong:** ClawsClient is a general HTTP wrapper used by all skills, including whisper-transcribe which has no concept of Google identity. Mixing identity into the transport layer violates separation of concerns.
**Do this instead:** Keep subject as an application-level parameter in each skill's `get_access_token()` function.

### Anti-Pattern: Subject Validation on Auth Server

**What people might do:** Add an allowed-subjects list or validate that the subject is a real Workspace user before minting.
**Why it's wrong for now:** The auth server uses an "open model" (any skill, any scope) per project decision. Adding subject validation would be inconsistent. Google's token endpoint rejects delegation for non-existent users with a clear error.
**Do this instead:** Let Google's token endpoint be the validator. The existing 503 error response handles this.

### Anti-Pattern: Subcommand-Level --as Flag

**What people might do:** Add `--as` to each subcommand parser individually.
**Why it's wrong:** Repetitive, error-prone (easy to forget on one subcommand), and inconsistent positioning in help output.
**Do this instead:** Add `--as` to the parent parser, before `add_subparsers()`.

## Suggested Build Order

Dependencies dictate order. Each step must be complete and tested before the next begins.

### Phase 1: Auth Server Subject Support

**Why first:** Everything downstream depends on this.

Changes:
- `TokenRequest` gains optional `subject` field
- Credential creation uses `with_subject()` instead of baking subject at startup
- Cache key becomes `(frozenset(scopes), effective_subject)`
- Startup stores `base_creds` without subject, keeps `default_subject` from env
- Startup validation continues using default subject
- All auth server tests updated

Risk: LOW. Well-scoped change to a single file with clear test boundaries.

### Phase 2: Gmail + Calendar --as Flag

**Why second:** Modifies existing tested skills. Low risk. Validates that auth server change works end-to-end.

Changes:
- `get_access_token()` gains optional `subject` parameter in both skills
- `subject` threaded through all API functions (mechanical)
- `--as` added to parent parser in both CLIs
- Existing tests updated (mostly adding `subject=None` to mock assertions)

Risk: LOW. Mechanical changes, existing test coverage catches regressions.

### Phase 3: Drive Skill

**Why last:** New code with no dependencies from existing components. The `--as` pattern is proven before being applied to new code.

Changes:
- New `skills/drive/` package with `drive.py` and `cli.py`
- list, download, upload subcommands
- `--as` flag built in from the start
- Entry point registration
- Full test suite
- Root `pyproject.toml` workspace member addition

Risk: MEDIUM. Download (binary response) and upload (multipart/related encoding) are new HTTP patterns not seen in Gmail/Calendar skills. Need careful testing.

## Sources

- Existing codebase: `servers/google-auth/src/google_auth_server/app.py` (current auth server, cache key structure, credential flow)
- Existing codebase: `skills/gmail/src/claws_gmail/gmail.py` (current token acquisition pattern)
- Existing codebase: `skills/calendar/src/claws_calendar/calendar.py` (confirms identical pattern)
- [Google Drive API scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) -- scope options and restrictions
- [Google Drive downloads](https://developers.google.com/workspace/drive/api/guides/manage-downloads) -- `files.get?alt=media` for binary download
- [Google Drive files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) -- query parameter syntax
- [Google Drive files.get](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) -- metadata and content download
- `google-auth` library: `service_account.Credentials` supports `with_subject()` method for changing delegation target

---
*Architecture research for: v1.3 Multi-Agent Identity + Google Drive*
*Researched: 2026-03-21*
