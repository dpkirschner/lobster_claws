# Roadmap: Lobster Claws

## Overview

Lobster Claws delivers AI agent skills as thin container-side CLIs paired with macOS host-side servers. The roadmap builds bottom-up: first the shared library and monorepo scaffolding that every skill depends on, then the first complete skill (whisper transcription) as the proof-of-concept that validates the full request-response loop, and finally the meta-CLI and documentation that make the system usable and extensible.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Monorepo structure, shared client library, and host resolution
- [ ] **Phase 2: Transcription Skill** - Whisper server, transcribe CLI, and launchd process supervision
- [ ] **Phase 3: Discovery and Documentation** - Meta-CLI with entry-point routing and project README

## Phase Details

### Phase 1: Foundation
**Goal**: Developers can build skills on top of a working monorepo with a shared client library that handles host resolution, HTTP, and structured output
**Depends on**: Nothing (first phase)
**Requirements**: LIB-01, LIB-02, LIB-03, INFR-02, INFR-03
**Success Criteria** (what must be TRUE):
  1. `claws-common` is pip-installable from git URL into a fresh `node:24-bookworm` container
  2. Host resolution returns `host.docker.internal` inside Docker and `localhost` on the host, with `OPENCLAW_TOOLS_HOST` override working in both environments
  3. HTTP client POST and GET calls to a running server succeed with correct timeout behavior, and connection failures produce error messages that name the service and URL
  4. CLI output follows structured convention: result to stdout, diagnostics to stderr, exit codes 0/1/2
  5. `uv sync` in the monorepo root resolves all workspace members
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Monorepo scaffolding: root workspace config, .gitignore, claws-common package skeleton
- [ ] 01-02-PLAN.md — claws-common library modules (host, client, output) with full test coverage

### Phase 2: Transcription Skill
**Goal**: An AI agent in the OpenClaw container can transcribe audio files by calling a CLI that proxies to a GPU-accelerated whisper server on the Mac mini host
**Depends on**: Phase 1
**Requirements**: WHSP-01, WHSP-02, WHSP-03, WHSP-04, TRNS-01, TRNS-02, TRNS-03, TRNS-04, INFR-01
**Success Criteria** (what must be TRUE):
  1. `claws transcribe <audio-file>` in the container prints transcription text to stdout and returns exit code 0
  2. Whisper server `GET /health` returns server status and loaded model info
  3. Model selection works end-to-end: `--model` flag on CLI propagates to server and uses the requested model
  4. Server auto-starts after Mac mini reboot via launchd and auto-restarts after crash
  5. Default model stays loaded in memory between requests (no cold-start penalty on second call)
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Whisper server: FastAPI app with /transcribe, /health, model preloading, and tests
- [ ] 02-02-PLAN.md — Transcribe CLI: claws-transcribe package with --model, --format flags, and tests
- [ ] 02-03-PLAN.md — launchd plist for whisper server auto-start/restart with validation tests

### Phase 3: Discovery and Documentation
**Goal**: Users can discover installed skills via a single `claws` command and new contributors can set up the project from the README
**Depends on**: Phase 2
**Requirements**: LIB-04, INFR-04
**Success Criteria** (what must be TRUE):
  1. Running `claws` with no arguments lists all installed skills discovered via Python entry points
  2. `claws transcribe <file>` routes correctly to the transcribe skill (meta-CLI delegates to sub-skills)
  3. README documents repo structure, skill installation, server setup, and how to add a new skill
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Not started | - |
| 2. Transcription Skill | 0/3 | Not started | - |
| 3. Discovery and Documentation | 0/? | Not started | - |
