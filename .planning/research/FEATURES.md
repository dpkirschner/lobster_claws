# Feature Research

**Domain:** Google auth server + Gmail CLI skill for AI agent tooling
**Researched:** 2026-03-19
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

The "user" here is the OpenClaw AI agent invoking `claws gmail <subcommand>`. These features are the minimum for Gmail to be useful as an agent tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Auth server: serve access tokens** | Every Gmail API call needs a Bearer token. The auth server's sole purpose is producing these. | MEDIUM | JWT assertion flow: sign with RS256 private key, POST to `https://oauth2.googleapis.com/token`, cache result for ~55 min. Requires `PyJWT` + `cryptography` for RS256 signing. |
| **Auth server: domain-wide delegation (sub claim)** | Service account alone cannot access a user's mailbox. The `sub` field in the JWT impersonates the target Gmail user. Without this, Gmail API returns 403. | LOW | Single extra field in JWT claim set. The delegated user email is a server config value (one agent = one Gmail identity). |
| **Auth server: health endpoint** | Every claws server exposes `GET /health`. Pattern established by whisper-server. | LOW | Identical pattern to whisper-server. Return status + service name. |
| **Auth server: token caching** | Google tokens last 3600s. Re-requesting on every call wastes time and risks rate limits. | LOW | Cache token in memory, refresh when `expires_at - buffer` is reached. Single-threaded FastAPI makes this trivial (module-level dict or dataclass). |
| **Auth server: launchd plist** | All host servers auto-start via launchd. Established pattern. | LOW | Copy whisper-server plist, change port/paths. |
| **Gmail server: list messages** | The most basic email operation. Agent needs to check what is in the inbox. | MEDIUM | `GET /gmail/v1/users/me/messages?q=in:inbox` returns message IDs, then batch-fetch headers for each. Pagination via `nextPageToken`. Server must handle both calls and merge results. |
| **Gmail server: read message content** | After listing, agent needs to read actual message bodies. | MEDIUM | `GET .../messages/{id}?format=full` returns nested MIME payload. Server must extract plain text from `payload.parts` tree (recursive, multipart messages have nested parts). |
| **Gmail server: send email** | Core capability -- agent needs to send emails on behalf of the user. | MEDIUM | `POST .../messages/send` with base64url-encoded RFC 2822 message. Server must construct MIME message from structured input (to, subject, body). |
| **Gmail server: search by query** | Gmail's killer feature. Agent should search by sender, subject, date, labels. | LOW | Same list endpoint but with `q` parameter. Gmail search syntax is powerful: `from:x subject:y after:2024/01/01 has:attachment`. Pass through from CLI. |
| **Gmail server: structured output** | Agent needs parseable JSON, not raw Gmail API payloads with nested MIME trees. | MEDIUM | Server-side transformation: extract From, To, Subject, Date, snippet, plain-text body from Gmail's nested payload format into flat JSON. |
| **Gmail CLI: subcommands** | Agent invokes `claws gmail inbox`, `claws gmail read <id>`, `claws gmail send`, `claws gmail search <query>`. Subcommand pattern matches how agents think about distinct actions. | MEDIUM | argparse with subparsers. Each subcommand maps to one Gmail server endpoint. Follows existing claws-transcribe pattern but with multiple operations. |
| **ClawsClient: post_json method** | Current ClawsClient only has `get` and `post_file`. Gmail skill needs to POST JSON bodies (for send). | LOW | ~15 lines following existing error-handling pattern. |
| **ClawsClient: get with query params** | Current `get()` takes only a path. Gmail search needs query parameters passed to the server. | LOW | Add `**params` to existing `get()`, pass as `params=` to httpx. |

### Differentiators (Competitive Advantage)

Features that make this agent Gmail integration notably better than the bare minimum.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Auth server: multi-scope token support** | Request tokens with different scope sets (gmail.readonly vs gmail.send vs gmail.modify). Future skills (Calendar, Drive) get auth for free with zero new server code. | LOW | Scope list comes from query param on token request. Server signs JWT with requested scopes. Already decided as "open token model" in PROJECT.md. |
| **Gmail: thread view** | Agents often need conversation context, not isolated messages. Thread grouping gives coherent email history. | LOW | `GET .../threads/{id}` returns all messages in a thread. Minimal extra work since message parsing already exists. |
| **Gmail: attachment metadata** | Agent can see what attachments exist without downloading them. Useful for triage ("you got a PDF from X"). | LOW | Attachment metadata already present in message payload parts. Just surface `filename`, `mimeType`, `size` fields during payload flattening. |
| **Gmail: label filtering** | Filter by label (INBOX, SENT, STARRED, custom labels). More precise than search query alone. | LOW | `labelIds` parameter on messages.list. Simple pass-through. |
| **Gmail: reply-to support** | Maintain email thread continuity by setting `In-Reply-To` and `References` headers when sending. | MEDIUM | Requires fetching the original message's `Message-ID` header, then setting reply headers in the outgoing MIME message. Agent sends `--reply-to <message_id>`. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **OAuth2 web flow (3-legged)** | "More standard" auth | Requires browser interaction, refresh token storage, token rotation. Service account + delegation is set-once, no user interaction, no expiring refresh tokens. | Domain-wide delegation. One-time admin console setup, then fully automated forever. |
| **google-api-python-client dependency** | "Official" Google library | Pulls in google-auth, google-auth-httplib2, uritemplate, and httplib2 -- a parallel HTTP stack alongside httpx. Heavy, unnecessary when you only need 4 REST endpoints. | Direct REST calls via httpx. JWT signing needs only PyJWT + cryptography. Gmail API is simple REST with Bearer tokens. Matches existing "thin wrapper" pattern. |
| **Attachment download** | Agent might want to "read" attachments | Large binary downloads through the server proxy are slow, and the agent cannot meaningfully process most attachment types (PDFs, images) without additional tools. Opens door to memory/storage issues. | List attachment metadata only. Download can be added per-type when a consuming skill exists (e.g., a future PDF-reader claw). |
| **Email deletion** | Agent could clean up inbox | Destructive, irreversible operation. Gmail's `DELETE` is permanent (bypasses trash). An AI agent deleting emails is a trust/safety risk. | Use trash (recoverable) if needed at all, but even trash should be deferred until trust is established with the agent. |
| **Draft management** | Agent could prepare emails for human review | Adds significant complexity (create, update, list, send drafts -- 4 new endpoints). For an autonomous agent, direct send is the right pattern. Drafts add a human-in-the-loop step that does not fit this architecture. | Direct send. If human review is needed, that is a higher-level agent concern, not a skill concern. |
| **Per-skill scope enforcement on auth server** | Security best practice | Over-engineering for a single-user, internal-network-only system. Adds ACL management, skill identity verification, config complexity. | Open token model (any skill requests any scope). Already decided in PROJECT.md. Revisit only if the system ever serves multiple users or untrusted skills. |
| **Real-time push notifications (Gmail watch)** | Know about new emails instantly | Requires a public webhook URL (impossible from a Mac mini behind NAT without tunneling), or Pub/Sub subscription (Google Cloud overhead). | Agent calls `claws gmail inbox` when it wants to check email. On-demand, not push. The agent decides when to look. |
| **HTML email rendering** | Show rich email content | Agent processes text, not HTML. Extracting text/plain is sufficient. HTML parsing adds complexity (sanitization, link extraction) for minimal agent value. | Return text/plain body. Include snippet (first ~200 chars) from Gmail API as fallback when text/plain part is missing. |

## Feature Dependencies

```
[ClawsClient enhancements (post_json, get with params)]
    └──required by──> [Gmail skill CLI]

[Auth server (token serving + delegation + caching)]
    └──required by──> [Gmail server (needs Bearer tokens for every API call)]
                          └──required by──> [Gmail skill CLI]

[Auth server: launchd plist]
    └──requires──> [Auth server working correctly]

[Gmail server: read message]
    └──requires──> [Gmail server: list messages (need message IDs)]
    └──requires──> [Gmail server: structured output (MIME flattening)]

[Gmail server: structured output]
    └──required by──> [Gmail server: read message]
    └──required by──> [Gmail server: list messages (header extraction)]

[Gmail server: search]
    └──enhances──> [Gmail server: list messages (same endpoint, adds q param)]

[Gmail server: send]
    └──independent of read (requires auth server + MIME construction)]
    └──requires──> [ClawsClient.post_json]

[Gmail: thread view]
    └──enhances──> [Gmail: read message]
    └──requires──> [Gmail server: structured output (reuse MIME flattening)]

[Auth server: multi-scope support]
    └──enables──> [Future Google skills (Calendar v1.2, Drive)]
```

### Dependency Notes

- **Auth server must exist before Gmail server:** Gmail server requests tokens from auth server on every outbound Gmail API call. Auth server is the foundation layer.
- **ClawsClient enhancements before Gmail skill:** The skill CLI needs `post_json` (for send) and parameterized `get` (for search/list). Small additions to existing `claws-common` code.
- **Structured output is cross-cutting:** Transforming Gmail's nested MIME payload into clean JSON is needed by both list (header extraction) and read (body extraction). Build this into the Gmail server from the start, not as an afterthought.
- **Multi-scope auth enables future skills:** Building the auth server with scope flexibility means Calendar (v1.2) and Drive skills get authentication for free -- just different scope strings.

## MVP Definition

### Launch With (v1.1)

Minimum to make Gmail useful as an agent tool.

- [ ] Auth server with service account + domain-wide delegation -- foundation for all Google API access
- [ ] Auth server token caching + health endpoint -- operational basics
- [ ] Auth server launchd plist -- auto-start on reboot
- [ ] Gmail server proxying list + get + send to Gmail REST API -- core email operations
- [ ] Gmail server search pass-through (q parameter) -- agent needs to find specific emails
- [ ] Gmail server structured output (flatten MIME payloads to clean JSON) -- agent needs parseable responses
- [ ] Gmail CLI skill: `claws gmail inbox`, `read <id>`, `send --to --subject --body`, `search <query>` -- the agent-facing interface
- [ ] ClawsClient.post_json and get-with-params enhancements -- required by Gmail skill
- [ ] Auth server multi-scope support -- trivial to add now, enables Calendar later

### Add After Validation (v1.1.x)

Features to add once core Gmail works end-to-end.

- [ ] Thread view (`claws gmail thread <id>`) -- add when agent needs conversation context
- [ ] Attachment metadata in message output -- add when agent asks "what files were attached"
- [ ] Label filtering on list/search -- add when inbox-only filtering is too limiting
- [ ] Reply-to support (In-Reply-To + References headers) -- add when agent needs to maintain email threads
- [ ] Mark as read/unread via modify endpoint -- add when agent manages inbox state

### Future Consideration (v2+)

- [ ] Google Calendar skill (v1.2) -- reuses auth server, different scopes, different REST endpoints
- [ ] Google Drive skill -- reuses auth server, different scopes
- [ ] Attachment download -- requires a consuming skill to process attachments
- [ ] Trash/archive -- defer until agent trust model is established
- [ ] Batch operations (batch delete, batch modify) -- defer until single-message operations prove limiting

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Auth server (token + delegation + caching) | HIGH | MEDIUM | P1 |
| Auth server health endpoint | HIGH | LOW | P1 |
| Auth server launchd plist | HIGH | LOW | P1 |
| Auth server multi-scope support | HIGH | LOW | P1 |
| Gmail server: list messages | HIGH | MEDIUM | P1 |
| Gmail server: read message | HIGH | MEDIUM | P1 |
| Gmail server: send message | HIGH | MEDIUM | P1 |
| Gmail server: search (q param) | HIGH | LOW | P1 |
| Gmail server: structured output | HIGH | MEDIUM | P1 |
| Gmail CLI: inbox/read/send/search | HIGH | MEDIUM | P1 |
| ClawsClient enhancements | HIGH | LOW | P1 |
| Gmail server: launchd plist | HIGH | LOW | P1 |
| Thread view | MEDIUM | LOW | P2 |
| Attachment metadata | MEDIUM | LOW | P2 |
| Reply-to support | MEDIUM | MEDIUM | P2 |
| Label filtering | LOW | LOW | P2 |
| Mark read/unread | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for v1.1 launch
- P2: Should have, add in v1.1.x patches
- P3: Nice to have, future consideration

## Gmail API Technical Reference

Key details that inform implementation complexity.

### Authentication Flow (Service Account + Domain-Wide Delegation)
1. Load service account JSON key file (contains `private_key`, `client_email`, `token_uri`)
2. Build JWT claims: `{"iss": client_email, "sub": delegated_user_email, "scope": "https://www.googleapis.com/auth/gmail.modify", "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now+3600}`
3. Sign JWT with RS256 using the service account's RSA private key
4. POST to `https://oauth2.googleapis.com/token` with `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=<signed_jwt>`
5. Response: `{"access_token": "ya29...", "token_type": "Bearer", "expires_in": 3600}`
6. Cache token, refresh at ~55 min mark

### Gmail API Endpoints Used (v1.1 scope)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/gmail/v1/users/me/messages` | GET | List messages (with `q`, `maxResults`, `pageToken`, `labelIds`) |
| `/gmail/v1/users/me/messages/{id}` | GET | Get single message (with `format=full\|metadata\|minimal`) |
| `/gmail/v1/users/me/messages/send` | POST | Send message (body: `{"raw": base64url_rfc2822}`) |
| `/gmail/v1/users/me/threads/{id}` | GET | Get thread with all messages (P2) |

### Required OAuth Scopes
| Scope | Grants | When to use |
|-------|--------|-------------|
| `gmail.readonly` | Read messages, threads, labels | Read-only access |
| `gmail.send` | Send email only | Send-only access |
| `gmail.modify` | Read + send + modify labels | Full access (superset, simplest) |

### MIME Payload Parsing Complexity
Gmail's `format=full` returns nested structures that need flattening:
- `payload.headers[]` -- array of `{name, value}` for From, To, Subject, Date
- `payload.body.data` -- base64url body (simple single-part messages)
- `payload.parts[]` -- array of parts for multipart, each with its own `body.data` and possibly nested `parts[]`
- Text extraction: walk parts tree, find `mimeType: "text/plain"`, decode `body.data` from base64url
- Fallback: if no text/plain, use `snippet` field (~200 chars, always present)

### Gmail Search Query Syntax (q parameter)
| Operator | Example | Notes |
|----------|---------|-------|
| `from:` | `from:boss@company.com` | Filter by sender |
| `to:` | `to:me` | Filter by recipient |
| `subject:` | `subject:meeting` | Filter by subject |
| `after:` / `before:` | `after:2024/01/01` | Date range |
| `has:attachment` | `has:attachment` | Messages with attachments |
| `is:unread` | `is:unread` | Unread messages |
| `in:` | `in:inbox` / `in:sent` | By mailbox/label |
| `OR` | `from:a OR from:b` | Boolean OR (default is AND) |

## Sources

- [Google OAuth2 Service Account Flow](https://developers.google.com/identity/protocols/oauth2/service-account) -- JWT assertion details, sub claim for delegation (HIGH confidence)
- [Gmail API REST Reference](https://developers.google.com/workspace/gmail/api/reference/rest) -- all endpoints, formats, parameters (HIGH confidence)
- [Gmail API Search/Filter Guide](https://developers.google.com/workspace/gmail/api/guides/filtering) -- q parameter syntax (HIGH confidence)
- [Gmail Message Format Reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/Format) -- raw vs full vs metadata (HIGH confidence)
- [Domain-Wide Delegation Best Practices](https://support.google.com/a/answer/14437356?hl=en) -- Google's official guidance (HIGH confidence)
- [Domain-Wide Delegation Setup](https://support.google.com/a/answer/162106?hl=en) -- Admin console configuration steps (HIGH confidence)

---
*Feature research for: Google auth server + Gmail CLI skill (v1.1 milestone)*
*Researched: 2026-03-19*
