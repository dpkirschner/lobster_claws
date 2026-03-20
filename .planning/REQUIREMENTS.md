# Requirements: Lobster Claws

**Defined:** 2026-03-19
**Core Value:** Every skill follows the same pattern: thin CLI in container -> HTTP call to host server -> stdout result. Adding a new capability means adding a new claw + server pair, nothing else changes.

## v1.1 Requirements

Requirements for Google Integration + Gmail milestone. Each maps to roadmap phases.

### Client Library

- [x] **CLI-01**: ClawsClient supports POST with JSON body (`post_json` method)
- [x] **CLI-02**: ClawsClient supports GET with query parameters

### Google Auth

- [x] **AUTH-01**: Auth server loads service account JSON key from configured path
- [x] **AUTH-02**: Auth server mints access tokens using domain-wide delegation with configurable subject
- [x] **AUTH-03**: Auth server caches tokens and refreshes before expiry (~55 min TTL)
- [x] **AUTH-04**: Auth server accepts arbitrary scope sets via request parameter
- [x] **AUTH-05**: Auth server exposes GET /health endpoint
- [x] **AUTH-06**: Auth server binds to 127.0.0.1:8301 (not 0.0.0.0)
- [x] **AUTH-07**: Auth server managed by launchd plist with auto-start and restart

### Gmail

- [ ] **GMAIL-01**: User can list inbox messages with sender, subject, date, and snippet
- [ ] **GMAIL-02**: User can read a message by ID with full plain-text body extracted from MIME
- [ ] **GMAIL-03**: User can send an email with to, subject, and body
- [ ] **GMAIL-04**: User can search messages using Gmail query syntax (from:, subject:, etc.)
- [ ] **GMAIL-05**: Gmail skill outputs structured JSON via stdout using claws_common.output
- [ ] **GMAIL-06**: Gmail CLI registered as `claws gmail` via entry-point discovery

## Future Requirements

### Gmail Enhancements (v1.1.x)

- **GMAIL-07**: User can view an email thread by thread ID
- **GMAIL-08**: User can see attachment metadata (filename, type, size) in message output
- **GMAIL-09**: User can filter messages by label
- **GMAIL-10**: User can reply to a message maintaining thread continuity (In-Reply-To headers)
- **GMAIL-11**: User can mark messages as read/unread

### Google Calendar (v1.2)

- **CAL-01**: User can list upcoming calendar events
- **CAL-02**: User can create calendar events
- **CAL-03**: User can modify or cancel calendar events

## Out of Scope

| Feature | Reason |
|---------|--------|
| OAuth2 web flow | Service account + delegation is set-once, no browser interaction needed |
| google-api-python-client library | Heavy dependency; direct REST via httpx matches existing patterns |
| Attachment download | Needs a consuming skill to process attachments; list metadata only |
| Email deletion | Destructive, irreversible; defer until agent trust model established |
| Draft management | Adds human-in-the-loop step; direct send fits autonomous agent pattern |
| Per-skill scope enforcement | Over-engineering for single-user, internal-network system |
| Real-time push notifications | Requires public webhook URL; agent polls on demand instead |
| HTML email rendering | Agent processes text; text/plain extraction with snippet fallback sufficient |
| Resy/Spotify skills | Deferred; Google integration prioritized |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 4 | Complete |
| CLI-02 | Phase 4 | Complete |
| AUTH-01 | Phase 4 | Complete |
| AUTH-02 | Phase 4 | Complete |
| AUTH-03 | Phase 4 | Complete |
| AUTH-04 | Phase 4 | Complete |
| AUTH-05 | Phase 4 | Complete |
| AUTH-06 | Phase 4 | Complete |
| AUTH-07 | Phase 4 | Complete |
| GMAIL-01 | Phase 5 | Pending |
| GMAIL-02 | Phase 5 | Pending |
| GMAIL-03 | Phase 5 | Pending |
| GMAIL-04 | Phase 5 | Pending |
| GMAIL-05 | Phase 5 | Pending |
| GMAIL-06 | Phase 5 | Pending |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
