---
phase: 01-foundation
plan: 02
subsystem: library
tags: [httpx, host-resolution, structured-output, tdd, pytest]

# Dependency graph
requires:
  - phase: 01-foundation-01
    provides: "uv workspace, claws-common package skeleton, pyproject.toml configs"
provides:
  - "resolve_host() for container-to-host communication"
  - "ClawsClient HTTP wrapper with service-aware errors"
  - "result/error/fail/crash structured output helpers"
  - "Public API exports via claws_common.__init__"
affects: [02-whisper-skill, 02-transcribe-server]

# Tech tracking
tech-stack:
  added: [httpx]
  patterns: [host-resolution-chain, service-aware-errors, structured-output-convention, tdd-red-green]

key-files:
  created:
    - common/src/claws_common/host.py
    - common/src/claws_common/client.py
    - common/src/claws_common/output.py
    - common/tests/test_host.py
    - common/tests/test_client.py
    - common/tests/test_output.py
  modified:
    - common/src/claws_common/__init__.py
    - pyproject.toml

key-decisions:
  - "Added claws-common as dev dependency with workspace source to fix package import in dev environment"

patterns-established:
  - "Host resolution: OPENCLAW_TOOLS_HOST env var > Docker detection > 127.0.0.1 fallback"
  - "HTTP errors include service name, URL, and diagnostic curl command"
  - "CLI output: result to stdout (str or JSON), errors to stderr, exit codes 0/1/2, always flush=True"
  - "TDD workflow: RED (failing tests) -> GREEN (implementation) -> lint fix"

requirements-completed: [LIB-01, LIB-02, LIB-03]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 1 Plan 2: claws-common Library Summary

**Three claws-common modules (host resolution, HTTP client, structured output) with 17 tests via TDD using httpx and pytest-httpx**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T05:47:39Z
- **Completed:** 2026-03-18T05:51:08Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Host resolution with env var override, Docker detection (/.dockerenv, cgroup, env var), and localhost fallback
- HTTP client wrapping httpx with service-aware ConnectionError and TimeoutError messages
- Structured output convention enforcing stdout/stderr separation and exit codes 0/1/2
- Full public API exported from claws_common package

## Task Commits

Each task was committed atomically (TDD RED then GREEN):

1. **Task 1: Host resolution module** - `2246888` (test: RED) -> `d8dfc65` (feat: GREEN)
2. **Task 2: HTTP client + structured output + __init__.py** - `d3295bd` (test: RED) -> `da19bdc` (feat: GREEN)

_TDD tasks had separate RED/GREEN commits_

## Files Created/Modified
- `common/src/claws_common/host.py` - resolve_host() and _in_docker() for container-to-host communication
- `common/src/claws_common/client.py` - ClawsClient with get() and post_file() wrapping httpx
- `common/src/claws_common/output.py` - result/error/fail/crash output helpers with flush=True
- `common/src/claws_common/__init__.py` - Public API re-exports and __all__
- `common/tests/test_host.py` - 6 tests for host resolution
- `common/tests/test_client.py` - 6 tests for HTTP client
- `common/tests/test_output.py` - 5 tests for structured output
- `pyproject.toml` - Added claws-common as dev dependency with workspace source

## Decisions Made
- Added claws-common as dev dependency in root pyproject.toml with `[tool.uv.sources]` workspace reference -- without this, the package was not installed in the dev environment and tests could not import it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed workspace package not installed in dev environment**
- **Found during:** Task 1 (test setup)
- **Issue:** claws-common was a workspace member but not installed -- `import claws_common` failed because root pyproject.toml did not list it as a dependency
- **Fix:** Added `claws-common` to dev dependency group and `[tool.uv.sources]` with `workspace = true`
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` installs claws-common, `import claws_common` succeeds
- **Committed in:** 2246888 (Task 1 RED commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for dev environment to work. No scope creep.

## Issues Encountered
- 5 ruff lint issues (import sorting, unnecessary mode argument) -- all auto-fixed with `ruff check --fix`

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- claws-common library complete with all three modules
- Public API stable: ClawsClient, resolve_host, result, error, fail, crash
- Ready for Phase 2 skill and server development that will import these modules

## Self-Check: PASSED

All 7 created files verified present. All 4 task commits verified in git history.

---
*Phase: 01-foundation*
*Completed: 2026-03-18*
