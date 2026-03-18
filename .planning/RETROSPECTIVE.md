# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-18
**Phases:** 3 | **Plans:** 7 | **Sessions:** 1

### What Was Built
- Shared client library (claws-common) with Docker-aware host resolution, service-named HTTP errors, flush-safe output
- Whisper transcription server (FastAPI + mlx-whisper) with model preloading on Apple Silicon
- Transcribe CLI skill with --model/--format flags proxying through ClawsClient
- launchd plist for whisper server auto-start and crash recovery
- Meta-CLI with entry-point skill discovery (`claws` command)
- 233-line README with complete onboarding guide

### What Worked
- **TDD throughout** — every code task used RED-GREEN pattern, caught issues early and made verification trivial
- **Parallel wave execution** — Wave 1 plans with no file overlap ran simultaneously, halving execution time for Phases 2 and 3
- **Research before planning** — the Phase 1 research surfaced the dual-environment (pip vs uv) packaging constraint before any code was written, preventing the #1 pitfall
- **Coarse granularity** — 3 phases was the right slice for this scope; more phases would have been overhead

### What Was Inefficient
- **VALIDATION.md drift** — test function names in VALIDATION.md diverged from what plans actually created; had to fix manually between plan-check and execution
- **No CONTEXT.md** — skipped discuss-phase for all 3 phases; worked fine for this well-documented project but would be risky for ambiguous requirements

### Patterns Established
- `claws-*` package naming with `claws.skills` entry point group for auto-discovery
- Each skill: `skills/<name>/` package + `servers/<name>/` server + launchd plist
- hatchling build backend + `[tool.uv.sources]` for workspace dev, named deps for pip install
- Port 8300+ range convention for servers

### Key Lessons
1. **Dual-environment packaging is the critical foundation decision** — getting hatchling + uv sources right in Phase 1 meant zero packaging issues in later phases
2. **Mock everything at test boundaries** — server tests mock mlx-whisper, CLI tests mock ClawsClient; no GPU or running server needed for CI
3. **flush=True in all output** — baked into output.py helpers so every future skill inherits Docker compatibility without thinking about it

### Cost Observations
- Model mix: ~60% opus (research, planning, execution), ~40% sonnet (verification, synthesis)
- Sessions: 1 (entire v1.0 built in single session)
- Notable: research agents ran in parallel (4x project researchers, then phase researchers), significantly reducing wait time

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 3 | Initial project — established TDD, parallel waves, research-first patterns |

### Cumulative Quality

| Milestone | Tests | Coverage | Packages |
|-----------|-------|----------|----------|
| v1.0 | 44 | — | 4 (common, cli, transcribe, whisper-server) |

### Top Lessons (Verified Across Milestones)

1. Research before planning prevents architectural mistakes (verified: dual-environment packaging)
2. TDD with mocked boundaries enables testing without infrastructure dependencies
