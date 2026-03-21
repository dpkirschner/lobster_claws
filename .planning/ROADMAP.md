# Roadmap: Lobster Claws

## Milestones

- v1.0 MVP - Phases 1-3 (shipped 2026-03-18)
- v1.1 Google Integration + Gmail - Phases 4-5 (shipped 2026-03-20)
- v1.2 Google Calendar - Phases 6-7 (shipped 2026-03-21)
- v1.3 Multi-Agent Identity + Google Drive - Phases 8-9 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-3) - SHIPPED 2026-03-18</summary>

- [x] Phase 1: Foundation (2/2 plans) - completed 2026-03-18
- [x] Phase 2: Transcription Skill (3/3 plans) - completed 2026-03-18
- [x] Phase 3: Discovery and Documentation (2/2 plans) - completed 2026-03-18

</details>

<details>
<summary>v1.1 Google Integration + Gmail (Phases 4-5) - SHIPPED 2026-03-20</summary>

- [x] Phase 4: Google Auth Server (3/3 plans) - completed 2026-03-20
- [x] Phase 5: Gmail Skill (2/2 plans) - completed 2026-03-20

</details>

<details>
<summary>v1.2 Google Calendar (Phases 6-7) - SHIPPED 2026-03-21</summary>

- [x] Phase 6: Calendar Read Operations (2/2 plans) - completed 2026-03-20
- [x] Phase 7: Calendar Write Operations (2/2 plans) - completed 2026-03-20

</details>

### v1.3 Multi-Agent Identity + Google Drive (Phases 8-9)

- [ ] **Phase 8: Multi-Agent Identity** - Auth server per-request subject support and --as flag on Gmail and Calendar
- [ ] **Phase 9: Google Drive Skill** - List, download, and upload files via Google Drive REST API with --as support

## Phase Details

### Phase 8: Multi-Agent Identity
**Goal**: Any agent can act as a specific Google Workspace user by passing `--as user@domain.com` to existing skills
**Depends on**: Phase 7
**Requirements**: ID-01, ID-02, ID-03, ID-04, ID-05
**Success Criteria** (what must be TRUE):
  1. Auth server accepts `POST /token` with optional `subject` field and returns a token scoped to that user
  2. Auth server returns tokens for the default delegated user when no `subject` is provided (backward compatible)
  3. Two requests with the same scopes but different subjects receive different cached tokens (no cross-agent collision)
  4. User can run `claws gmail inbox --as alice@domain.com` and see Alice's inbox
  5. User can run `claws calendar list --as bob@domain.com` and see Bob's calendar
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md — Auth server per-request subject delegation with cache key fix
- [ ] 08-02-PLAN.md — Gmail and Calendar --as flag with subject threading

### Phase 9: Google Drive Skill
**Goal**: Agent can browse, download, and upload files in any user's Google Drive
**Depends on**: Phase 8
**Requirements**: DRV-01, DRV-02, DRV-03, DRV-04, DRV-05
**Success Criteria** (what must be TRUE):
  1. User can run `claws drive list` and see files with name, type, size, and modified date as structured JSON
  2. User can run `claws drive download <fileId>` to save a binary file to disk, and Google Workspace documents are automatically exported
  3. User can run `claws drive upload --name report.txt ./report.txt` to upload a file to Google Drive
  4. User can run `claws drive list --as user@domain.com` to browse another user's Drive
  5. `claws drive` appears in `claws` skill listing via entry-point discovery
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-03-18 |
| 2. Transcription Skill | v1.0 | 3/3 | Complete | 2026-03-18 |
| 3. Discovery and Documentation | v1.0 | 2/2 | Complete | 2026-03-18 |
| 4. Google Auth Server | v1.1 | 3/3 | Complete | 2026-03-20 |
| 5. Gmail Skill | v1.1 | 2/2 | Complete | 2026-03-20 |
| 6. Calendar Read Operations | v1.2 | 2/2 | Complete | 2026-03-20 |
| 7. Calendar Write Operations | v1.2 | 2/2 | Complete | 2026-03-20 |
| 8. Multi-Agent Identity | v1.3 | 0/2 | Not started | - |
| 9. Google Drive Skill | v1.3 | 0/? | Not started | - |
