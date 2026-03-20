# Roadmap: Lobster Claws

## Milestones

- v1.0 MVP - Phases 1-3 (shipped 2026-03-18)
- v1.1 Google Integration + Gmail - Phases 4-5 (shipped 2026-03-20)
- v1.2 Google Calendar - Phases 6-7 (in progress)

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

### v1.2 Google Calendar

- [ ] **Phase 6: Calendar Read Operations** - Query calendar events with list and get subcommands
- [ ] **Phase 7: Calendar Write Operations** - Create, update, and delete calendar events

## Phase Details

### Phase 6: Calendar Read Operations
**Goal**: Agent can query Google Calendar to see upcoming events and read event details
**Depends on**: Phase 5 (auth server, ClawsClient patterns established)
**Requirements**: CAL-01, CAL-02, CAL-06, CAL-07
**Success Criteria** (what must be TRUE):
  1. Running `claws calendar list` shows events for today by default, and accepts date range flags
  2. Running `claws calendar get <event-id>` prints full event details (title, time, location, description, attendees)
  3. All calendar output is structured JSON printed to stdout via claws_common.output
  4. `claws` meta-CLI discovers and lists the calendar skill
**Plans:** 2 plans
Plans:
- [ ] 06-01-PLAN.md — Package skeleton, Calendar API module (list_events, get_event), and unit tests
- [ ] 06-02-PLAN.md — CLI entry point with list/get subcommands, date range flags, and CLI tests

### Phase 7: Calendar Write Operations
**Goal**: Agent can create, modify, and remove calendar events through the CLI
**Depends on**: Phase 6
**Requirements**: CAL-03, CAL-04, CAL-05
**Success Criteria** (what must be TRUE):
  1. Running `claws calendar create` with title and start/end time creates an event and prints the created event details
  2. Running `claws calendar update <event-id>` with field flags modifies the specified event
  3. Running `claws calendar delete <event-id>` removes the event and confirms deletion
**Plans:** 2 plans
Plans:
- [ ] 07-01-PLAN.md — HTTP helpers and write functions (create_event, update_event, delete_event) with API tests
- [ ] 07-02-PLAN.md — CLI subcommands (create, update, delete) with flag parsing and CLI tests

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-03-18 |
| 2. Transcription Skill | v1.0 | 3/3 | Complete | 2026-03-18 |
| 3. Discovery and Documentation | v1.0 | 2/2 | Complete | 2026-03-18 |
| 4. Google Auth Server | v1.1 | 3/3 | Complete | 2026-03-20 |
| 5. Gmail Skill | v1.1 | 2/2 | Complete | 2026-03-20 |
| 6. Calendar Read Operations | v1.2 | 0/2 | Not started | - |
| 7. Calendar Write Operations | v1.2 | 0/2 | Not started | - |
