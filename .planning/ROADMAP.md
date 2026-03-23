# Roadmap: Lobster Claws

## Milestones

- v1.0 MVP - Phases 1-3 (shipped 2026-03-18)
- v1.1 Google Integration + Gmail - Phases 4-5 (shipped 2026-03-20)
- v1.2 Google Calendar - Phases 6-7 (shipped 2026-03-21)
- v1.3 Multi-Agent Identity + Google Drive - Phases 8-9 (shipped 2026-03-21)

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

<details>
<summary>v1.3 Multi-Agent Identity + Google Drive (Phases 8-9) - SHIPPED 2026-03-21</summary>

- [x] Phase 8: Multi-Agent Identity (2/2 plans) - completed 2026-03-21
- [x] Phase 9: Google Drive Skill (2/2 plans) - completed 2026-03-21

</details>

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
| 8. Multi-Agent Identity | v1.3 | 2/2 | Complete | 2026-03-21 |
| 9. Google Drive Skill | v1.3 | 2/2 | Complete | 2026-03-21 |

### Phase 1: Add Google Tasks, Contacts, Sheets, and Docs skills

**Goal:** Add four new Google API skills (Tasks, Contacts, Sheets, Docs) following the established claw pattern -- thin CLI with argparse, ClawsClient for auth, raw httpx for Google REST APIs, result/fail/crash output helpers.
**Requirements**: D-01 through D-17
**Depends on:** Phase 9
**Plans:** 4 plans

Plans:
- [ ] 01-01-PLAN.md — Google Tasks skill (full CRUD for task lists and tasks)
- [ ] 01-02-PLAN.md — Google Contacts skill (full CRUD + search via People API)
- [ ] 01-03-PLAN.md — Google Sheets skill (data-only read/write via A1 notation)
- [ ] 01-04-PLAN.md — Google Docs skill (read plain text, create, append)
