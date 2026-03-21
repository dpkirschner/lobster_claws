# Requirements: Lobster Claws

**Defined:** 2026-03-21
**Core Value:** Every skill follows the same pattern: thin CLI in container -> HTTP call to host server -> stdout result. Adding a new capability means adding a new claw + server pair, nothing else changes.

## v1.3 Requirements

Requirements for Multi-Agent Identity + Google Drive milestone. Each maps to roadmap phases.

### Identity

- [x] **ID-01**: Auth server accepts optional `subject` field on POST /token for per-agent identity
- [x] **ID-02**: Auth server caches tokens by (subject, scopes) tuple, not scopes alone
- [x] **ID-03**: Auth server falls back to `GOOGLE_DELEGATED_USER` when no subject provided
- [x] **ID-04**: Gmail skill accepts `--as user@domain.com` flag and passes subject to auth server
- [x] **ID-05**: Calendar skill accepts `--as user@domain.com` flag and passes subject to auth server

### Drive

- [ ] **DRV-01**: User can list files in Google Drive with name, type, size, and modified date
- [ ] **DRV-02**: User can download a file by ID (binary files via alt=media, Google Docs via export)
- [ ] **DRV-03**: User can upload a file to Google Drive via multipart/related upload
- [ ] **DRV-04**: Drive skill outputs structured JSON via stdout using claws_common.output
- [ ] **DRV-05**: Drive CLI registered as `claws drive` with `--as` flag via entry-point discovery

## Future Requirements

### Additional Google Services

- **SHEETS-01**: User can read/write Google Sheets data
- **CONTACTS-01**: User can search Google Contacts

### Drive Enhancements (v1.3.x)

- **DRV-06**: User can search files by name, type, or content
- **DRV-07**: User can create folders
- **DRV-08**: User can move files between folders
- **DRV-09**: Resumable upload for large files (>5MB)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Resumable upload | Simple multipart sufficient for agent-generated files; defer until needed |
| Shared drive support | Adds complexity; personal drive sufficient for agent use |
| Watch/push notifications | Requires public webhook; agent polls on demand |
| Folder creation | Can be added in v1.3.x if needed |
| Streaming downloads to stdout | Agent needs file on disk for processing |
| Per-skill scope enforcement | Open token model chosen; internal network only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ID-01 | Phase 8 | Complete |
| ID-02 | Phase 8 | Complete |
| ID-03 | Phase 8 | Complete |
| ID-04 | Phase 8 | Complete |
| ID-05 | Phase 8 | Complete |
| DRV-01 | Phase 9 | Pending |
| DRV-02 | Phase 9 | Pending |
| DRV-03 | Phase 9 | Pending |
| DRV-04 | Phase 9 | Pending |
| DRV-05 | Phase 9 | Pending |

**Coverage:**
- v1.3 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after roadmap creation*
