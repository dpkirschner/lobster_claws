---
phase: 01-foundation
verified: 2026-03-17T00:00:00Z
status: passed
score: 9/9 must-haves verified
gaps: []
human_verification:
  - test: "pip install from git URL into a fresh node:24-bookworm container"
    expected: "claws-common installs cleanly and `from claws_common import ClawsClient, resolve_host, result, error, fail, crash` works"
    why_human: "Build artifact verified locally (wheel + sdist produced successfully) but live container install requires a Docker environment not available programmatically here"
---

# Phase 1: Foundation Verification Report

**Phase Goal:** Developers can build skills on top of a working monorepo with a shared client library that handles host resolution, HTTP, and structured output
**Verified:** 2026-03-17
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `claws-common` is pip-installable (build produces valid wheel) | ✓ VERIFIED | `uv build` produced `claws_common-0.1.0-py3-none-any.whl` and `claws_common-0.1.0.tar.gz` successfully |
| 2 | Host resolution returns `host.docker.internal` inside Docker and `127.0.0.1` on the host, with `OPENCLAW_TOOLS_HOST` override working | ✓ VERIFIED | `host.py` implements all three branches; 6 unit tests pass covering env override, dockerenv, cgroup, container env var, host.docker.internal, and 127.0.0.1 fallback |
| 3 | HTTP client POST and GET calls succeed with correct timeout behavior; connection failures name the service and URL | ✓ VERIFIED | `client.py` implements `get()` and `post_file()` with `ConnectionError`/`TimeoutError` including service name and URL; 6 unit tests pass |
| 4 | CLI output follows structured convention: result to stdout, diagnostics to stderr, exit codes 0/1/2 | ✓ VERIFIED | `output.py` implements `result()/error()/fail()/crash()` with `flush=True`; 5 unit tests pass covering stdout/stderr separation and all exit codes |
| 5 | `uv sync` in the monorepo root resolves all workspace members | ✓ VERIFIED | `uv.lock` present; `.venv` active with Python 3.14.3; all 17 tests ran via `uv run pytest` with no import errors |
| 6 | All 17 unit tests pass | ✓ VERIFIED | `uv run pytest common/tests/ -x -v` → 17 passed in 0.06s |
| 7 | `__init__.py` exports full public API | ✓ VERIFIED | Exports `ClawsClient`, `resolve_host`, `result`, `error`, `fail`, `crash` via `__all__` |
| 8 | `.gitignore` covers Python artifacts, virtualenvs, IDE files, OS files | ✓ VERIFIED | Contains `__pycache__/`, `*.egg-info/`, `.venv/`, `.idea/`, `.vscode/`, `.DS_Store`, `.env` |
| 9 | Monorepo workspace links root pyproject.toml to common package | ✓ VERIFIED | `members = ["common", "skills/*", "servers/*"]`; `claws-common` added as dev dep with `workspace = true` source |

**Score:** 9/9 truths verified (1 item flagged for human verification — live Docker container install)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Root workspace config with uv workspace members, dev deps, ruff config, pytest config | ✓ VERIFIED | Contains `[tool.uv.workspace]`, `[dependency-groups]`, `[tool.ruff]`, `[tool.pytest.ini_options]` |
| `.gitignore` | Standard Python monorepo gitignore | ✓ VERIFIED | 38 lines; covers `__pycache__/`, `.venv/`, `.DS_Store`, `.env`, IDE files |
| `common/pyproject.toml` | claws-common package definition with hatchling backend | ✓ VERIFIED | `build-backend = "hatchling.build"`, `dependencies = ["httpx>=0.28"]` |
| `common/src/claws_common/__init__.py` | Public API re-exports for all library modules | ✓ VERIFIED | Exports all 6 public symbols; `__all__` defined |
| `common/src/claws_common/host.py` | `resolve_host()` and `_in_docker()` functions | ✓ VERIFIED | Both functions present; priority chain correct: env var > Docker > 127.0.0.1 |
| `common/src/claws_common/client.py` | `ClawsClient` with `get()` and `post_file()` methods | ✓ VERIFIED | Full implementation with service-aware error messages and configurable timeout |
| `common/src/claws_common/output.py` | `result()`, `error()`, `fail()`, `crash()` output helpers | ✓ VERIFIED | All 4 functions; all `print()` calls use `flush=True`; exit codes correct |
| `common/tests/test_host.py` | 6 unit tests for host resolution | ✓ VERIFIED | 6 tests; all pass |
| `common/tests/test_client.py` | 6 unit tests for HTTP client | ✓ VERIFIED | 6 tests; all pass |
| `common/tests/test_output.py` | 5 unit tests for structured output | ✓ VERIFIED | 5 tests; all pass |
| `uv.lock` | Generated lockfile | ✓ VERIFIED | Present at repo root |
| `skills/.gitkeep` | Placeholder directory | ✓ VERIFIED | File exists |
| `servers/.gitkeep` | Placeholder directory | ✓ VERIFIED | File exists |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml` | `common/pyproject.toml` | uv workspace members | ✓ WIRED | `members = ["common", "skills/*", "servers/*"]` on line 10 |
| `common/src/claws_common/client.py` | `common/src/claws_common/host.py` | `from claws_common.host import resolve_host` | ✓ WIRED | Line 5 of client.py; `resolve_host()` called in `__init__` on line 17 |
| `common/src/claws_common/__init__.py` | `common/src/claws_common/client.py` | re-export `ClawsClient` | ✓ WIRED | `from claws_common.client import ClawsClient` line 3 |
| `common/src/claws_common/__init__.py` | `common/src/claws_common/output.py` | re-export output helpers | ✓ WIRED | `from claws_common.output import crash, error, fail, result` line 5 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LIB-01 | 01-02-PLAN.md | Host resolution auto-detects Docker vs host via `.dockerenv`, cgroup check, and `OPENCLAW_TOOLS_HOST` env var override | ✓ SATISFIED | `host.py` implements all three detection methods; 6 tests pass |
| LIB-02 | 01-02-PLAN.md | HTTP client wrapper with POST/GET, configurable timeouts, connection error messages including service name and URL | ✓ SATISFIED | `client.py` ClawsClient wraps httpx; errors include service name and URL; 6 tests pass |
| LIB-03 | 01-02-PLAN.md | Structured output: result JSON to stdout, errors/diagnostics to stderr, exit codes 0/1/2 | ✓ SATISFIED | `output.py` enforces convention with `flush=True`; 5 tests pass |
| INFR-02 | 01-01-PLAN.md | Standard Python `.gitignore` for monorepo | ✓ SATISFIED | `.gitignore` covers Python artifacts, virtualenvs, IDE files, OS files, environment files |
| INFR-03 | 01-01-PLAN.md | uv workspace configuration with root `pyproject.toml` managing all packages | ✓ SATISFIED | `[tool.uv.workspace]` with members; `claws-common` wired as workspace dep |

No orphaned requirements: all 5 phase requirements (LIB-01, LIB-02, LIB-03, INFR-02, INFR-03) appear in plan frontmatter and are accounted for.

### Anti-Patterns Found

No anti-patterns detected.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | — |

Ruff lint: `ruff check common/` → all checks passed.

### Notable Finding: ROADMAP SC-2 Wording vs Implementation

The ROADMAP Success Criterion 2 says the host returns `"localhost"` outside Docker. The implementation returns `"127.0.0.1"` instead. This is the correct engineering choice (explicit IP avoids DNS resolution) and is what the PLAN truths and all tests specify. The ROADMAP wording is imprecise; no functional gap exists. The PLAN's stated truth (`"127.0.0.1"`) supersedes the loose ROADMAP wording.

### Human Verification Required

#### 1. Live Container pip Install

**Test:** In a fresh `node:24-bookworm` Docker container, run:
```
pip install git+https://github.com/<owner>/lobster_claws.git#subdirectory=common
python -c "from claws_common import ClawsClient, resolve_host, result, error, fail, crash; print('OK')"
```
**Expected:** Install succeeds; import prints `OK`; `resolve_host()` returns `"host.docker.internal"` (because `/.dockerenv` exists inside the container)
**Why human:** Requires a running Docker daemon and a reachable git remote; cannot verify programmatically in this environment. Build artifacts (`claws_common-0.1.0-py3-none-any.whl`) were verified successfully locally, which provides high confidence.

### Gaps Summary

No gaps. All automated must-haves are verified. One item (live Docker container install) requires human verification but the local build test (wheel + sdist produced correctly) provides strong supporting evidence.

---

_Verified: 2026-03-17_
_Verifier: Claude (gsd-verifier)_
