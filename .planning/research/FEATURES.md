# Feature Research

**Domain:** Multi-agent identity + Google Drive CLI skill for AI agent platform
**Researched:** 2026-03-21
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

The "user" is the OpenClaw AI agent operator. These features are what makes v1.3 complete.

#### Multi-Agent Identity

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `--as user@domain.com` flag on all Google skills | Multiple agents need separate Workspace identities; the entire point of this milestone | LOW | argparse parent parser or per-skill addition; threads through to auth server |
| Auth server accepts `subject` field on POST /token | Domain-wide delegation supports per-request subject via `with_subject()`; current server hardcodes `GOOGLE_DELEGATED_USER` at startup | LOW | Add optional `subject` to `TokenRequest` Pydantic model; use `base_creds.with_subject(subject)` before `with_scopes()` |
| Default subject when `--as` omitted | Existing skills must keep working without `--as`; backward compatibility is non-negotiable | LOW | Fall back to `GOOGLE_DELEGATED_USER` env var (already set) when no subject in request |
| Token cache keyed by (subject, scopes) | Different subjects produce different tokens; current cache uses only scopes as key | LOW | Change cache key from `frozenset(scopes)` to `(subject, frozenset(scopes))` |
| Gmail updated to pass `--as` through | Existing skill becomes multi-agent aware | LOW | Thread `--as` value through `get_access_token(subject=args.as_user)` to auth server POST body |
| Calendar updated to pass `--as` through | Same pattern as Gmail | LOW | Identical change across all subcommands |

#### Google Drive Skill

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `claws drive list` -- list files | Basic file browsing; equivalent to Gmail inbox | LOW | `GET /drive/v3/files` with `fields=files(id,name,mimeType,modifiedTime,size,parents)`, `pageSize`, optional `q` |
| `claws drive list --query` search support | Agents need to find specific files; Drive API supports rich `q` syntax (`name contains 'report'`, `mimeType='...'`) | LOW | Pass `--query` value directly to `q` param on files.list |
| `claws drive download <fileId>` | Agents need file content for analysis/processing | MEDIUM | `GET /drive/v3/files/{id}?alt=media` for binary files; write to temp file, return path in JSON |
| Google Docs/Sheets/Slides export on download | Google-native files cannot be downloaded with `alt=media`; agent will hit these immediately | MEDIUM | Detect `application/vnd.google-apps.*` mimeType, use `files.export` endpoint; export doc->text/plain, sheet->text/csv, slides->application/pdf |
| `claws drive upload --name <name> <filepath>` | Agents need to save outputs (reports, generated files) to Drive | MEDIUM | Multipart upload via `POST /upload/drive/v3/files?uploadType=multipart`; metadata + file content in single request |
| `--as` flag on all drive subcommands | Consistent with other Google skills | LOW | Same pattern as gmail/calendar |
| JSON output via `result()` | Consistent with all existing skills; agent parses stdout JSON | LOW | Already established pattern |
| Error handling via `handle_drive_error()` | Consistent with `handle_gmail_error()` and `handle_calendar_error()` | LOW | Same HTTP status code translation pattern |

### Differentiators (Competitive Advantage)

Features that make the skill more useful than bare minimum, worth building if low-cost.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `--folder <folderId>` filter on list | Agents navigating folder hierarchies need scoped listing | LOW | Add `'<folderId>' in parents` to `q` parameter |
| `--mime-type` filter on list | Agent looking for specific file types (spreadsheets, docs, PDFs) | LOW | Add `mimeType='...'` to `q` parameter |
| Upload to specific folder via `--folder` | Agents need to organize outputs, not dump everything in root | LOW | Set `parents: [folderId]` in file metadata on create |
| `claws drive info <fileId>` | Get file metadata without downloading content (size, owner, modified time, sharing) | LOW | `GET /drive/v3/files/{id}` with metadata fields, no `alt=media` |
| Shared argparse parent for `--as` | DRY: define `--as` once, reuse across gmail/calendar/drive parsers | LOW | `argparse.ArgumentParser(add_help=False)` with just `--as`; each skill uses `parents=[as_parser]` |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Resumable upload | "What about large files?" | Adds significant complexity (session URIs, chunk tracking, retry logic); agent-generated files are small (reports, text, configs) | Simple multipart upload handles files up to 5MB easily; revisit only if agents produce large files |
| Streaming download to stdout | "Pipe file content directly" | Binary files corrupt terminals; large files exhaust memory; breaks JSON output contract | Download to temp file, return file path in JSON; agent reads file separately |
| Watch/push notifications | "Real-time file changes" | Requires webhook endpoint, long-lived connections; agent polls on demand | Agent calls `claws drive list` when it needs to check for changes |
| Shared drive support | "We use shared drives" | `supportsAllDrives=true` adds edge cases; shared drives have different permission model | Start with My Drive only; add `--shared` flag in future milestone |
| Move/copy/rename operations | "Full file management" | Scope creep; each operation is a separate API pattern; agents rarely need these | Can be added in a future milestone via files.update with addParents/removeParents |
| Folder creation | "Organize files" | Agents don't typically create folder hierarchies; adds complexity | Upload to existing folders via `--folder`; manual folder creation sufficient |
| Per-skill scope enforcement on auth server | "Drive skill shouldn't request gmail scopes" | Already decided out of scope in PROJECT.md; internal-only network; adds auth server complexity | Open token model -- any skill requests any scope |
| Agent identity registry/validation | "Validate --as email against a list of known agents" | Over-engineering; delegation itself validates -- Google rejects invalid subjects | Let Google's delegation validation handle it; auth server returns clear error on 403 |
| Centralized `--as` middleware in auth server | "Auth server should enforce which agent is calling" | Skills run in container, auth server on host; no caller identity available on internal HTTP | Each skill passes `--as` through; simplest path |

## Feature Dependencies

```
Auth server subject field (POST /token accepts optional subject)
    |
    +--requires--> TokenRequest model change (add optional subject: str)
    +--requires--> Token cache key update (include subject in key)
    +--requires--> Credential delegation logic (with_subject before with_scopes)
    |
    +--enables--> --as flag on Gmail
    +--enables--> --as flag on Calendar
    +--enables--> --as flag on Drive

Drive list
    +--requires--> Auth server (token with drive scope)
    +--requires--> Drive API client module (new: drive.py)

Drive download
    +--requires--> Drive list (need fileIds + mimeType to know export vs download)
    +--enhances--> Google Docs export (handles native doc types)

Drive upload
    +--requires--> Auth server (token with drive write scope)
    +--independent-of--> Drive download

--as flag on existing skills (Gmail, Calendar)
    +--requires--> Auth server subject field
    +--independent-of--> Drive skill
```

### Dependency Notes

- **Auth server subject field is the foundation**: All `--as` features depend on the auth server accepting a per-request subject. Must be built first.
- **Drive skill and `--as` updates are independent**: They can be built in parallel after auth server changes. Both depend on auth server but not on each other.
- **Google Docs export enhances download**: Not strictly required for binary file download, but agents will encounter Google-native files immediately. Build together.
- **Drive scope**: Use `https://www.googleapis.com/auth/drive` (full access). Single scope for all operations, matching the gmail approach (`gmail.modify` covers read + write). The scope must be authorized in Workspace Admin's domain-wide delegation settings.

## MVP Definition

### Launch With (v1.3)

- [ ] Auth server accepts optional `subject` in POST /token body
- [ ] Token cache keyed by `(subject, scopes)` tuple
- [ ] Default to `GOOGLE_DELEGATED_USER` when no subject provided
- [ ] `--as user@domain.com` on Gmail (all subcommands)
- [ ] `--as user@domain.com` on Calendar (all subcommands)
- [ ] `claws drive list` with optional `--query` and `--max`
- [ ] `claws drive download <fileId>` with auto-export for Google Docs
- [ ] `claws drive upload --name <name> <filepath>`
- [ ] `--as user@domain.com` on Drive (all subcommands)
- [ ] Structured JSON output, error handling, tests

### Add After Validation (v1.3.x)

- [ ] `--folder` filter on list -- when agents start navigating folder trees
- [ ] `--mime-type` filter on list -- when agents need type-specific searches
- [ ] Upload to folder via `--folder` -- when agents need organized output
- [ ] `claws drive info <fileId>` -- when agents need metadata without downloading

### Future Consideration (v2+)

- [ ] Shared drive support (`--shared` flag) -- when multi-team use cases emerge
- [ ] Resumable upload -- only if agents produce files > 5MB
- [ ] Move/copy/rename -- only if agents need file management workflows
- [ ] Folder creation -- only if automated organization is needed
- [ ] Download format selection (`--format pdf`) -- when agents need specific export formats

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Auth server subject field | HIGH | LOW | P1 |
| Token cache key update | HIGH | LOW | P1 |
| `--as` on Gmail | HIGH | LOW | P1 |
| `--as` on Calendar | HIGH | LOW | P1 |
| `claws drive list` | HIGH | LOW | P1 |
| `claws drive download` | HIGH | MEDIUM | P1 |
| Google Docs export | MEDIUM | MEDIUM | P1 |
| `claws drive upload` | HIGH | MEDIUM | P1 |
| `--as` on Drive | HIGH | LOW | P1 |
| `--folder` filter | MEDIUM | LOW | P2 |
| `--mime-type` filter | MEDIUM | LOW | P2 |
| Upload to folder | MEDIUM | LOW | P2 |
| `claws drive info` | LOW | LOW | P2 |
| Shared drives | LOW | MEDIUM | P3 |
| Resumable upload | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.3 launch
- P2: Should have, add when agent usage patterns emerge
- P3: Nice to have, future milestone

## Implementation Patterns (from existing codebase)

The existing Gmail and Calendar skills establish clear patterns. Drive should follow them exactly.

### Established Pattern: Skill Module Structure

| Component | Gmail Example | Drive Equivalent |
|-----------|--------------|------------------|
| API client module | `gmail.py` with `get_access_token()`, `_gmail_get()`, `_gmail_post()` | `drive.py` with `get_access_token()`, `_drive_get()`, `_drive_post()` |
| CLI module | `cli.py` with argparse subcommands | `cli.py` with list/download/upload subcommands |
| Error handler | `handle_gmail_error()` translating HTTP status codes | `handle_drive_error()` same pattern |
| Auth token flow | `ClawsClient.post_json("/token", {"scopes": [SCOPE]})` | Same, with `https://www.googleapis.com/auth/drive` |
| External API calls | Direct httpx with Bearer token header | Same |
| Output | `result()` for success, `fail()`/`crash()` for errors | Same |
| Scope strategy | Single broad scope (`gmail.modify`) | Single broad scope (`drive`) |

### Auth Server Change: Adding Subject Support

Current token request flow:
```python
# In gmail.py / calendar.py
def get_access_token() -> str:
    client = ClawsClient(service="google-auth", port=8301)
    resp = client.post_json("/token", {"scopes": [SCOPE]})
    return resp["access_token"]
```

After `--as` support:
```python
def get_access_token(subject: str | None = None) -> str:
    client = ClawsClient(service="google-auth", port=8301)
    body: dict = {"scopes": [SCOPE]}
    if subject:
        body["subject"] = subject
    resp = client.post_json("/token", body)
    return resp["access_token"]
```

Auth server change (in app.py):
```python
class TokenRequest(BaseModel):
    scopes: list[str]
    subject: str | None = None  # Optional per-request impersonation

# In get_token():
subject = req.subject or app.state.delegated_user
cache_key = (subject, frozenset(req.scopes))
creds = app.state.base_creds.with_subject(subject).with_scopes(list(req.scopes))
```

### Drive-Specific Technical Details

| Concern | Approach |
|---------|----------|
| Download binary files | `GET /drive/v3/files/{id}?alt=media`, write to temp file, return `{"path": "/tmp/...", "name": "...", "size": ...}` |
| Google Docs export | Detect `application/vnd.google-apps.document` etc., use `GET /drive/v3/files/{id}/export?mimeType=text/plain` |
| Export format mapping | `document->text/plain`, `spreadsheet->text/csv`, `presentation->application/pdf`, `drawing->image/png` |
| Upload | `POST /upload/drive/v3/files?uploadType=multipart` with `Content-Type: multipart/related`; first part is JSON metadata, second is file content |
| Drive scope | `https://www.googleapis.com/auth/drive` -- full access for list + download + upload |
| Metadata base URL | `https://www.googleapis.com/drive/v3` |
| Upload base URL | `https://www.googleapis.com/upload/drive/v3` |
| List fields | `fields=files(id,name,mimeType,modifiedTime,size,parents)` to avoid huge response payloads |
| Search syntax | `q` param: `name contains 'report'`, `mimeType='application/pdf'`, `'<folderId>' in parents`, `modifiedTime > '2026-01-01T00:00:00'` |

## Sources

- [Google Drive API v3 files.list](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list) -- parameters, response format, scopes (HIGH confidence)
- [Google Drive API v3 files.get](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get) -- download with alt=media, Google Docs limitation (HIGH confidence)
- [Google Drive API v3 files.create](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create) -- upload types, multipart, max file size (HIGH confidence)
- [Google OAuth2 Service Account Flow](https://developers.google.com/identity/protocols/oauth2/service-account) -- subject/sub field, with_subject() for impersonation (HIGH confidence)
- [Domain-Wide Delegation Best Practices](https://support.google.com/a/answer/14437356?hl=en) -- per-request impersonation guidance (HIGH confidence)
- [Control API Access with Domain-Wide Delegation](https://support.google.com/a/answer/162106?hl=en) -- scope authorization in Workspace Admin (HIGH confidence)

---
*Feature research for: Multi-agent identity + Google Drive CLI skill (v1.3 milestone)*
*Researched: 2026-03-21*
