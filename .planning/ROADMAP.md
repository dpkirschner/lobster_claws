# Roadmap: Lobster Claws

## Milestones

- v1.0 MVP - Phases 1-3 (shipped 2026-03-18)
- v1.1 Google Integration + Gmail - Phases 4-5 (in progress)

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

### v1.1 Google Integration + Gmail

**Milestone Goal:** Add a reusable Google auth server using Workspace service account delegation, then build a Gmail skill on top of it.

- [ ] **Phase 4: Google Auth Server** - Service account token vending server with domain-wide delegation, plus ClawsClient extensions
- [ ] **Phase 5: Gmail Skill** - Read, send, and search Gmail via thin CLI proxying through auth server

## Phase Details

### Phase 4: Google Auth Server
**Goal**: Skills can obtain short-lived Google access tokens from a host-side server that holds the service account key
**Depends on**: Phase 3 (v1.0 complete)
**Requirements**: CLI-01, CLI-02, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07
**Success Criteria** (what must be TRUE):
  1. ClawsClient can send POST requests with JSON bodies and GET requests with query parameters
  2. Auth server loads a service account key and mints access tokens with domain-wide delegation for a specified subject
  3. Auth server caches tokens and serves cached tokens on repeated requests within the TTL window
  4. Auth server responds to health checks on port 8301 (bound to 127.0.0.1 only)
  5. Auth server starts automatically on boot via launchd and restarts on crash
**Plans:** 3 plans

Plans:
- [ ] 04-01-PLAN.md -- ClawsClient extensions (post_json, get with params)
- [ ] 04-02-PLAN.md -- Auth server core (token vending, health, caching)
- [ ] 04-03-PLAN.md -- Launchd plist and workspace wiring

### Phase 5: Gmail Skill
**Goal**: The OpenClaw agent can read, search, and send Gmail through the `claws gmail` CLI
**Depends on**: Phase 4
**Requirements**: GMAIL-01, GMAIL-02, GMAIL-03, GMAIL-04, GMAIL-05, GMAIL-06
**Success Criteria** (what must be TRUE):
  1. User can list inbox messages and see sender, subject, date, and snippet for each
  2. User can read a specific message by ID and see the full plain-text body extracted from MIME
  3. User can send an email with recipient, subject, and body
  4. User can search messages using Gmail query syntax (from:, subject:, etc.)
  5. All Gmail output is structured JSON printed to stdout via claws_common.output, and `claws gmail` is discoverable via the meta-CLI
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 4 -> 5

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-03-18 |
| 2. Transcription Skill | v1.0 | 3/3 | Complete | 2026-03-18 |
| 3. Discovery and Documentation | v1.0 | 2/2 | Complete | 2026-03-18 |
| 4. Google Auth Server | v1.1 | 0/3 | Not started | - |
| 5. Gmail Skill | v1.1 | 0/? | Not started | - |
