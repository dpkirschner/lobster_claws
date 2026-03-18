---
phase: 03-discovery-and-documentation
plan: 01
subsystem: cli
tags: [entry-points, importlib, meta-cli, skill-discovery]

requires:
  - phase: 02-transcription-skill
    provides: "claws_transcribe.cli:main entry point for transcribe skill"
provides:
  - "claws meta-CLI console script for skill discovery and routing"
  - "claws.skills entry point group convention for skill registration"
affects: [future-skills, cli-extensions]

tech-stack:
  added: [claws-cli]
  patterns: [entry-point-discovery, skill-routing-via-sys-argv]

key-files:
  created:
    - cli/pyproject.toml
    - cli/src/claws_cli/__init__.py
    - cli/src/claws_cli/main.py
    - cli/tests/__init__.py
    - cli/tests/test_main.py
  modified:
    - skills/transcribe/pyproject.toml
    - pyproject.toml

key-decisions:
  - "No external dependencies for claws-cli; uses stdlib importlib.metadata only"
  - "Skills register via [project.entry-points.'claws.skills'] in their pyproject.toml"

patterns-established:
  - "Skill registration: add [project.entry-points.'claws.skills'] with name = 'module.cli:main' to skill pyproject.toml"
  - "Meta-CLI sets sys.argv before delegating so skill argparse sees correct argv"

requirements-completed: [LIB-04]

duration: 2min
completed: 2026-03-18
---

# Phase 3 Plan 1: Discovery and Documentation Summary

**Meta-CLI `claws` command with importlib.metadata entry-point discovery routing to transcribe skill**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T06:32:09Z
- **Completed:** 2026-03-18T06:34:20Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 7

## Accomplishments
- Created claws-cli package with `claws` console script entry point
- Implemented discover_skills() using importlib.metadata.entry_points(group='claws.skills')
- Registered transcribe skill under claws.skills entry point group
- 7 unit tests covering discovery, listing, routing, argv handling, and error cases
- Full test suite passes (44 tests, no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `60dc175` (test)
2. **Task 1 GREEN: Implementation** - `35fa581` (feat)

## Files Created/Modified
- `cli/pyproject.toml` - claws-cli package definition with claws console script
- `cli/src/claws_cli/__init__.py` - Package init
- `cli/src/claws_cli/main.py` - discover_skills() and main() with entry-point discovery and routing
- `cli/tests/__init__.py` - Test package init
- `cli/tests/test_main.py` - 7 tests for discovery, listing, routing, error handling
- `skills/transcribe/pyproject.toml` - Added claws.skills entry point registration
- `pyproject.toml` - Added cli to workspace members, dev deps, sources, testpaths

## Decisions Made
- No external dependencies for claws-cli; stdlib importlib.metadata is sufficient
- Skills self-register via [project.entry-points."claws.skills"] section in their pyproject.toml
- sys.argv is rewritten before delegating to skill so skill's argparse sees correct arguments

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Meta-CLI foundation complete; any new skill just needs a claws.skills entry point
- All 44 tests passing across entire workspace

---
*Phase: 03-discovery-and-documentation*
*Completed: 2026-03-18*
