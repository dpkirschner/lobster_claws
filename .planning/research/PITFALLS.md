# Pitfalls Research

**Domain:** Multi-agent identity (`--as` flag) + Google Drive skill for existing claws monorepo
**Researched:** 2026-03-21
**Confidence:** HIGH (based on codebase inspection + official Google documentation)

## Critical Pitfalls

### Pitfall 1: Token Cache Key Does Not Include Subject

**What goes wrong:**
The current auth server caches tokens with `cache_key = frozenset(req.scopes)` (line 91 of `app.py`). When `--as` adds per-agent identity, two agents requesting the same scopes (e.g., both requesting `gmail.modify`) get the same cached token -- which belongs to whichever agent requested first. Agent A silently reads Agent B's Gmail. This is a data access crossover bug that produces no errors.

**Why it happens:**
The cache was designed when only one subject existed (set via `GOOGLE_DELEGATED_USER` at startup). Scopes were the only varying dimension. Adding a second dimension (subject) without updating the cache key is the single most predictable bug in this milestone.

**How to avoid:**
Change the cache key to `(frozenset(scopes), subject)` where `subject` is the requested user or the default. Do this in the same commit that adds subject support to `POST /token` -- never ship one without the other.

**Warning signs:**
- Agent A sees Agent B's email/calendar/files
- Tests pass when only testing one agent at a time but fail with interleaved agents
- "Works in dev" (single user) but breaks in production (multiple agents)

**Phase to address:**
Phase 1 (Auth server identity changes) -- this is the first thing to fix, before any skill changes.

---

### Pitfall 2: `base_creds` Has Subject Baked In at Startup

**What goes wrong:**
The current auth server creates `base_creds` at startup with `subject=subject` baked into `from_service_account_file()` (line 44-45 of `app.py`). The `POST /token` handler calls `base_creds.with_scopes()` but never calls `with_subject()`. Since google-auth's `with_subject()` and `with_scopes()` both return NEW credentials objects (immutable pattern), adding a `subject` field to the token request without also calling `with_subject()` will silently continue using the startup subject for every request.

**Why it happens:**
The google-auth library uses immutable credentials. `with_scopes()` returns a new object that carries forward the original subject. To change the subject, you must call `with_subject()` explicitly. The current code path is: `base_creds.with_scopes(scopes)` which preserves the startup subject regardless of what `subject` was in the request body.

**How to avoid:**
Store `base_creds` WITHOUT a default subject at startup. The lifespan should create credentials with `from_service_account_file(key_path)` (no `subject=`). The startup validation can use `base_creds.with_subject(default_user)` for the health check. Per-request: `base_creds.with_subject(requested_subject).with_scopes(scopes)`.

**Warning signs:**
- All `--as` requests return data for the startup user regardless of the `--as` value
- No error is raised -- the token mints successfully but for the wrong user
- Health endpoint always shows the env var user as "subject"

**Phase to address:**
Phase 1 (Auth server identity changes) -- fundamental to the identity architecture.

---

### Pitfall 3: `--as` Flag Parsed but Not Threaded to Token Acquisition

**What goes wrong:**
Gmail and Calendar both have a `get_access_token()` function that takes zero arguments and calls the auth server with hardcoded scopes and no subject. Adding `--as` to the CLI argument parser but forgetting to pass the subject through the entire call chain means the flag is silently ignored. Every operation uses the default user.

**Why it happens:**
The `--as` flag is parsed in `cli.py`, but `get_access_token()` lives in the API module (`gmail.py`, `calendar.py`). Every public function in the call chain (`list_inbox`, `read_message`, `send_message`, `list_events`, `get_event`, `create_event`, `update_event`, `delete_event`) needs a `subject` parameter threaded through. That is 8+ function signatures to update across two packages.

**How to avoid:**
Add `subject: str | None = None` to `get_access_token()` first, then to every public API function, then wire the CLI flag. Test with two different subjects in the same test -- assert the mock auth server receives different `subject` values.

**Warning signs:**
- `--as` flag accepted by argparse but all operations use default user's data
- Tests only verify flag is accepted, not that it changes behavior
- `get_access_token()` signature unchanged from v1.2

**Phase to address:**
Phase 1 (after auth server changes, before Drive skill).

---

### Pitfall 4: Drive Download vs Export -- Two Different Code Paths

**What goes wrong:**
Google Drive has two file types requiring different download methods: (1) binary blobs (PDFs, images) use `files.get?alt=media`, and (2) Google Workspace documents (Docs, Sheets, Slides) use `files.export` with an explicit MIME type. Using `files.get?alt=media` on a Google Doc returns an error. A download command handling only one path fails on the other.

**Why it happens:**
Most Drive tutorials show one or the other. Developers implement `alt=media` for binary files, ship it, then discover Google Docs fail. The MIME type `application/vnd.google-apps.document` indicates a Workspace document, but you must check for it explicitly.

**How to avoid:**
In the download command, first fetch file metadata to get the MIME type. If it starts with `application/vnd.google-apps.*`, use `files.export` with an appropriate export MIME type (e.g., `text/plain` for Docs, `text/csv` for Sheets). Otherwise, use `files.get?alt=media`. Handle this transparently -- the user should not need to know which type a file is.

**Warning signs:**
- Download works for uploaded PDFs but fails for Google Docs
- Error: "Export only supports Workspace documents"
- Tests only cover binary file downloads

**Phase to address:**
Phase 2 (Drive skill) -- must be in the initial download implementation.

---

### Pitfall 5: Drive Export Has a Hard 10 MB Limit

**What goes wrong:**
`files.export` has a hard 10 MB limit on exported content. Large Google Docs or Sheets fail or return truncated content. This is easy to miss because test documents are typically small.

**Why it happens:**
The limit is documented but buried. Most test documents are well under 10 MB. The limit only surfaces with real-world spreadsheets or heavily-formatted documents.

**How to avoid:**
Document the 10 MB export limit in CLI help text. When export returns a 403/413 error, surface a clear message: "Document too large to export (10 MB limit)." For MVP this is acceptable -- agents typically read document content, not export massive datasets.

**Warning signs:**
- Export works in tests but fails on production documents
- Truncated content returned without error

**Phase to address:**
Phase 2 (Drive skill) -- handle in error handling.

---

### Pitfall 6: Startup Validation Only Proves One Subject Works

**What goes wrong:**
The current server validates delegation at startup by minting a token for `GOOGLE_DELEGATED_USER`. With multi-agent identity, this proves delegation works for ONE user but not others. The server starts successfully, then `--as other@domain.com` fails at runtime if that user is suspended, doesn't exist, or delegation is misconfigured for their OU.

**Why it happens:**
Domain-wide delegation is configured per-scope in the Workspace admin console, and impersonation works for any active user in the domain. But suspended or deleted users fail. Developers assume startup validation covers all cases.

**How to avoid:**
Keep startup validation for the default user. Add clear error messages at `/token` when delegation fails for a specific subject -- include the subject email in the error so the operator knows which user failed, not just "Failed to mint token."

**Warning signs:**
- Server starts fine but `--as` requests fail with opaque 503 errors
- Error messages say "Failed to mint token after retry" without indicating which subject

**Phase to address:**
Phase 1 (Auth server identity changes) -- error messages must include subject context.

---

### Pitfall 7: Drive Upload Requires Two-Part Multipart Body

**What goes wrong:**
Drive file upload requires metadata (name, parent folder) as JSON AND file content as binary in a single multipart request. Sending only the file bytes creates a file with no name. Sending only metadata creates an empty file. The multipart boundary format is specific: `multipart/related` (not `multipart/form-data`).

**Why it happens:**
The existing `ClawsClient.post_file()` uses `multipart/form-data` (standard web upload). Google Drive's upload API uses `multipart/related` which is a different format requiring manual construction or httpx's lower-level APIs.

**How to avoid:**
Do not use `ClawsClient.post_file()` for Drive uploads. Build the multipart/related body manually: first part is JSON metadata with `Content-Type: application/json`, second part is file content with the file's MIME type. Use httpx directly for this specific endpoint, matching the existing pattern in gmail.py and calendar.py where external Google API calls use raw httpx.

**Warning signs:**
- Uploaded files have "Untitled" as name
- Uploaded files are 0 bytes
- Upload returns success but file metadata is wrong

**Phase to address:**
Phase 2 (Drive skill) -- must be correct from initial implementation.

---

### Pitfall 8: Breaking Backward Compatibility When Subject Becomes Required

**What goes wrong:**
If the auth server's `POST /token` is changed to REQUIRE `subject` in the request body, all existing skill code breaks immediately. Gmail and Calendar skills currently send `{"scopes": [...]}` with no subject field. If the server rejects this with 422 (Pydantic validation error), all skills fail until updated simultaneously.

**Why it happens:**
Natural instinct is to make the new parameter required to enforce correctness. But the auth server and skills are separate packages deployed independently. The server might be updated before skills are.

**How to avoid:**
Make `subject` optional on `TokenRequest` with `subject: str | None = None`. When omitted, fall back to the `GOOGLE_DELEGATED_USER` env var (current behavior). This means existing skill code works without changes and `--as` is purely additive. The env var becomes the default identity.

**Warning signs:**
- All existing tests fail after auth server update
- Skills return 422 errors with "field required" messages
- Simultaneous deploy required across all packages

**Phase to address:**
Phase 1 (Auth server identity changes) -- backward compatibility is a hard requirement.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Simple upload only (no resumable) | Much simpler code, faster to ship | Cannot upload files over 5 MB | MVP -- agents rarely upload large files |
| Default subject from env var when `--as` omitted | Backward compatible, no breaking changes | Implicit behavior may confuse new operators | Always -- explicit default is good UX |
| No per-subject scope restriction | Simpler auth server, any agent can request any scope | Any agent can impersonate any user and access any API | Now -- internal network only, trusted agents |
| Hardcoded export MIME types (text/plain for Docs, text/csv for Sheets) | No user config needed | Cannot export in other formats (PDF, DOCX) | MVP -- add `--format` flag later |
| Duplicated `get_access_token()` per skill module | Each skill is self-contained | Subject threading logic duplicated in gmail.py, calendar.py, drive.py | Acceptable for 3 skills; extract to claws-common if a 4th skill appears |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Auth server `POST /token` | Adding `subject` as query parameter | Add to `TokenRequest` Pydantic model body: `subject: str | None = None` |
| `google-auth` library | Calling `with_scopes()` on credentials that already have subject baked in | Store base credentials WITHOUT subject; chain `with_subject().with_scopes()` per request |
| Drive `files.list` | Omitting `fields` parameter -- returns only `id` and `kind` | Specify `fields=files(id,name,mimeType,size,modifiedTime,parents)` |
| Drive `files.list` | Not handling `nextPageToken` -- only first page returned | For MVP, set `pageSize=100` and document limit; add pagination later |
| Drive download | Using `alt=media` on Google Workspace documents | Check MIME type first; use `files.export` for `application/vnd.google-apps.*` |
| Drive upload | Using `multipart/form-data` (web standard) | Drive uses `multipart/related` -- different format requiring manual construction |
| Drive upload | Forgetting to specify parent folder | Without `parents: ["folder_id"]` in metadata, file goes to user's root Drive |
| `--as` flag on skills | Adding flag to parent parser (before subcommands) | Add to parent parser so it applies to ALL subcommands: `parser.add_argument("--as", dest="as_user")` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Token cache returns wrong user's token (cache key bug) | Silent data crossover -- no performance symptom, just wrong data | Include subject in cache key from day one | Immediately with multi-agent use |
| Minting new token per request when cache key is wrong | 200-500ms latency per CLI call, Google rate limits | Fix cache key to `(frozenset(scopes), subject)` | Immediately with concurrent agents |
| N+1 API calls for Drive file listing | Listing 100 files takes 101 calls if fetching metadata individually | Use `fields` parameter on `files.list` for all metadata in one call | At 50+ files |
| Synchronous file download blocking CLI | CLI hangs during large downloads with no output | Stream response with chunked writes; print progress to stderr | Files over 10 MB |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `--as` allows impersonation of any domain user with no audit trail | Any agent operator can access any user's email, calendar, drive | Log every token request with timestamp, requested subject, scopes, and source IP |
| Allowing `--as` with external domain emails | Confusing errors when delegation fails for non-domain users | Validate `--as` value ends with expected domain before sending to auth server |
| Returning access tokens in error messages | Token leakage in agent logs, stderr | Never include token value in error output; log only subject and scope metadata |
| Drive download path traversal | Agent passes `../../etc/something` as output path | Download to current directory by default; validate output path |
| Cache poisoning via subject | Attacker sends `subject=admin@domain.com` to get admin's token | Acceptable risk -- auth server on 127.0.0.1, internal network only |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `--as` required on every command | Verbose, agents must always specify identity | Make `--as` optional; default to `GOOGLE_DELEGATED_USER` env var |
| Drive download outputs binary to stdout | Terminal corruption, garbled output | Save to file by default (use filename from Drive metadata); only stdout with explicit `--stdout` flag |
| Drive list shows file IDs without names | Opaque identifiers mean nothing to agents | Always include name, MIME type, size, and modified time in list output |
| Inconsistent error format across skills for auth failures | Agent parses gmail errors differently from calendar errors | Centralize delegation error handling pattern -- same format for "auth server down" and "delegation failed for user X" |
| `--as` flag name conflicts with Python keyword | `args.as` is a syntax error | Use `dest="as_user"`: `parser.add_argument("--as", dest="as_user", ...)` |

## "Looks Done But Isn't" Checklist

- [ ] **Token cache key:** Verify cache key includes BOTH scopes AND subject -- test by requesting same scopes for two different subjects and confirming different tokens returned
- [ ] **`base_creds` is subject-free:** Verify stored base credentials do NOT have a hardcoded subject -- assert `app.state.base_creds._subject is None` in tests
- [ ] **`--as` flag threading:** Verify subject reaches auth server -- mock auth server in tests and assert `subject` field present in POST body
- [ ] **Backward compatibility:** All 151 existing tests pass without `--as` flag -- subject defaults to env var value
- [ ] **Drive download for Google Docs:** Test downloading a Google Doc (not just binary) -- verify `files.export` path is used
- [ ] **Drive upload metadata:** Verify uploaded file has correct name and parent folder -- not just that bytes arrived
- [ ] **Error messages include subject:** When token minting fails, verify error says which user failed
- [ ] **`--as` argparse dest:** Verify `dest="as_user"` is used since `as` is a Python keyword -- `args.as` would be a syntax error

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Token cache returns wrong user's data | LOW | Fix cache key, restart auth server (in-memory cache clears on restart) |
| `base_creds` has subject baked in | MEDIUM | Refactor `lifespan()` to store subject-free credentials; update token endpoint to call `with_subject()`; update tests |
| `--as` parsed but not threaded | MEDIUM | Add `subject` parameter to every public function in gmail.py, calendar.py; update all call sites and tests (8+ functions) |
| Drive download uses wrong endpoint for Docs | LOW | Add MIME type check; route to `files.export` for Workspace documents |
| Backward compatibility broken | LOW | Make `subject` optional on `TokenRequest`, default to env var |
| Upload uses wrong multipart format | MEDIUM | Rewrite upload to use `multipart/related`; test against real Drive API |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Token cache key missing subject | Phase 1: Auth server identity | Test: same scopes, different subjects produce different tokens |
| `base_creds` has subject baked in | Phase 1: Auth server identity | Test: `app.state.base_creds._subject is None` |
| Backward compatibility (subject optional) | Phase 1: Auth server identity | All 151 existing tests pass unchanged |
| Startup validation ambiguity | Phase 1: Auth server identity | Error messages include subject email |
| `--as` not threaded to API modules | Phase 1: Update existing skills | Mock auth server receives subject in POST body |
| `--as` argparse dest keyword conflict | Phase 1: Update existing skills | `dest="as_user"` used; `args.as_user` works |
| Drive download vs export | Phase 2: Drive skill | Google Doc download returns content, not error |
| Drive export 10 MB limit | Phase 2: Drive skill | Clear error message on large document export |
| Drive upload multipart format | Phase 2: Drive skill | Uploaded file has correct name and content |
| Drive upload complexity (resumable) | Phase 2: Drive skill (defer) | Ship with simple upload; document 5 MB limit |

## Sources

- Codebase inspection: `servers/google-auth/src/google_auth_server/app.py` lines 44-45 (subject baked into base_creds), line 91 (cache key is scopes-only), lines 104-108 (with_scopes without with_subject)
- Codebase inspection: `skills/gmail/src/claws_gmail/gmail.py` line 20-23 (`get_access_token()` takes no arguments)
- Codebase inspection: `skills/calendar/src/claws_calendar/calendar.py` line 18-21 (`get_access_token()` takes no arguments)
- [google-auth Python library: service_account module](https://google-auth.readthedocs.io/en/master/reference/google.oauth2.service_account.html) -- `with_subject()` and `with_scopes()` immutability pattern (HIGH confidence)
- [Google Drive: Upload file data](https://developers.google.com/drive/api/guides/manage-uploads) -- simple vs resumable upload, multipart/related format (HIGH confidence)
- [Google Drive: files.export reference](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/export) -- 10 MB export limit (HIGH confidence)
- [Google Workspace MIME types](https://developers.google.com/workspace/drive/api/guides/mime-types) -- `application/vnd.google-apps.*` types requiring export (HIGH confidence)
- [Domain-wide delegation best practices](https://support.google.com/a/answer/14437356?hl=en) -- security considerations for impersonation (HIGH confidence)
- [Using OAuth 2.0 for Server to Server Applications](https://developers.google.com/identity/protocols/oauth2/service-account) -- delegation flow (HIGH confidence)

---
*Pitfalls research for: Multi-agent identity + Google Drive skill (v1.3 milestone)*
*Researched: 2026-03-21*
