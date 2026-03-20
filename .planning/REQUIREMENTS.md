# Requirements: Lobster Claws

**Defined:** 2026-03-20
**Core Value:** Every skill follows the same pattern: thin CLI in container -> HTTP call to host server -> stdout result. Adding a new capability means adding a new claw + server pair, nothing else changes.

## v1.2 Requirements

Requirements for Google Calendar milestone. Each maps to roadmap phases.

### Calendar

- [ ] **CAL-01**: User can list events for a date range (today, this week, custom range)
- [ ] **CAL-02**: User can get details for a specific event by ID
- [ ] **CAL-03**: User can create an event with title, start/end time, and optional location, description, and attendees
- [ ] **CAL-04**: User can update an existing event's fields
- [ ] **CAL-05**: User can delete an event by ID
- [ ] **CAL-06**: Calendar skill outputs structured JSON via stdout using claws_common.output
- [ ] **CAL-07**: Calendar CLI registered as `claws calendar` via entry-point discovery

## Future Requirements

### Additional Google Services

- **DRIVE-01**: User can list files in Google Drive
- **DRIVE-02**: User can download/upload files to Google Drive

### Gmail Enhancements (v1.1.x)

- **GMAIL-07**: User can view an email thread by thread ID
- **GMAIL-08**: User can see attachment metadata in message output
- **GMAIL-09**: User can filter messages by label
- **GMAIL-10**: User can reply to a message maintaining thread continuity
- **GMAIL-11**: User can mark messages as read/unread

## Out of Scope

| Feature | Reason |
|---------|--------|
| Recurring event management | Complex recurrence rules; agent creates single events for now |
| Calendar sharing/permissions | Admin-level feature, not needed for agent use |
| Auth server changes | Existing server handles Calendar scopes out of the box |
| Free/busy lookup | Could be v1.2.x if needed, not core CRUD |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAL-01 | Phase 6 | Pending |
| CAL-02 | Phase 6 | Pending |
| CAL-03 | Phase 7 | Pending |
| CAL-04 | Phase 7 | Pending |
| CAL-05 | Phase 7 | Pending |
| CAL-06 | Phase 6 | Pending |
| CAL-07 | Phase 6 | Pending |

**Coverage:**
- v1.2 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after roadmap creation*
